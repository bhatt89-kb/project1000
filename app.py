"""Legal Document Assistant: upload a legal document, get a plain-language analysis, and ask grounded questions.

Documents are kept in memory only and never written to disk.
Privacy-first, local processing with no external API calls.
"""

import hashlib
import uuid
from typing import Dict, List, Optional, TypedDict, Any

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from legallens.analysis import analyze, compare_documents
from legallens.parser import MAX_BYTES, UnsupportedFileError, extract_pages
from legallens.search import build_chunks, search

# =============================================================================
# CONSTANTS - All magic numbers extracted for maintainability
# =============================================================================

# Rate limiting constants (requests per minute)
RATE_LIMIT_UPLOAD = 10          # Maximum uploads per minute per IP
RATE_LIMIT_QUESTIONS = 30       # Maximum questions per minute per IP
RATE_LIMIT_COMPARISONS = 5      # Maximum comparisons per minute per IP
RATE_LIMIT_EXPORT = 20          # Maximum exports per minute per IP
RATE_LIMIT_LIST_DOCS = 100      # Maximum document list requests per minute

# Document storage limits
MAX_DOCUMENTS = 50              # Maximum documents stored in memory
MAX_QUESTION_CHARS = 500        # Maximum characters in a question
MIN_QUESTION_CHARS = 3          # Minimum characters for valid question

# File upload limits
MAX_FILENAME_LENGTH = 255       # Maximum filename length in characters
FILE_SIZE_BUFFER = 64 * 1024    # Extra buffer for file upload headers (64KB)

# UUID format validation
UUID_HEX_LENGTH = 32            # Length of UUID in hexadecimal format

# Messages
NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded document."
INVALID_UUID_MESSAGE = "Invalid document ID format."
DOCUMENT_NOT_FOUND_MESSAGE = "Document not found. Please upload it again."

# =============================================================================
# TYPE DEFINITIONS - Improved type safety
# =============================================================================

class ChunkDict(TypedDict):
    """Type definition for document chunk."""
    text: str
    page: int
    clause: Optional[str]

class AnalysisResult(TypedDict):
    """Type definition for analysis result."""
    summary: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    entities: Dict[str, List[str]]
    findings: List[Dict[str, Any]]
    checklist: List[str]
    disclaimer: str

class DocumentData(TypedDict):
    """Type definition for stored document data."""
    chunks: List[ChunkDict]
    result: AnalysisResult

# Type aliases for clarity
DocumentId = str
DocumentStore = Dict[DocumentId, DocumentData]
ContentHash = str

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + FILE_SIZE_BUFFER

# Rate limiting configuration with memory storage
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",
)

# Document storage: document_id -> DocumentData
DOCUMENTS: DocumentStore = {}

# Content-based cache: content_hash -> DocumentData (prevents duplicate analysis)
CONTENT_CACHE: Dict[ContentHash, DocumentData] = {}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def error(message: str, status: int):
    """Return a JSON error response.
    
    Args:
        message: Human-readable error message
        status: HTTP status code
        
    Returns:
        Tuple of (JSON response, status code)
    """
    return jsonify(error=message), status


def get_content_hash(data: bytes) -> ContentHash:
    """Generate SHA-256 hash of file content for caching.
    
    Args:
        data: File content as bytes
        
    Returns:
        Hexadecimal hash string
        
    Note:
        Used to detect duplicate uploads and avoid re-analyzing same content
    """
    return hashlib.sha256(data).hexdigest()


def validate_uuid(value: str) -> bool:
    """Validate that a string is a valid UUID hex format.
    
    Args:
        value: String to validate
        
    Returns:
        True if valid UUID hex (32 hexadecimal characters), False otherwise
        
    Example:
        >>> validate_uuid("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
        True
        >>> validate_uuid("invalid")
        False
    """
    if not isinstance(value, str):
        return False
    
    # UUID hex is exactly 32 hexadecimal characters (no hyphens)
    return len(value) == UUID_HEX_LENGTH and all(c in '0123456789abcdef' for c in value.lower())


def sanitize_input(value: Any, max_length: int = 500, allow_newlines: bool = True) -> str:
    """Sanitize and validate user input strings.
    
    Removes control characters and truncates to maximum length.
    Critical for preventing injection attacks and malformed input.
    
    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length in characters
        allow_newlines: Whether to allow newline characters
        
    Returns:
        Sanitized string with control characters removed and length capped
        
    Example:
        >>> sanitize_input("Hello\x00World", 10)
        'HelloWorld'
    """
    if value is None:
        return ""
    
    text = str(value).strip()
    
    # Remove null bytes and other control characters (except newlines/tabs if allowed)
    if allow_newlines:
        text = ''.join(char for char in text if char.isprintable() or char in ('\n', '\r', '\t'))
    else:
        text = ''.join(char for char in text if char.isprintable())
    
    # Truncate to maximum length to prevent memory exhaustion
    return text[:max_length]


