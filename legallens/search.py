"""Split documents into clause-sized chunks and search them by keyword overlap.

This module provides rule-based text chunking and keyword search functionality
for legal documents. No embedding models or LLMs are used, ensuring all results
are exact passages from the uploaded document.

Key features:
    - Clause-aware text chunking with numbered clause detection
    - Keyword-based search with stopword filtering
    - Term stemming (6-character prefix matching)
    - Ranked results by keyword overlap
    - LRU caching for repeated queries (512 cache size)

Typical usage example:
    ```python
    pages = ['Page 1 text...', 'Page 2 text...']
    chunks = build_chunks(pages)
    results = search(chunks, 'What is the notice period?', top_k=3)
    ```
"""

import re
from functools import lru_cache
from typing import List, Dict, Set, Any, Optional, Tuple

# Regex to detect numbered clauses (e.g., "Clause 4", "4.", "4.1:")
CLAUSE_START = re.compile(
    r"^(?:clause\s+(\d+(?:\.\d+)*)|(\d{1,2}(?:\.\d+)*)[.):])\s*",
    re.IGNORECASE
)

# Common words to ignore in keyword matching
STOPWORDS: Set[str] = {
    "the", "and", "for", "are", "with", "that", "this", "from", "what", "how", "does",
    "have", "will", "can", "you", "your", "any", "not", "into", "about", "when", "which",
    "who", "where", "there", "their", "they", "its", "should", "would", "could", "much",
    "many", "need", "must",
}


def _blocks(page_text: str) -> List[str]:
    """Group lines into blocks, starting a new block at each numbered clause.
    
    Splits page text into logical blocks based on clause numbering. A new block
    begins whenever a numbered clause pattern is detected at the start of a line.
    
    Args:
        page_text: Full text content of a single page
    
    Returns:
        List of text blocks, each representing a clause or paragraph
    
    Example:
        >>> text = "Introduction text\\n\\n4. Termination clause\\nDetails here"
        >>> _blocks(text)
        ['Introduction text', '4. Termination clause Details here']
    
    Notes:
        - Empty lines are skipped
        - Lines are joined with spaces within each block
        - Numbered clauses must start at line beginning
    """
    blocks, current = [], []
    
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        
        # Start new block when numbered clause is detected
        if CLAUSE_START.match(line) and current:
            blocks.append(" ".join(current))
            current = []
        
        current.append(line)
    
    # Add final block
    if current:
        blocks.append(" ".join(current))
    
    return blocks


def build_chunks(pages: List[str]) -> List[Dict[str, Any]]:
    """Convert pages into searchable chunks with metadata.
    
    Processes document pages into structured chunks, each containing the text,
    page number, and clause number (if detected). Chunks are clause-aware,
    splitting at numbered clause boundaries.
    
    Args:
        pages: List of page texts from extract_pages()
    
    Returns:
        List of dictionaries, each with keys:
            - text (str): The chunk text content
            - page (int): Page number (1-indexed)
            - clause (str | None): Clause number if detected (e.g., "4", "4.1")
    
    Example:
        >>> pages = ['Page 1 content', 'Clause 2. Text here']
        >>> chunks = build_chunks(pages)
        >>> chunks[0]
        {'text': 'Page 1 content', 'page': 1, 'clause': None}
        >>> chunks[1]
        {'text': 'Clause 2. Text here', 'page': 2, 'clause': '2'}
    
    Notes:
        - Page numbering starts at 1 (not 0)
        - Clause numbers extracted from patterns like "4.", "Clause 4", "4.1:"
        - Chunks without clause numbers have clause=None
    """
    chunks: List[Dict[str, Any]] = []
    
    for page_number, page_text in enumerate(pages, start=1):
        for block in _blocks(page_text):
            # Extract clause number if present
            match = CLAUSE_START.match(block)
            clause: Optional[str] = (match.group(1) or match.group(2)) if match else None
            
            chunks.append({
                "text": block,
                "page": page_number,
                "clause": clause
            })
    
    return chunks


@lru_cache(maxsize=512)
def _terms(text: str) -> frozenset:
    """Extract search terms from text with stemming and stopword filtering.
    
    Cached version with LRU cache to speed up repeated queries and chunk processing.
    Converts text to lowercase keywords, truncates to 6 characters for stemming
    (so 'terminate' matches 'termination'), and removes common stopwords.
    
    Args:
        text: Input text to extract terms from
    
    Returns:
        Frozenset of stemmed, filtered keywords (lowercase, 6-char max)
    
    Example:
        >>> _terms("What is the termination notice period?")
        frozenset({'termin', 'notice', 'period'})
    
    Notes:
        - Only alphanumeric words considered
        - Words must be >2 characters after lowercasing
        - Stopwords like 'the', 'is', 'what' are filtered out
        - 6-character stemming enables fuzzy matching
        - Returns frozenset for hashability (required by lru_cache)
        - Cache size: 512 unique text strings
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return frozenset(
        word[:6] 
        for word in words 
        if len(word) > 2 and word not in STOPWORDS
    )


def search(
    chunks: List[Dict[str, Any]], 
    question: str, 
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """Search chunks for passages matching the question by keyword overlap.
    
    Ranks chunks by the number of shared keywords with the question, returning
    the top_k best matches. Uses stemmed keyword matching without embeddings
    or LLMs, ensuring all results are exact document passages.
    
    Args:
        chunks: List of chunk dictionaries from build_chunks()
        question: User's search query
        top_k: Maximum number of results to return (default: 3)
    
    Returns:
        List of up to top_k chunk dictionaries, ranked by relevance.
        Each contains 'text', 'page', and 'clause' keys.
        Returns empty list if no matches found.
    
    Example:
        >>> chunks = build_chunks(['Clause 4. 30 days notice required'])
        >>> results = search(chunks, 'How much notice do I need?')
        >>> len(results)
        1
        >>> results[0]['text']
        'Clause 4. 30 days notice required'
    
    Notes:
        - Keyword matching is case-insensitive
        - Results sorted by keyword overlap count (descending)
        - Minimum 1 keyword overlap required for match
        - Stopwords filtered from both question and chunks
    """
    wanted = _terms(question)
    
    # No valid search terms extracted
    if not wanted:
        return []
    
    scored: List[tuple[int, Dict[str, Any]]] = []
    
    for chunk in chunks:
        # Count keyword overlap
        overlap = len(wanted & _terms(chunk["text"]))
        
        if overlap:
            scored.append((overlap, chunk))
    
    # Sort by overlap (highest first)
    scored.sort(key=lambda pair: pair[0], reverse=True)
    
    # Return top_k results with metadata
    return [
        {
            "text": chunk["text"],
            "page": chunk["page"],
            "clause": chunk["clause"]
        }
        for _, chunk in scored[:top_k]
    ]
