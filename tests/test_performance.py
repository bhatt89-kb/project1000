"""Performance benchmarks using pytest-benchmark.

These tests measure the performance of critical operations to ensure
efficiency goals are met (sub-second response times for typical documents).
"""

import pytest
from legallens.parser import extract_pages
from legallens.analysis import analyze, summarize, flag_clauses, extract_entities, sentences
from legallens.search import build_chunks, search

# =============================================================================
# FIXTURES - Test Data
# =============================================================================

@pytest.fixture
def small_document_text():
    """Small document (< 1 page)."""
    return """
    RENTAL AGREEMENT
    
    This agreement is between Landlord John Doe and Tenant Jane Smith.
    The monthly rent is ₹18,000 with a security deposit of ₹36,000.
    The lease term is 12 months starting from 01/01/2024.
    The notice period for termination is 30 days.
    
    The tenant shall maintain the property in good condition and pay rent on time.
    The landlord may terminate this agreement for violation of any clause.
    Late payment will result in a penalty of ₹500 per day.
    """


@pytest.fixture
def medium_document_text():
    """Medium document (5-10 pages)."""
    base_text = """
    COMMERCIAL LEASE AGREEMENT
    
    This lease agreement is made between ABC Properties Limited (Landlord) 
    and XYZ Corporation (Tenant) on this 15th day of March 2024.
    
    PROPERTY DESCRIPTION:
    The leased premises consist of 2,500 square feet of office space located 
    at 123 Business Park, Suite 400, Mumbai, Maharashtra.
    
    TERM: The initial term shall be 36 months commencing on April 1, 2024.
    
    RENT: Monthly rent is ₹75,000 plus applicable taxes. Security deposit: ₹225,000.
    
    RENEWAL: This agreement shall automatically renew for successive 12-month periods
    unless either party provides written notice of non-renewal 90 days prior to expiration.
    
    MAINTENANCE: Tenant is responsible for interior maintenance. Landlord maintains exterior.
    
    INSURANCE: Tenant must maintain liability insurance with minimum coverage of ₹1,00,00,000.
    
    TERMINATION: Either party may terminate with 60 days written notice.
    Tenant shall forfeit security deposit if terminating before 24 months.
    
    INDEMNIFICATION: Tenant shall indemnify and hold harmless Landlord from all claims.
    
    DISPUTE RESOLUTION: Any disputes shall be resolved through binding arbitration in Mumbai.
    
    ASSIGNMENT: Tenant may not assign or sublease without Landlord's written consent.
    
    FORCE MAJEURE: Neither party shall be liable for delays due to acts of God.
    """
    # Repeat to simulate multi-page document
    return base_text * 5


@pytest.fixture
def large_document_text():
    """Large document (20+ pages) for stress testing."""
    base_text = """
    MASTER SERVICE AGREEMENT
    
    Article 1: Definitions and Interpretation
    1.1 In this Agreement, unless the context otherwise requires:
    "Services" means the professional services described in Schedule A.
    "Fees" means the amounts payable as specified in Schedule B.
    "Intellectual Property" means all patents, trademarks, copyrights, and trade secrets.
    
    Article 2: Scope of Services
    2.1 The Provider shall perform the Services with reasonable care and skill.
    2.2 The Provider may engage subcontractors subject to Client approval.
    2.3 The Provider warrants that Services will conform to specifications.
    
    Article 3: Payment Terms
    3.1 Client shall pay fees within 30 days of invoice date.
    3.2 Late payments shall accrue interest at 1.5% per month.
    3.3 Provider may suspend Services for non-payment exceeding 45 days.
    
    Article 4: Confidentiality
    4.1 Each party shall protect Confidential Information of the other party.
    4.2 Confidential Information excludes publicly available information.
    4.3 Confidentiality obligations survive termination for 5 years.
    
    Article 5: Liability and Indemnification
    5.1 Provider's liability is limited to fees paid in preceding 12 months.
    5.2 Provider shall indemnify Client for third-party IP claims.
    5.3 Client shall indemnify Provider for claims arising from Client data.
    
    Article 6: Term and Termination
    6.1 Initial term is 24 months from the Effective Date.
    6.2 Either party may terminate for material breach with 30 days cure period.
    6.3 Client may terminate for convenience with 90 days notice and payment of termination fee.
    
    Article 7: Dispute Resolution
    7.1 Disputes shall be escalated to senior management.
    7.2 If unresolved, disputes shall proceed to mediation.
    7.3 Arbitration shall be conducted under ICC Rules in Singapore.
    
    Article 8: General Provisions
    8.1 This Agreement may only be amended in writing.
    8.2 No waiver of any provision shall constitute waiver of any other provision.
    8.3 If any provision is invalid, remaining provisions continue in effect.
    8.4 This Agreement is governed by the laws of Singapore.
    """
    # Repeat to simulate 20+ page document
    return base_text * 10