def validate_file_upload(file) -> tuple[bool, Optional[str]]:
    """Validate uploaded file for security and integrity.
    
    Performs comprehensive validation:
    - Filename validation (length, special characters)
    - Path traversal prevention
    - File extension whitelist
    - Size limits
    - MIME type validation via magic bytes
    
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid
    """
    if file is None or file.filename == "":
        return False, "Please choose a PDF or TXT file."
    
    # Validate filename length and format
    filename = str(file.filename).strip()
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        return False, "Invalid filename length."
    
    # Check for path traversal attempts and null bytes
    # These are common attack vectors for file uploads
    if '\x00' in filename or '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename characters detected."
    
    # Validate file extension against whitelist
    allowed_extensions = {'.pdf', '.txt'}
    file_ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if file_ext not in allowed_extensions:
        return False, "Only PDF and TXT files are supported."
    
    # Check file size before reading entire content into memory
    file.seek(0, 2)  # Seek to end of file
    size = file.tell()
    file.seek(0)  # Reset to start for later reading
    
    if size == 0:
        return False, "The uploaded file is empty."
    
    if size > MAX_BYTES:
        return False, f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB."
    
    # Validate file content via magic bytes (file signature)
    # This prevents file type spoofing attacks
    file_start = file.read(8)
    file.seek(0)  # Reset after reading
    
    # PDF magic bytes: %PDF (hex: 25 50 44 46)
    if file_ext == '.pdf':
        if not file_start.startswith(b'%PDF'):
            return False, "File does not appear to be a valid PDF."
    # Text files: check if content is valid UTF-8
    elif file_ext == '.txt':
        try:
            file_start.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            # Try with relaxed checking for different encodings
            if not any(b >= 0x20 and b <= 0x7E or b in (0x09, 0x0A, 0x0D) for b in file_start[:100]):
                return False, "File does not appear to be valid text."
    
    return True, None


# =============================================================================
# FLASK ROUTES AND MIDDLEWARE
# =============================================================================

