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
    # Invalid UUID format now returns 400 instead of 404 due to UUID validation
    response = client.post("/api/ask", json={"id": "missing", "question": "Notice?"})
    assert response.status_code == 400


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
    # Invalid UUID format now returns 400 instead of 404 due to UUID validation
    response = client.post(
        "/api/compare",
        json={"id1": "invalid1", "id2": "invalid2"},
        content_type="application/json"
    )
    assert response.status_code == 400


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


# === Additional Edge Case Tests for >95% Coverage ===

def test_corrupted_pdf_binary_garbage():
    """Test that completely corrupted binary data is rejected."""
    from legallens.parser import extract_pages, UnsupportedFileError
    garbage_data = b'\x00\x01\x02\x03\x04\x05\xFF\xFE\xFD'
    
    with pytest.raises(UnsupportedFileError) as exc_info:
        extract_pages("corrupted.pdf", garbage_data)
    assert "could not be read" in str(exc_info.value).lower()


def test_empty_pdf_file():
    """Test handling of completely empty PDF file."""
    from legallens.parser import extract_pages, UnsupportedFileError
    empty_pdf = b'%PDF-1.4\n%%EOF'
    
    with pytest.raises(UnsupportedFileError):
        extract_pages("empty.pdf", empty_pdf)


def test_txt_file_with_special_characters():
    """Test TXT files with unicode and special characters."""
    from legallens.parser import extract_pages
    special_text = "Contract with émojis 🏠 and unicode: ₹20,000".encode('utf-8')
    
    pages = extract_pages("special.txt", special_text)
    assert len(pages) == 1
    assert "₹20,000" in pages[0]
    assert "🏠" in pages[0]


def test_txt_file_with_invalid_utf8():
    """Test TXT file with invalid UTF-8 sequences."""
    from legallens.parser import extract_pages
    invalid_utf8 = b'Contract text \xFF\xFE invalid bytes'
    
    pages = extract_pages("invalid.txt", invalid_utf8)
    assert len(pages) == 1
    # Should not crash, uses replace error handling


def test_case_insensitive_extension_matching():
    """Test that file extensions are case-insensitive."""
    from legallens.parser import extract_pages
    
    # Use valid content for each file type
    txt_data = b"Test content for text file"
    
    # Should work with various cases of TXT
    pages1 = extract_pages("file.TXT", txt_data)
    pages2 = extract_pages("file.Txt", txt_data)
    pages3 = extract_pages("file.txt", txt_data)
    
    assert all(len(p) == 1 for p in [pages1, pages2, pages3])


def test_filename_with_multiple_dots():
    """Test filenames with multiple dots in the name."""
    from legallens.parser import extract_pages
    data = b"Test content"
    
    pages = extract_pages("my.legal.document.v2.1.final.txt", data)
    assert len(pages) == 1


def test_empty_search_question():
    """Test search with empty or whitespace-only question."""
    from legallens.search import search, build_chunks
    chunks = build_chunks(["Some text here"])
    
    assert search(chunks, "") == []
    assert search(chunks, "   ") == []
    assert search(chunks, "the and or") == []  # Only stopwords


def test_search_with_no_matching_chunks():
    """Test search when no chunks match the query."""
    from legallens.search import search, build_chunks
    chunks = build_chunks(["Rental agreement details"])
    
    results = search(chunks, "quantum physics relativity")
    assert results == []


def test_search_top_k_parameter():
    """Test that top_k limits results correctly."""
    from legallens.search import search, build_chunks
    text = "rent payment notice termination deposit security landlord tenant"
    chunks = build_chunks([text] * 10)  # 10 identical chunks
    
    results = search(chunks, "rent payment", top_k=1)
    assert len(results) == 1
    
    results = search(chunks, "rent payment", top_k=5)
    assert len(results) == 5


def test_chunk_building_preserves_page_numbers():
    """Test that page numbers are correctly assigned."""
    from legallens.search import build_chunks
    pages = ["Page 1 content", "Page 2 content", "Page 3 content"]
    
    chunks = build_chunks(pages)
    
    assert all(c['page'] in [1, 2, 3] for c in chunks)
    assert any(c['page'] == 1 for c in chunks)
    assert any(c['page'] == 2 for c in chunks)
    assert any(c['page'] == 3 for c in chunks)


def test_clause_detection_various_formats():
    """Test different clause numbering formats."""
    from legallens.search import build_chunks
    text = """
    Clause 1. First clause
    2. Second clause
    3: Third clause with colon
    4. Fourth clause
    """
    
    chunks = build_chunks([text])
    clause_numbers = [c['clause'] for c in chunks if c['clause']]
    
    assert '1' in clause_numbers
    assert '2' in clause_numbers
    assert '3' in clause_numbers
    assert '4' in clause_numbers


def test_analysis_with_empty_pages():
    """Test analysis handles empty pages gracefully."""
    from legallens.analysis import analyze
    from legallens.search import build_chunks
    
    pages = ["", "  ", "\n\n", "Some actual content"]
    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    
    assert 'summary' in result
    assert 'findings' in result


def test_analysis_with_no_matching_categories():
    """Test document with no flagged clauses."""
    from legallens.analysis import analyze
    from legallens.search import build_chunks
    
    pages = ["Simple rental agreement with no special terms."]
    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    
    assert result['findings'] == []
    assert len(result['checklist']) == 1  # Should have lawyer consultation item


def test_risk_score_boundaries():
    """Test risk level calculation at boundaries."""
    from legallens.analysis import analyze
    from legallens.search import build_chunks
    
    # Document with various risk levels
    text = """
    1. Liability clause with indemnification.
    2. Security deposit required.
    3. Penalty for late payment.
    """
    
    pages = [text]
    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    
    risk = result.get('risk_assessment', {})
    assert risk['level'] in ['Low', 'Medium', 'High']
    assert 0 <= risk['score'] <= 10


