# Legal Document Assistant - Setup Guide

Quick start guide to get the Legal Document Assistant running on your machine.

## Prerequisites

- **Python 3.10 or higher**
- **pip** (Python package manager)
- **A web browser** (Chrome, Firefox, Safari, or Edge)

## Installation

### Step 1: Navigate to Project Directory

```bash
cd d:\final\legallens-lite\legallens-lite
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **Flask** - Web framework
- **pypdf** - PDF text extraction
- **pytest** - Testing framework

### Step 3: Run the Application

```bash
python app.py
```

You should see:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### Step 4: Open in Browser

Visit: **http://127.0.0.1:5000**

## Using the Application

### 1. Upload a Document

- Click "Choose File" and select a PDF or TXT file
- File must be under 5 MB
- Click "Analyze document"

### 2. Review the Analysis

You'll see:
- **Summary**: Document type, duration, rent, deposit, notice period
- **Flagged Clauses**: Categories that need review (liability, termination, etc.)
- **Checklist**: Action items before signing

### 3. Ask Questions

- Type a question like "How much notice do I need to give?"
- Click "Ask"
- Get exact passages from your document with clause and page numbers

## Running Tests

```bash
python -m pytest
```

Expected output:
```
================ test session starts ================
collected 13 items

tests/test_core.py ............. [100%]

================ 13 passed in 0.5s ================
```

## Features Overview

### Core Capabilities

✅ **Document Analysis**
- Rental and lease agreements
- Plain-language summaries
- Automatic clause detection

✅ **Security & Privacy**
- Documents stay in memory only
- No external API calls
- No data leaves your machine

✅ **Accessibility**
- Screen reader compatible
- Keyboard navigation
- WCAG 2.1 compliant

### Document Support

| Format | Support | Notes |
|---|---|---|
| PDF | ✅ Yes | Text-based PDFs only |
| TXT | ✅ Yes | Plain text files |
| Scanned PDF | ❌ No | No text layer (OCR needed) |
| DOCX | ❌ No | Not yet supported |

## Troubleshooting

### "Module not found" errors

```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### Port 5000 already in use

Edit `app.py` and change the last line:
```python
if __name__ == "__main__":
    app.run(debug=False, port=5001)  # Changed from 5000 to 5001
```

### PDF not parsing correctly

**Possible causes:**
- PDF is scanned (no text layer) - Not supported
- PDF is corrupted - Try re-downloading
- File size over 5 MB - Compress or split the file

**Solutions:**
- Ensure PDF has selectable text
- Try exporting as TXT from your PDF reader
- Check file is under 5 MB limit

### "File too large" error

The maximum file size is **5 MB**. To reduce file size:
- Remove unnecessary pages
- Use PDF compression tools
- Convert to TXT format

### Tests failing

```bash
# Clear pytest cache
python -m pytest --cache-clear

# Run with verbose output
python -m pytest -v

# Run specific test
python -m pytest tests/test_core.py::test_name -v
```

## Configuration Options

### Changing Document Limit

Edit `app.py`:
```python
MAX_DOCUMENTS = 50  # Change to desired number
```

### Changing File Size Limit

Edit `legallens/parser.py`:
```python
MAX_BYTES = 5 * 1024 * 1024  # 5 MB (change as needed)
```

Also update in `app.py`:
```python
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 64 * 1024
```

### Changing Question Length Limit

Edit `app.py`:
```python
MAX_QUESTION_CHARS = 500  # Change to desired length
```

## Directory Structure

```
legallens-lite/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── pytest.ini               # Test configuration
│
├── legallens/               # Core analysis modules
│   ├── __init__.py
│   ├── parser.py           # PDF/TXT extraction
│   ├── search.py           # Keyword search
│   └── analysis.py         # Document analysis
│
├── static/                  # Frontend files
│   ├── index.html          # User interface
│   └── app.js              # Client-side logic
│
└── tests/                   # Test suite
    └── test_core.py        # 13 automated tests
```

## Development Tips

### Hot Reload (Development Mode)

For automatic reloading during development:

```python
# In app.py, change the last line to:
if __name__ == "__main__":
    app.run(debug=True)  # Enables auto-reload
```

⚠️ **Never use debug mode in production!**

### Adding Custom Clause Categories

Edit `legallens/analysis.py` and add to the `CATEGORIES` list:

```python
{
    "name": "Your Category Name",
    "keywords": ["keyword1", "keyword2", "phrase to match"],
    "label": "Review",  # or "Caution", "Note"
    "explanation": "Why this needs attention"
}
```

### Viewing Logs

```python
# Add logging to app.py
import logging
logging.basicConfig(level=logging.INFO)
```

## Next Steps

1. **Upload a test document** - Try with a sample rental agreement
2. **Ask sample questions** - Test the Q&A functionality
3. **Review the code** - Explore `legallens/` modules
4. **Run the tests** - Verify everything works
5. **Read SECURITY.md** - Learn about security features

## Performance Tips

- **Memory usage**: Each document uses ~100-500 KB in memory
- **50 document limit**: Oldest automatically removed
- **Response time**: Analysis takes 1-3 seconds per document
- **Concurrent users**: Flask dev server handles 1 user; use gunicorn for more

## Common Questions

**Q: Is my data secure?**  
A: Yes! Documents stay in memory only and are never written to disk or sent anywhere.

**Q: Can I use this offline?**  
A: Yes! No internet connection required after installation.

**Q: Can I deploy this online?**  
A: Yes, but use a production WSGI server. See `SECURITY.md` for deployment guide.

**Q: Does it work with scanned PDFs?**  
A: No, only text-based PDFs are supported. Scanned PDFs need OCR (not implemented).

**Q: Can I analyze contracts in other languages?**  
A: Currently English only. Keyword patterns would need translation for other languages.

## Getting Help

- **README.md** - Full project documentation
- **SECURITY.md** - Security and deployment guide
- **tests/test_core.py** - Code examples and usage patterns

## System Requirements

**Minimum:**
- Python 3.10+
- 100 MB disk space
- 512 MB RAM

**Recommended:**
- Python 3.11+
- 500 MB disk space
- 1 GB RAM
- Modern web browser

---

**Ready to go!** Start analyzing legal documents with confidence.