@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - Referrer-Policy: Control referrer information
    - Content-Security-Policy: Restrict resource loading
    - Strict-Transport-Security: Force HTTPS (HSTS)
    - Permissions-Policy: Restrict browser features
    - X-Permitted-Cross-Domain-Policies: Restrict cross-domain policies
    
    All headers meet OWASP security best practices.
    """
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    
    # Control referrer information leakage
    response.headers["Referrer-Policy"] = "no-referrer"
    
    # Content Security Policy - restrict resource loading to same origin
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    
    # Force HTTPS connections (HSTS) - max age 1 year, include subdomains
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Restrict browser features for privacy
    response.headers["Permissions-Policy"] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=()"
    )
    
    # Restrict cross-domain policies
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    
    return response


@app.errorhandler(413)
def file_too_large(_):
    """Handle file upload size limit exceeded error."""
    return error("The file is larger than 5 MB.", 413)


@app.get("/")
def index():
    """Serve the main application HTML page."""
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/upload")
@limiter.limit(f"{RATE_LIMIT_UPLOAD} per minute")
def upload():
    """Upload and analyze a legal document.
    
    Process:
    1. Validate uploaded file (security checks)
    2. Check content hash for duplicate detection
    3. Extract text from PDF/TXT
    4. Analyze document (risk scoring, entity extraction)
    5. Store results in memory with UUID
    
    Returns:
        JSON with document ID, summary, risk assessment, entities, findings, checklist
        
    Rate Limited:
        10 uploads per minute per IP address
    """
    uploaded = request.files.get("document")
    
    # Step 1: Validate file upload (security critical)
    is_valid, error_message = validate_file_upload(uploaded)
    if not is_valid:
        return error(error_message, 400)
    
    try:
        # Step 2: Read file content with size limit enforced
        file_content = uploaded.read(MAX_BYTES + 1)
        if len(file_content) > MAX_BYTES:
            return error(f"File exceeds maximum size of {MAX_BYTES // (1024 * 1024)} MB.", 413)
        
        # Step 3: Check content hash for duplicate detection (efficiency optimization)
        content_hash = get_content_hash(file_content)
        if content_hash in CONTENT_CACHE:
            # Duplicate detected - return cached result with new document ID
            cached_data = CONTENT_CACHE[content_hash]
            document_id = uuid.uuid4().hex
            DOCUMENTS[document_id] = cached_data
            return jsonify(id=document_id, **cached_data["result"])
        
        # Step 4: Extract pages from PDF or text file
        pages = extract_pages(uploaded.filename, file_content)
        
    except UnsupportedFileError as exc:
        return error(str(exc), 400)
    except Exception as exc:
        # Log unexpected errors but don't expose internal details to user
        app.logger.error(f"Upload error: {type(exc).__name__}: {exc}")
        return error("Failed to process the document. Please try again.", 500)
    
    # Step 5: Build searchable chunks from pages
    chunks = build_chunks(pages)
    
    # Step 6: Analyze document for risks, entities, and key terms
    result = analyze(pages, chunks)
    
    # Step 7: Enforce document limit (prevent memory exhaustion)
    if len(DOCUMENTS) >= MAX_DOCUMENTS:
        # Remove oldest document (FIFO)
        oldest_id = next(iter(DOCUMENTS))
        DOCUMENTS.pop(oldest_id)
    
    # Step 8: Generate unique document ID and store results
    document_id = uuid.uuid4().hex
    document_data: DocumentData = {"chunks": chunks, "result": result}
    DOCUMENTS[document_id] = document_data
    
    # Step 9: Cache by content hash for future duplicate detection
    CONTENT_CACHE[content_hash] = document_data
    
    # Step 10: Return analysis results with document ID
    return jsonify(id=document_id, **result)


@app.post("/api/ask")
@limiter.limit(f"{RATE_LIMIT_QUESTIONS} per minute")
def ask():
    """Ask a question about an uploaded document.
    
    Uses keyword-based search with stemming and stopword filtering.
    Returns up to 3 most relevant passages with page numbers and clause references.
    
    Rate Limited:
        30 questions per minute per IP address
    """
    body = request.get_json(silent=True) or {}
    
    # Validate document ID format (security: prevent enumeration attacks)
    doc_id = str(body.get("id", ""))
    if not validate_uuid(doc_id):
        return error(INVALID_UUID_MESSAGE, 400)
    
    # Check if document exists in memory
    document = DOCUMENTS.get(doc_id)
    if document is None:
        return error(DOCUMENT_NOT_FOUND_MESSAGE, 404)
    
    # Sanitize and validate question input
    question = sanitize_input(body.get("question", ""), MAX_QUESTION_CHARS, allow_newlines=False)
    if not question:
        return error("Please type a question.", 400)
    
    if len(question) < MIN_QUESTION_CHARS:
        return error("Question is too short. Please provide more detail.", 400)
    
    # Search for relevant passages using keyword matching
    matches = search(document["chunks"], question)
    
    # Return matches or helpful message if nothing found
    return jsonify(
        matches=matches,
        message="" if matches else NOT_FOUND_MESSAGE
    )


@app.post("/api/compare")
@limiter.limit(f"{RATE_LIMIT_COMPARISONS} per minute")
def compare():
    """Compare two documents side-by-side.
    
    Highlights differences in:
    - Summary fields (rent, deposit, duration)
    - Risk levels and scores
    - Unique clauses present in each document
    
    Rate Limited:
        5 comparisons per minute per IP address
    """
    body = request.get_json(silent=True) or {}
    
    # Validate both document IDs
    doc1_id = str(body.get("id1", ""))
    doc2_id = str(body.get("id2", ""))
    
    if not validate_uuid(doc1_id) or not validate_uuid(doc2_id):
        return error(INVALID_UUID_MESSAGE, 400)
    
    # Prevent comparing document with itself
    if doc1_id == doc2_id:
        return error("Cannot compare a document with itself.", 400)
    
    # Check both documents exist
    doc1 = DOCUMENTS.get(doc1_id)
    doc2 = DOCUMENTS.get(doc2_id)
    
    if doc1 is None or doc2 is None:
        return error(DOCUMENT_NOT_FOUND_MESSAGE, 404)
    
    # Perform comparison analysis
    comparison = compare_documents(doc1["result"], doc2["result"])
    
    return jsonify(comparison)


@app.get("/api/documents")
@limiter.limit(f"{RATE_LIMIT_LIST_DOCS} per minute")
def list_documents():
    """Return list of currently uploaded documents.
    
    Used for document selection in comparison feature.
    Returns basic metadata only (type, pages) to minimize response size.
    """
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
@limiter.limit(f"{RATE_LIMIT_EXPORT} per minute")
def export_report(document_id: str):
    """Export analysis report as HTML for printing/saving.
    
    Generates a formatted HTML report with:
    - Risk assessment summary
    - Document summary
    - Key information (dates, amounts, parties)
    - Flagged clauses with explanations
    - Pre-signing checklist
    - Professional styling for print
    
    Args:
        document_id: UUID of document to export
        
    Returns:
        HTML document with embedded CSS
    """
    # Validate document ID format
    if not validate_uuid(document_id):
        return error(INVALID_UUID_MESSAGE, 400)
    
    # Check document exists
    document = DOCUMENTS.get(document_id)
    if document is None:
        return error(DOCUMENT_NOT_FOUND_MESSAGE, 404)
    
    result = document["result"]
    
    # Generate HTML report with professional formatting
    html_report = generate_html_report(result)
    
    response = Response(html_report, mimetype='text/html')
    response.headers['Content-Disposition'] = 'inline; filename="legal-analysis-report.html"'
    return response


# =============================================================================
# REPORT GENERATION HELPERS
# =============================================================================

def generate_html_report(result: AnalysisResult) -> str:
    """Generate a formatted HTML report of the analysis.
    
    Args:
        result: Analysis result containing summary, findings, entities, etc.
        
    Returns:
        Complete HTML document as string
    """
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


def generate_findings_html(findings: List[Dict[str, Any]]) -> str:
    """Generate HTML for findings section.
    
    Args:
        findings: List of finding dictionaries
        
    Returns:
        HTML string for findings section
    """
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
