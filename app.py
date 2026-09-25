"""Legal Document Assistant: upload a legal document, get a plain-language analysis, and ask grounded questions.

Documents are kept in memory only and never written to disk.
Privacy-first, local processing with no external API calls.
"""

import uuid

from flask import Flask, jsonify, request, send_from_directory

from legallens.analysis import analyze
from legallens.parser import MAX_BYTES, UnsupportedFileError, extract_pages
from legallens.search import build_chunks, search

MAX_DOCUMENTS = 50
MAX_QUESTION_CHARS = 500
NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded document."

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 64 * 1024
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


@app.post("/api/upload")
def upload():
    uploaded = request.files.get("document")
    if uploaded is None or uploaded.filename == "":
        return error("Please choose a PDF or TXT file.", 400)
    try:
        pages = extract_pages(uploaded.filename, uploaded.read())
    except UnsupportedFileError as exc:
        return error(str(exc), 400)

    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    if len(DOCUMENTS) >= MAX_DOCUMENTS:
        DOCUMENTS.pop(next(iter(DOCUMENTS)))  # forget the oldest document
    document_id = uuid.uuid4().hex
    DOCUMENTS[document_id] = {"chunks": chunks, "result": result}
    return jsonify(id=document_id, **result)


@app.post("/api/ask")
def ask():
    body = request.get_json(silent=True) or {}
    document = DOCUMENTS.get(str(body.get("id", "")))
    question = str(body.get("question", "")).strip()[:MAX_QUESTION_CHARS]
    if document is None:
        return error("Document not found. Please upload it again.", 404)
    if not question:
        return error("Please type a question.", 400)

    matches = search(document["chunks"], question)
    return jsonify(matches=matches, message="" if matches else NOT_FOUND_MESSAGE)


if __name__ == "__main__":
    app.run(debug=False)
