"""Split documents into clause-sized chunks and search them by keyword overlap.

No embedding model or LLM is used, so answers are always exact passages
from the uploaded document and cannot be invented.
"""

import re

CLAUSE_START = re.compile(r"^(?:clause\s+(\d+(?:\.\d+)*)|(\d{1,2}(?:\.\d+)*)[.):])\s*", re.IGNORECASE)
STOPWORDS = {
    "the", "and", "for", "are", "with", "that", "this", "from", "what", "how", "does",
    "have", "will", "can", "you", "your", "any", "not", "into", "about", "when", "which",
    "who", "where", "there", "their", "they", "its", "should", "would", "could", "much",
    "many", "need", "must",
}


def _blocks(page_text):
    """Group lines into blocks, starting a new block at each numbered clause."""
    blocks, current = [], []
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if CLAUSE_START.match(line) and current:
            blocks.append(" ".join(current))
            current = []
        current.append(line)
    if current:
        blocks.append(" ".join(current))
    return blocks


def build_chunks(pages):
    """Return a list of chunks with text, page number, and clause number (or None)."""
    chunks = []
    for page_number, page_text in enumerate(pages, start=1):
        for block in _blocks(page_text):
            match = CLAUSE_START.match(block)
            clause = (match.group(1) or match.group(2)) if match else None
            chunks.append({"text": block, "page": page_number, "clause": clause})
    return chunks


def _terms(text):
    """Lowercase keywords, shortened to six letters so 'terminate' matches 'termination'."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word[:6] for word in words if len(word) > 2 and word not in STOPWORDS}


def search(chunks, question, top_k=3):
    """Return up to top_k chunks that share at least one keyword with the question."""
    wanted = _terms(question)
    if not wanted:
        return []
    scored = []
    for chunk in chunks:
        overlap = len(wanted & _terms(chunk["text"]))
        if overlap:
            scored.append((overlap, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {"text": chunk["text"], "page": chunk["page"], "clause": chunk["clause"]}
        for _, chunk in scored[:top_k]
    ]