@pytest.fixture
def sample_chunks():
    """Pre-built chunks for search benchmarking."""
    return [
        {
            "text": "The monthly rent is ₹18,000 payable on the 1st of each month.",
            "page": 1,
            "clause": "3.1"
        },
        {
            "text": "Security deposit of ₹36,000 shall be refundable upon lease termination.",
            "page": 1,
            "clause": "3.2"
        },
        {
            "text": "Either party may terminate this agreement with 30 days written notice.",
            "page": 2,
            "clause": "8.1"
        },
        {
            "text": "Late payment penalty is ₹500 per day after the due date.",
            "page": 1,
            "clause": "3.3"
        },
        {
            "text": "The tenant shall maintain the property and make no alterations without consent.",
            "page": 2,
            "clause": "5.2"
        },
    ] * 20  # 100 chunks total


# =============================================================================
# PARSER BENCHMARKS
# =============================================================================

def test_benchmark_extract_pages_small_text(benchmark, small_document_text):
    """Benchmark: Extract pages from small text document."""
    result = benchmark(extract_pages, "test.txt", small_document_text.encode('utf-8'))
    assert len(result) >= 1


def test_benchmark_extract_pages_medium_text(benchmark, medium_document_text):
    """Benchmark: Extract pages from medium text document."""
    result = benchmark(extract_pages, "test.txt", medium_document_text.encode('utf-8'))
    assert len(result) >= 1


def test_benchmark_extract_pages_large_text(benchmark, large_document_text):
    """Benchmark: Extract pages from large text document."""
    result = benchmark(extract_pages, "test.txt", large_document_text.encode('utf-8'))
    assert len(result) >= 1


# =============================================================================
# ANALYSIS BENCHMARKS
# =============================================================================

def test_benchmark_sentences_small(benchmark, small_document_text):
    """Benchmark: Split small text into sentences."""
    result = benchmark(sentences, small_document_text)
    assert isinstance(result, list)


def test_benchmark_sentences_large(benchmark, large_document_text):
    """Benchmark: Split large text into sentences."""
    result = benchmark(sentences, large_document_text)
    assert isinstance(result, list)


def test_benchmark_summarize_small(benchmark, small_document_text):
    """Benchmark: Summarize small document."""
    result = benchmark(summarize, small_document_text, 1)
    assert "type" in result


def test_benchmark_summarize_medium(benchmark, medium_document_text):
    """Benchmark: Summarize medium document."""
    result = benchmark(summarize, medium_document_text, 5)
    assert "type" in result


def test_benchmark_extract_entities_small(benchmark, small_document_text):
    """Benchmark: Extract entities from small document."""
    result = benchmark(extract_entities, small_document_text)
    assert "dates" in result


def test_benchmark_extract_entities_large(benchmark, large_document_text):
    """Benchmark: Extract entities from large document."""
    result = benchmark(extract_entities, large_document_text)
    assert "dates" in result


def test_benchmark_flag_clauses_small(benchmark):
    """Benchmark: Flag clauses in small chunk set."""
    chunks = [
        {"text": "The tenant shall indemnify the landlord for all damages.", "page": 1, "clause": "1"},
        {"text": "Monthly rent is ₹18,000 due on the 1st.", "page": 1, "clause": "2"},
        {"text": "Termination requires 30 days notice.", "page": 1, "clause": "3"},
    ]
    result = benchmark(flag_clauses, chunks)
    assert isinstance(result, list)


def test_benchmark_flag_clauses_large(benchmark, sample_chunks):
    """Benchmark: Flag clauses in large chunk set."""
    result = benchmark(flag_clauses, sample_chunks)
    assert isinstance(result, list)


def test_benchmark_analyze_end_to_end_small(benchmark, small_document_text):
    """Benchmark: Full analysis pipeline on small document."""
    pages = [small_document_text]
    chunks = build_chunks(pages)
    result = benchmark(analyze, pages, chunks)
    assert "summary" in result