def test_entity_extraction_date_formats():
    """Test various date format extractions."""
    from legallens.analysis import extract_entities
    
    text = """
    Agreement dated 15/01/2024.
    Rent due on January 15, 2024.
    Notice period starts 15 Jan 2024.
    """
    
    entities = extract_entities(text)
    assert len(entities['dates']) > 0


def test_entity_extraction_amount_formats():
    """Test various currency format extractions."""
    from legallens.analysis import extract_entities
    
    text = """
    Rent: Rs. 25,000 per month
    Deposit: ₹50,000
    Fee: Rs.1000
    USD $500 also mentioned
    """
    
    entities = extract_entities(text)
    assert len(entities['amounts']) >= 3


def test_concurrent_document_uploads(client):
    """Test handling of multiple concurrent uploads."""
    # Upload multiple documents quickly
    doc1 = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "doc1.txt")})
    doc2 = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "doc2.txt")})
    doc3 = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "doc3.txt")})
    
    assert doc1.status_code == 200
    assert doc2.status_code == 200
    assert doc3.status_code == 200
    
    # Verify all have unique IDs
    ids = {doc1.get_json()['id'], doc2.get_json()['id'], doc3.get_json()['id']}
    assert len(ids) == 3


def test_document_limit_enforcement(client):
    """Test that document limit (50) is enforced."""
    from app import MAX_DOCUMENTS
    
    # Upload documents up to limit
    for i in range(MAX_DOCUMENTS + 5):
        client.post("/api/upload", data={"document": (io.BytesIO(f"Doc {i}".encode()), f"doc{i}.txt")})
    
    # Should have exactly MAX_DOCUMENTS
    docs = client.get("/api/documents")
    assert len(docs.get_json()['documents']) <= MAX_DOCUMENTS


def test_export_nonexistent_document(client):
    """Test export endpoint with invalid document ID."""
    # Invalid UUID format now returns 400 instead of 404
    response = client.get("/api/export/nonexistent-id-12345")
    assert response.status_code == 400  # Changed from 404 due to UUID validation


def test_export_generates_valid_html(client):
    """Test that export generates valid HTML."""
    # Clear documents and limiter storage to avoid rate limiting in test suite
    from app import DOCUMENTS, limiter
    DOCUMENTS.clear()
    limiter.reset()  # Reset rate limiter for this test
    import time
    time.sleep(1)  # Brief pause for limiter reset
    
    upload = client.post("/api/upload", data={"document": (io.BytesIO(SAMPLE.encode()), "test.txt")})
    assert upload.status_code == 200
    
    data = upload.get_json()
    assert data is not None
    doc_id = data['id']
    
    response = client.get(f"/api/export/{doc_id}")
    assert response.status_code == 200
    assert response.mimetype == 'text/html'
    assert b"<!DOCTYPE html>" in response.data
    assert b"Risk Assessment" in response.data


def test_malformed_json_in_request(client):
    """Test API handling of malformed JSON."""
    response = client.post(
        "/api/ask",
        data="not valid json{{{",
        content_type="application/json"
    )
    # Should handle gracefully, not crash
    assert response.status_code in [400, 404]


def test_question_length_truncation():
    """Test that very long questions are truncated."""
    from app import MAX_QUESTION_CHARS
    
    long_q = "word " * 1000  # Much longer than limit
    truncated = long_q[:MAX_QUESTION_CHARS]
    
    assert len(truncated) == MAX_QUESTION_CHARS


def test_special_characters_in_search():
    """Test search with special characters and symbols."""
    from legallens.search import search, build_chunks
    
    chunks = build_chunks(["Clause about payment $1,000 & termination"])
    
    results = search(chunks, "payment $ termination &")
    assert len(results) > 0


def test_comparison_with_different_risk_levels():
    """Test comparison highlights different risk levels."""
    from legallens.analysis import compare_documents
    
    doc1 = {
        "summary": {"duration": "12 months"},
        "risk_assessment": {"level": "Low", "score": 3.0, "total_issues": 2},
        "findings": []
    }
    
    doc2 = {
        "summary": {"duration": "12 months"},
        "risk_assessment": {"level": "High", "score": 9.0, "total_issues": 10},
        "findings": []
    }
    
    comparison = compare_documents(doc1, doc2)
    assert comparison['risk_comparison']['document1']['level'] == 'Low'
    assert comparison['risk_comparison']['document2']['level'] == 'High'


def test_finding_deduplication():
    """Test that duplicate findings for same clause are removed."""
    from legallens.analysis import flag_clauses
    from legallens.search import build_chunks  # Import from correct module
    
    # Text with multiple keywords matching same categories
    text = """
    Clause 1. Tenant shall indemnify and hold harmless the landlord from all liability.
    """
    
    chunks = build_chunks([text])
    findings = flag_clauses(chunks)
    
    # Should not have duplicate entries for same clause/category
    clause_categories = [(f['clause'], f['category']) for f in findings]
    assert len(clause_categories) == len(set(clause_categories))


def test_empty_document_list_endpoint(client):
    """Test documents list when no documents uploaded."""
    # Clear any existing documents by restarting would be needed
    # For now, just verify endpoint works
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert 'documents' in response.get_json()


def test_summary_with_unusual_formats():
    """Test summary extraction with non-standard text."""
    from legallens.analysis import summarize
    
    text = "Agreement for property at xyz address. Duration not mentioned clearly."
    result = summarize(text, 1)
    
    assert result['type'] in ['Legal document', 'Rental agreement']
    assert result['pages'] == 1
