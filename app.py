"""Legal Document Assistant: upload a legal document, get a plain-language analysis, and ask grounded questions.

Documents are kept in memory only and never written to disk.
Privacy-first, local processing with no external API calls.
"""

import uuid

from flask import Flask, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from legallens.analysis import analyze
from legallens.parser import MAX_BYTES, UnsupportedFileError, extract_pages
from legallens.search import build_chunks, search

MAX_DOCUMENTS = 50
MAX_QUESTION_CHARS = 500
NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded document."

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 64 * 1024

# Rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",
)

DOCUMENTS = {}  # document id -> {"chunks": [...], "result": {...}}


def error(message, status):
    return jsonify(error=message), status


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    )
    return response


@app.errorhandler(413)
def file_too_large(_):
    return error("The file is larger than 5 MB.", 413)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


def validate_file_upload(file):
    """Validate uploaded file for security and integrity.
    
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if file is None or file.filename == "":
        return False, "Please choose a PDF or TXT file."
    
    # Validate filename
    filename = str(file.filename).strip()
    if not filename or len(filename) > 255:
        return False, "Invalid filename length."
    
    # Check for null bytes and path traversal attempts
    if '\x00' in filename or '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename characters detected."
    
    # Validate file extension
    allowed_extensions = {'.pdf', '.txt'}
    file_ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if file_ext not in allowed_extensions:
        return False, "Only PDF and TXT files are supported."
    
    # Check file size before reading (peek at content length if available)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to start
    
    if size == 0:
        return False, "The uploaded file is empty."
    
    if size > MAX_BYTES:
        return False, f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB."
    
    # Basic MIME type validation (check file signature/magic bytes)
    file_start = file.read(8)
    file.seek(0)
    
    # PDF magic bytes: %PDF
    # Text files: typically ASCII/UTF-8 printable characters
    if file_ext == '.pdf':
        if not file_start.startswith(b'%PDF'):
            return False, "File does not appear to be a valid PDF."
    elif file_ext == '.txt':
        # Check if file starts with reasonable text bytes (not binary garbage)
        try:
            file_start.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            # Try with relaxed checking for different encodings
            if not any(b >= 0x20 and b <= 0x7E or b in (0x09, 0x0A, 0x0D) for b in file_start[:100]):
                return False, "File does not appear to be valid text."
    
    return True, None


@app.post("/api/upload")
@limiter.limit("10 per minute")
def upload():
    uploaded = request.files.get("document")
    
    # Validate file upload
    is_valid, error_message = validate_file_upload(uploaded)
    if not is_valid:
        return error(error_message, 400)
    
    try:
        # Read file content with size limit enforced
        file_content = uploaded.read(MAX_BYTES + 1)
        if len(file_content) > MAX_BYTES:
            return error(f"File exceeds maximum size of {MAX_BYTES // (1024 * 1024)} MB.", 413)
        
        pages = extract_pages(uploaded.filename, file_content)
    except UnsupportedFileError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        # Log unexpected errors but don't expose internal details
        app.logger.error(f"Upload error: {type(exc).__name__}: {exc}")
        return error("Failed to process the document. Please try again.", 500)

    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    if len(DOCUMENTS) >= MAX_DOCUMENTS:
        DOCUMENTS.pop(next(iter(DOCUMENTS)))  # forget the oldest document
    document_id = uuid.uuid4().hex
    DOCUMENTS[document_id] = {"chunks": chunks, "result": result}
    return jsonify(id=document_id, **result)


def sanitize_input(value, max_length=500, allow_newlines=True):
    """Sanitize and validate user input strings.
    
    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters
        
    Returns:
        str: Sanitized string
    """
    if value is None:
        return ""
    
    text = str(value).strip()
    
    # Remove null bytes and other control characters (except newlines/tabs if allowed)
    if allow_newlines:
        text = ''.join(char for char in text if char.isprintable() or char in ('\n', '\r', '\t'))
    else:
        text = ''.join(char for char in text if char.isprintable())
    
    # Truncate to max length
    return text[:max_length]


def validate_uuid(value):
    """Validate that a string is a valid UUID hex format.
    
    Args:
        value: String to validate
        
    Returns:
        bool: True if valid UUID hex
    """
    if not isinstance(value, str):
        return False
    
    # UUID hex is 32 hexadecimal characters
    return len(value) == 32 and all(c in '0123456789abcdef' for c in value.lower())


@app.post("/api/ask")
@limiter.limit("30 per minute")
def ask():
    body = request.get_json(silent=True) or {}
    
    # Validate document ID format
    doc_id = str(body.get("id", ""))
    if not validate_uuid(doc_id):
        return error("Invalid document ID format.", 400)
    
    document = DOCUMENTS.get(doc_id)
    if document is None:
        return error("Document not found. Please upload it again.", 404)
    
    # Sanitize and validate question
    question = sanitize_input(body.get("question", ""), MAX_QUESTION_CHARS, allow_newlines=False)
    if not question:
        return error("Please type a question.", 400)
    
    if len(question) < 3:
        return error("Question is too short. Please provide more detail.", 400)

    matches = search(document["chunks"], question)
    return jsonify(matches=matches, message="" if matches else NOT_FOUND_MESSAGE)


@app.post("/api/compare")
@limiter.limit("5 per minute")
def compare():
    """Compare two documents side-by-side and highlight differences in key terms."""
    body = request.get_json(silent=True) or {}
    
    # Validate both document IDs
    doc1_id = str(body.get("id1", ""))
    doc2_id = str(body.get("id2", ""))
    
    if not validate_uuid(doc1_id) or not validate_uuid(doc2_id):
        return error("Invalid document ID format.", 400)
    
    if doc1_id == doc2_id:
        return error("Cannot compare a document with itself.", 400)
    
    doc1 = DOCUMENTS.get(doc1_id)
    doc2 = DOCUMENTS.get(doc2_id)
    
    if doc1 is None or doc2 is None:
        return error("One or both documents not found. Please upload them again.", 404)
    
    from legallens.analysis import compare_documents
    comparison = compare_documents(doc1["result"], doc2["result"])
    
    return jsonify(comparison)


@app.get("/api/documents")
def list_documents():
    """Return a list of currently uploaded documents for comparison selection."""
    doc_list = []
    for doc_id, doc_data in DOCUMENTS.items():
        summary = doc_data["result"]["summary"]
        doc_list.append({
            "id": doc_id,
            "type": summary["type"],
            "pages": summary["pages"]
        })
    return jsonify(documents=doc_list)


@app.get("/api/export/<document_id>")
def export_report(document_id):
    """Export analysis report as HTML for printing/saving."""
    # Validate document ID format
    if not validate_uuid(document_id):
        return error("Invalid document ID format.", 400)
    
    document = DOCUMENTS.get(document_id)
    if document is None:
        return error("Document not found.", 404)
    
    result = document["result"]
    
    # Generate HTML report
    html_report = generate_html_report(result)
    
    from flask import Response
    response = Response(html_report, mimetype='text/html')
    response.headers['Content-Disposition'] = f'inline; filename="legal-analysis-report.html"'
    return response


def generate_html_report(result):
    """Generate a formatted HTML report of the analysis."""
    summary = result["summary"]
    findings = result["findings"]
    entities = result.get("entities", {})
    risk = result.get("risk_assessment", {})
    checklist = result["checklist"]
    
    # Risk level styling
    risk_level = risk.get("level", "Unknown")
    risk_color = "#ef4444" if risk_level == "High" else "#f59e0b" if risk_level == "Medium" else "#10b981"
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal Document Analysis Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            background: #f9fafb;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.9; }}
        .section {{
            background: white;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #2563eb;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
        }}
        .risk-badge {{
            display: inline-block;
            padding: 0.5rem 1.5rem;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1rem;
            background: {risk_color};
            color: white;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 0.5rem 1rem;
            margin-top: 1rem;
        }}
        .summary-label {{ font-weight: 600; color: #6b7280; }}
        .summary-value {{ color: #1f2937; }}
        .finding {{
            background: #f3f4f6;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 4px solid #2563eb;
            border-radius: 4px;
        }}
        .finding-header {{
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }}
        .finding-label {{
            display: inline-block;
            background: #dbeafe;
            color: #1e40af;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }}
        .finding-meta {{ color: #6b7280; font-size: 0.9rem; margin: 0.5rem 0; }}
        .excerpt {{
            background: white;
            padding: 1rem;
            border-left: 3px solid #3b82f6;
            margin-top: 0.5rem;
            font-style: italic;
            color: #4b5563;
        }}
        .checklist {{ list-style: none; }}
        .checklist li {{
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #f3f4f6;
            border-radius: 4px;
        }}
        .checklist li:before {{
            content: "✓ ";
            color: #10b981;
            font-weight: bold;
            margin-right: 0.5rem;
        }}
        .entity-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .entity-box {{
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 4px;
        }}
        .entity-title {{
            font-weight: 600;
            color: #2563eb;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            text-transform: uppercase;
        }}
        .entity-list {{ list-style: none; font-size: 0.9rem; }}
        .entity-list li {{
            padding: 0.25rem 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .disclaimer {{
            background: #fef3c7;
            border: 2px solid #f59e0b;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 2rem;
            text-align: center;
        }}
        .disclaimer strong {{ color: #92400e; }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e5e7eb;
            font-size: 0.9rem;
        }}
        @media print {{
            body {{ background: white; }}
            .header {{ background: #2563eb; }}
            .section {{ box-shadow: none; border: 1px solid #e5e7eb; page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚖️ Legal Document Analysis Report</h1>
        <p>Generated by Legal Document Assistant</p>
        <p style="font-size: 0.9rem; margin-top: 0.5rem;">
            {summary['type']} | {summary['pages']} page(s)
        </p>
    </div>

    <!-- Risk Assessment -->
    <div class="section">
        <h2>⚠️ Risk Assessment</h2>
        <div style="text-align: center; padding: 1rem;">
            <div class="risk-badge">{risk_level} Risk</div>
            <div style="margin-top: 1rem; color: #6b7280;">
                <strong>Risk Score:</strong> {risk.get('score', 0)}/10 | 
                <strong>Total Issues:</strong> {risk.get('total_issues', 0)} | 
                <strong>High Priority:</strong> {risk.get('high_priority', 0)}
            </div>
        </div>
    </div>

    <!-- Summary -->
    <div class="section">
        <h2>📊 Document Summary</h2>
        <div class="summary-grid">
            <div class="summary-label">Document Type:</div>
            <div class="summary-value">{summary['type']}</div>
            <div class="summary-label">Pages:</div>
            <div class="summary-value">{summary['pages']}</div>
            <div class="summary-label">Duration:</div>
            <div class="summary-value">{summary['duration']}</div>
            <div class="summary-label">Monthly Rent:</div>
            <div class="summary-value">{summary['monthly_rent']}</div>
            <div class="summary-label">Security Deposit:</div>
            <div class="summary-value">{summary['security_deposit']}</div>
            <div class="summary-label">Notice Period:</div>
            <div class="summary-value">{summary['notice_period']}</div>
        </div>
    </div>

    <!-- Key Information -->
    <div class="section">
        <h2>🔍 Key Information</h2>
        <div class="entity-grid">
            <div class="entity-box">
                <div class="entity-title">📅 Important Dates</div>
                <ul class="entity-list">
                    {"".join(f"<li>{date}</li>" for date in entities.get('dates', [])[:5]) or "<li>None found</li>"}
                </ul>
            </div>
            <div class="entity-box">
                <div class="entity-title">💰 Financial Amounts</div>
                <ul class="entity-list">
                    {"".join(f"<li>{amount}</li>" for amount in entities.get('amounts', [])[:5]) or "<li>None found</li>"}
                </ul>
            </div>
            <div class="entity-box">
                <div class="entity-title">👥 Parties</div>
                <ul class="entity-list">
                    {"".join(f"<li>{party}</li>" for party in entities.get('parties', [])[:5]) or "<li>None found</li>"}
                </ul>
            </div>
        </div>
    </div>

    <!-- Findings -->
    <div class="section">
        <h2>📋 Clauses to Review ({len(findings)} found)</h2>
        {generate_findings_html(findings)}
    </div>

    <!-- Checklist -->
    <div class="section">
        <h2>✅ Pre-Signing Checklist</h2>
        <ul class="checklist">
            {"".join(f"<li>{item}</li>" for item in checklist)}
        </ul>
    </div>

    <div class="disclaimer">
        <strong>⚠️ Important Disclaimer</strong><br>
        {result['disclaimer']}
    </div>

    <div class="footer">
        <p>Report generated on {__import__('datetime').datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>Legal Document Assistant - Privacy-First Document Analysis</p>
    </div>
</body>
</html>
"""
    return html


def generate_findings_html(findings):
    """Generate HTML for findings section."""
    if not findings:
        return '<p style="color: #6b7280; text-align: center; padding: 2rem;">No issues found.</p>'
    
    html_parts = []
    for finding in findings[:20]:  # Limit to top 20 findings
        clause_info = f"Clause {finding['clause']}" if finding['clause'] else "Unnumbered section"
        html_parts.append(f"""
        <div class="finding">
            <div class="finding-header">
                <span class="finding-label">{finding['label']} - Risk: {finding['risk_score']}/10</span>
                <br>{finding['category'].title()}
            </div>
            <p>{finding['explanation']}</p>
            <div class="finding-meta">{clause_info}, Page {finding['page']}</div>
            <div class="excerpt">{finding['excerpt'][:250]}...</div>
        </div>
        """)
    
    return "".join(html_parts)


if __name__ == "__main__":
    app.run(debug=False)
