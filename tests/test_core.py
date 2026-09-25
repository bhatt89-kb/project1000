import io

import pytest

from app import DOCUMENTS, app
from legallens.analysis import analyze
from legallens.parser import MAX_BYTES, UnsupportedFileError, extract_pages
from legallens.search import build_chunks, search

SAMPLE = """RENTAL AGREEMENT
1. Term
This agreement is for a term of 11 months.
2. Rent
The monthly rent is Rs. 18,000 payable on the 5th.
3. Security Deposit
The tenant pays a security deposit of Rs. 50,000 refundable at the end of the term.
4. Notice and Termination
The tenant must give 2 months notice before terminating this agreement.
5. Automatic Renewal
This agreement renews automatically unless either party objects.
6. Late Payment
A late payment fee of 5% applies after 10 days.
7. Liability
The tenant is liable for damage beyond normal wear and tear.
"""


@pytest.fixture
def client():
    DOCUMENTS.clear()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_txt_is_read_as_one_page():
    assert extract_pages("lease.txt", b"hello") == ["hello"]


def test_unsupported_extension_is_rejected():
    with pytest.raises(UnsupportedFileError):
        extract_pages("malware.exe", b"data")


def test_oversized_file_is_rejected():
    with pytest.raises(UnsupportedFileError):
        extract_pages("lease.txt", b"x" * (MAX_BYTES + 1))


def test_malformed_pdf_is_rejected():
    with pytest.raises(UnsupportedFileError):
        extract_pages("lease.pdf", b"not really a pdf")


def test_chunks_follow_numbered_clauses():
    chunks = build_chunks([SAMPLE])
    clauses = [chunk["clause"] for chunk in chunks]
    assert clauses[:4] == [None, "1", "2", "3"]
    assert all(chunk["page"] == 1 for chunk in chunks)


def test_search_finds_the_notice_clause():
    chunks = build_chunks([SAMPLE])
    top = search(chunks, "How much notice do I need to give before leaving?")[0]
    assert top["clause"] == "4"


def test_search_returns_nothing_for_unrelated_question():
    assert search(build_chunks([SAMPLE]), "Is there a pet clause?") == []


def test_analysis_summary_and_flags():
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    assert result["summary"]["type"] == "Rental agreement"
    assert result["summary"]["duration"] == "11 months"
    assert result["summary"]["monthly_rent"] == "₹18,000"
    assert result["summary"]["security_deposit"] == "₹50,000"
    assert result["summary"]["notice_period"] == "2 months"
    categories = {finding["category"] for finding in result["findings"]}
    assert {"termination", "renewal", "penalty", "liability", "financial"} <= categories
    assert result["checklist"][-1].startswith("Ask a qualified lawyer")


def test_index_page_is_served_with_security_headers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Legal Document Assistant" in response.data
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_upload_then_ask_returns_clause_and_page(client):
    upload = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "lease.txt")})
    assert upload.status_code == 200
    body = upload.get_json()
    ask = client.post("/api/ask", json={"id": body["id"], "question": "How much notice do I need?"})
    match = ask.get_json()["matches"][0]
    assert match["clause"] == "4" and match["page"] == 1


def test_upload_rejects_unsupported_file(client):
    response = client.post("/api/upload", data={"document": (io.BytesIO(b"x"), "photo.png")})
    assert response.status_code == 400
    assert "PDF and TXT" in response.get_json()["error"]


def test_ask_without_match_says_not_found(client):
    upload = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "lease.txt")})
    doc_id = upload.get_json()["id"]
    ask = client.post("/api/ask", json={"id": doc_id, "question": "Is there a pet clause?"})
    assert ask.get_json() == {"matches": [], "message": "I couldn't find this information in the uploaded document."}


def test_ask_with_unknown_document_is_404(client):
    response = client.post("/api/ask", json={"id": "missing", "question": "Notice?"})
    assert response.status_code == 404
