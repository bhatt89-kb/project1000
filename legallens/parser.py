"""Extract page-by-page text from uploaded PDF and TXT files."""

import io

from pypdf import PdfReader

ALLOWED_EXTENSIONS = (".pdf", ".txt")
MAX_BYTES = 5 * 1024 * 1024


class UnsupportedFileError(ValueError):
    """Raised when a file has the wrong type, is too large, or cannot be read."""


def extract_pages(filename: str, data: bytes) -> list[str]:
    """Return the text of each page. A plain text file counts as one page."""
    name = filename.lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise UnsupportedFileError("Only PDF and TXT files are supported.")
    if len(data) > MAX_BYTES:
        raise UnsupportedFileError("The file is larger than 5 MB.")

    if name.endswith(".txt"):
        return [data.decode("utf-8", errors="replace")]

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # malformed PDFs can raise many different error types
        raise UnsupportedFileError("This PDF could not be read.") from exc

    if not any(page.strip() for page in pages):
        raise UnsupportedFileError("No text was found. Scanned PDFs are not supported yet.")
    return pages
