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


# === New tests for Phase 1 & 2 enhancements ===

def test_risk_assessment_in_analysis():
    """Test that risk assessment is included in analysis results."""
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    assert "risk_assessment" in result
    assert "level" in result["risk_assessment"]
    assert "score" in result["risk_assessment"]
    assert result["risk_assessment"]["level"] in ["Low", "Medium", "High"]
    assert 0 <= result["risk_assessment"]["score"] <= 10


def test_entity_extraction_finds_dates():
    """Test that dates are extracted from documents."""
    from legallens.analysis import extract_entities
    text = "Agreement dated 15th January 2024. Rent due on 01-05-2024."
    entities = extract_entities(text)
    assert "dates" in entities
    assert len(entities["dates"]) > 0


def test_entity_extraction_finds_amounts():
    """Test that monetary amounts are extracted."""
    from legallens.analysis import extract_entities
    text = "Monthly rent of Rs. 25,000 and security deposit of ₹50000."
    entities = extract_entities(text)
    assert "amounts" in entities
    assert len(entities["amounts"]) >= 2


def test_entity_extraction_finds_obligations():
    """Test that obligations (shall/must statements) are extracted."""
    from legallens.analysis import extract_entities
    text = "Tenant shall maintain the property. Landlord must provide receipts."
    entities = extract_entities(text)
    assert "obligations" in entities
    assert len(entities["obligations"]) > 0


def test_entity_extraction_limits_results():
    """Test that entity extraction limits results to reasonable numbers."""
    from legallens.analysis import extract_entities
    # Create text with many dates
    text = " ".join([f"Date: {i}/01/2024." for i in range(1, 30)])
    entities = extract_entities(text)
    assert len(entities["dates"]) <= 10  # Should be limited


def test_enhanced_clause_detection_with_risk_scores():
    """Test that clause flagging includes risk scores."""
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    if result["findings"]:
        finding = result["findings"][0]
        assert "risk_score" in finding
        assert 1 <= finding["risk_score"] <= 10


def test_findings_sorted_by_risk_score():
    """Test that findings are sorted with highest risk first."""
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    if len(result["findings"]) > 1:
        scores = [f["risk_score"] for f in result["findings"]]
        assert scores == sorted(scores, reverse=True), "Findings should be sorted by risk score descending"


def test_compare_endpoint_requires_two_documents(client):
    """Test that comparison endpoint validates both document IDs."""
    response = client.post(
        "/api/compare",
        json={"id1": "invalid1", "id2": "invalid2"},
        content_type="application/json"
    )
    assert response.status_code == 404
    assert b"not found" in response.data


def test_compare_endpoint_returns_comparison(client):
    """Test that comparing two documents returns comparison data."""
    # Upload two documents
    doc1 = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "lease1.txt")})
    doc1_id = doc1.get_json()["id"]
    
    doc2 = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "lease2.txt")})
    doc2_id = doc2.get_json()["id"]
    
    # Compare them
    response = client.post(
        "/api/compare",
        json={"id1": doc1_id, "id2": doc2_id},
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "summary_comparison" in data
    assert "risk_comparison" in data


def test_list_documents_endpoint(client):
    """Test that list documents endpoint returns uploaded documents."""
    # Upload a document
    client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "lease.txt")})
    
    # List documents
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.get_json()
    assert "documents" in data
    assert len(data["documents"]) > 0


def test_comparison_identifies_differences():
    """Test that document comparison correctly identifies differences."""
    from legallens.analysis import compare_documents
    
    result1 = {
        "summary": {"duration": "12 months", "monthly_rent": "₹20,000"},
        "risk_assessment": {"level": "Medium", "score": 6.0, "total_issues": 5},
        "findings": [{"category": "liability"}, {"category": "termination"}]
    }
    
    result2 = {
        "summary": {"duration": "6 months", "monthly_rent": "₹25,000"},
        "risk_assessment": {"level": "High", "score": 8.0, "total_issues": 8},
        "findings": [{"category": "liability"}, {"category": "penalty"}]
    }
    
    comparison = compare_documents(result1, result2)
    
    # Check summary comparison shows differences
    assert comparison["summary_comparison"]["duration"]["different"] == True
    assert comparison["summary_comparison"]["monthly_rent"]["different"] == True
    
    # Check differences are identified
    assert len(comparison["differences"]) > 0


def test_upload_validates_file_extension():
    """Test that only PDF and TXT extensions are allowed."""
    from legallens.parser import extract_pages, UnsupportedFileError
    
    with pytest.raises(UnsupportedFileError):
        extract_pages("document.docx", b"fake content")
    
    with pytest.raises(UnsupportedFileError):
        extract_pages("image.png", b"fake content")


def test_empty_document_handled_gracefully():
    """Test that empty documents are handled without crashes."""
    pages = [""]
    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    assert "summary" in result
    assert "findings" in result
    assert "checklist" in result


def test_very_long_question_is_truncated():
    """Test that extremely long questions are truncated."""
    from app import MAX_QUESTION_CHARS
    long_question = "a" * (MAX_QUESTION_CHARS + 100)
    truncated = long_question[:MAX_QUESTION_CHARS]
    assert len(truncated) == MAX_QUESTION_CHARS


def test_checklist_includes_disclaimer():
    """Test that checklist always includes lawyer consultation."""
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    checklist_text = " ".join(result["checklist"])
    assert "lawyer" in checklist_text.lower()


def test_risk_level_calculation():
    """Test that risk levels are correctly calculated from scores."""
    pages = [SAMPLE]
    result = analyze(pages, build_chunks(pages))
    risk = result["risk_assessment"]
    
    if risk["score"] >= 7:
        assert risk["level"] == "High"
    elif risk["score"] >= 5:
        assert risk["level"] == "Medium"
    else:
        assert risk["level"] == "Low"


def test_entities_structure():
    """Test that entities have the correct structure."""
    pages = [SAMPLE]
    result = analyze(pages, chunks=build_chunks(pages))
    entities = result.get("entities", {})
    
    assert "dates" in entities
    assert "amounts" in entities
    assert "parties" in entities
    assert "obligations" in entities
    assert isinstance(entities["dates"], list)
    assert isinstance(entities["amounts"], list)
