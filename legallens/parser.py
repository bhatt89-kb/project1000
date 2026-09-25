"""Extract page-by-page text from uploaded PDF and TXT files.

This module handles document parsing for legal document analysis. It supports
PDF and plain text files, enforcing size limits and validating file types.

Typical usage example:
    ```python
    with open('contract.pdf', 'rb') as f:
        pages = extract_pages('contract.pdf', f.read())
    ```
"""

import io
from typing import List

from pypdf import PdfReader

ALLOWED_EXTENSIONS = (".pdf", ".txt")
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class UnsupportedFileError(ValueError):
    """Raised when a file has the wrong type, is too large, or cannot be read.
    
    This exception is raised in the following scenarios:
        - File extension is not .pdf or .txt
        - File size exceeds MAX_BYTES (5 MB)
        - PDF structure is malformed or corrupted
        - PDF contains no extractable text (scanned images)
    
    Attributes:
        message: Human-readable error description
    """


def extract_pages(filename: str, data: bytes) -> List[str]:
    """Extract text content from uploaded document, page by page.
    
    Processes PDF and TXT files, returning a list where each element represents
    one page of text content. For TXT files, the entire content is returned as
    a single-element list.
    
    Args:
        filename: Original filename with extension (e.g., 'lease.pdf')
        data: Raw file bytes read from upload
    
    Returns:
        List of strings, one per page. Empty pages return empty strings.
        For TXT files, returns single-element list.
    
    Raises:
        UnsupportedFileError: If file extension is invalid
        UnsupportedFileError: If file size exceeds 5 MB
        UnsupportedFileError: If PDF is malformed or unreadable
        UnsupportedFileError: If PDF contains no extractable text
    
    Example:
        >>> data = open('contract.pdf', 'rb').read()
        >>> pages = extract_pages('contract.pdf', data)
        >>> len(pages)
        12
        >>> pages[0][:50]
        'RESIDENTIAL LEASE AGREEMENT\nThis lease is entered...'
    
    Notes:
        - Scanned PDFs without text layers are rejected
        - Text extraction may vary based on PDF structure
        - UTF-8 decoding is used for TXT files with error replacement
    """
    name = filename.lower()
    
    # Validate file extension
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise UnsupportedFileError(
            f"Only PDF and TXT files are supported. Got: {filename}"
        )
    
    # Validate file size
    if len(data) > MAX_BYTES:
        size_mb = len(data) / (1024 * 1024)
        raise UnsupportedFileError(
            f"The file is larger than 5 MB. Got: {size_mb:.2f} MB"
        )

    # Handle plain text files
    if name.endswith(".txt"):
        try:
            return [data.decode("utf-8", errors="replace")]
        except Exception as exc:
            raise UnsupportedFileError(
                "Text file could not be decoded as UTF-8"
            ) from exc

    # Handle PDF files
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # malformed PDFs can raise many different error types
        raise UnsupportedFileError(
            "This PDF could not be read. It may be corrupted or password-protected."
        ) from exc

    # Verify PDF contains extractable text
    if not any(page.strip() for page in pages):
        raise UnsupportedFileError(
            "No text was found. Scanned PDFs without text layers are not supported yet."
        )
    
    return pages