def test_benchmark_analyze_end_to_end_medium(benchmark, medium_document_text):
    """Benchmark: Full analysis pipeline on medium document."""
    pages = [medium_document_text[i:i+2000] for i in range(0, len(medium_document_text), 2000)]
    chunks = build_chunks(pages)
    result = benchmark(analyze, pages, chunks)
    assert "summary" in result


def test_benchmark_analyze_end_to_end_large(benchmark, large_document_text):
    """Benchmark: Full analysis pipeline on large document."""
    pages = [large_document_text[i:i+2000] for i in range(0, len(large_document_text), 2000)]
    chunks = build_chunks(pages)
    result = benchmark(analyze, pages, chunks)
    assert "summary" in result


# =============================================================================
# SEARCH BENCHMARKS
# =============================================================================

def test_benchmark_search_single_keyword(benchmark, sample_chunks):
    """Benchmark: Search with single keyword."""
    result = benchmark(search, sample_chunks, "rent")
    assert isinstance(result, list)


def test_benchmark_search_multiple_keywords(benchmark, sample_chunks):
    """Benchmark: Search with multiple keywords."""
    result = benchmark(search, sample_chunks, "rent payment deposit")
    assert isinstance(result, list)


def test_benchmark_search_complex_query(benchmark, sample_chunks):
    """Benchmark: Search with complex multi-word query."""
    result = benchmark(search, sample_chunks, "termination notice period requirements")
    assert isinstance(result, list)


def test_benchmark_search_no_match(benchmark, sample_chunks):
    """Benchmark: Search with no matches (worst case)."""
    result = benchmark(search, sample_chunks, "xyzabc nonexistent query")
    assert result == []


# =============================================================================
# MEMORY BENCHMARKS (Using tracemalloc)
# =============================================================================

def test_memory_usage_large_document(large_document_text):
    """Memory test: Verify large document doesn't exceed memory limits."""
    import tracemalloc
    
    tracemalloc.start()
    
    pages = [large_document_text[i:i+2000] for i in range(0, len(large_document_text), 2000)]
    chunks = build_chunks(pages)
    result = analyze(pages, chunks)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Peak memory should be under 50 MB for large document
    assert peak < 50 * 1024 * 1024, f"Peak memory usage: {peak / (1024*1024):.2f} MB"
    assert "summary" in result


# =============================================================================
# REGRESSION BENCHMARKS (Compare to Baseline)
# =============================================================================

@pytest.mark.benchmark(group="analysis-pipeline")
def test_baseline_full_analysis_1page(benchmark, small_document_text):
    """Baseline: 1-page document analysis (target: < 100ms)."""
    pages = [small_document_text]
    chunks = build_chunks(pages)
    result = benchmark(analyze, pages, chunks)
    assert "findings" in result


@pytest.mark.benchmark(group="analysis-pipeline")
def test_baseline_full_analysis_5pages(benchmark, medium_document_text):
    """Baseline: 5-page document analysis (target: < 500ms)."""
    pages = [medium_document_text[i:i+2000] for i in range(0, len(medium_document_text), 2000)]
    chunks = build_chunks(pages)
    result = benchmark(analyze, pages, chunks)
    assert "findings" in result


@pytest.mark.benchmark(group="search")
def test_baseline_search_100chunks(benchmark, sample_chunks):
    """Baseline: Search across 100 chunks (target: < 50ms)."""
    result = benchmark(search, sample_chunks, "rent payment")
    assert isinstance(result, list)


# =============================================================================
# PERFORMANCE ASSERTIONS
# =============================================================================

def test_performance_goals_met(small_document_text):
    """Verify that performance goals are met for typical use case."""
    import time
    
    # Goal: Analyze 1-page document in under 100ms
    pages = [small_document_text]
    chunks = build_chunks(pages)
    
    start = time.perf_counter()
    result = analyze(pages, chunks)
    duration = time.perf_counter() - start
    
    assert duration < 0.1, f"Analysis took {duration*1000:.2f}ms (goal: < 100ms)"
    assert "findings" in result


if __name__ == "__main__":
    # Run with: pytest test_performance.py -v --benchmark-only --benchmark-autosave
    pytest.main([__file__, "-v", "--benchmark-only", "--benchmark-autosave"])
