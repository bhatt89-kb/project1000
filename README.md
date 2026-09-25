# Legal Document Assistant

A simple, powerful tool to analyze rental and lease agreements. Upload a document (PDF or TXT) and get:

- **Plain-language summary** - document type, duration, rent, deposit, notice period
- **Flagged clauses** - review categories with clause numbers and page references
- **Action checklist** - items to verify before signing
- **Quick Q&A** - ask questions and get exact passages from your document with citations

**Not legal advice** - Every result is a prompt to review, not a verdict.

## Key Features

✅ **Privacy-first**: Documents stay in memory only, never written to disk  
✅ **Rule-based analysis**: No external APIs, no data leaves your machine  
✅ **Accessible UI**: WCAG compliant with semantic HTML and ARIA labels  
✅ **Security hardened**: Input validation, CSP headers, safe rendering  
✅ **Fast and local**: Instant analysis with keyword-based search  

## Progress

| Feature | Status |
|---|---|
| Upload PDF/TXT with validation | ✅ Complete |
| Text extraction with page numbers | ✅ Complete |
| Plain-language summary | ✅ Complete |
| Clause flagging (7 categories) | ✅ Complete |
| Grounded Q&A with citations | ✅ Complete |
| Action checklist | ✅ Complete |
| Accessible UI | ✅ Complete |
| Security basics | ✅ Complete |
| Automated tests | ✅ Complete |

## How It Works

### Analysis Engine
- **Rule-based detection**: Uses regex patterns to identify document types and key terms
- **Keyword search**: Returns exact passages from your document
- **No AI or external APIs**: Everything runs locally on your machine
- **Privacy guaranteed**: No data transmission, no cloud services

### Security Features

| Security Measure | Implementation |
|---|---|
| File validation | Extension check, 5 MB size limit |
| Memory-only storage | Documents never touch disk |
| Safe rendering | Frontend uses `textContent`, not `innerHTML` |
| HTTP headers | CSP, X-Frame-Options, nosniff |
| Input sanitization | Question length limits, JSON parsing with fallback |

## Installation & Usage

### Quick Start

```bash
# Navigate to project directory
cd legallens-lite

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Then open your browser to: **http://127.0.0.1:5000**

### Run Tests

```bash
python -m pytest
```

All 13 tests should pass.

## Project Structure

```
legallens-lite/
├── app.py                  Flask routes, security headers, document store
├── legallens/
│   ├── parser.py          PDF/TXT text extraction with page numbers
│   ├── search.py          Clause chunking and keyword search
│   └── analysis.py        Summary extraction, clause flagging, checklist
├── static/
│   ├── index.html         Accessible single-page interface
│   └── app.js             Upload, rendering, and Q&A handling
├── tests/
│   └── test_core.py       pytest test suite (13 tests)
├── requirements.txt        Python dependencies
├── pytest.ini             Test configuration
└── README.md              This file
```

## Usage Example

1. **Upload** a rental agreement PDF or TXT file (up to 5 MB)
2. **Review** the plain-language summary of key terms
3. **Check** flagged clauses that may need attention
4. **Ask** questions like "How much notice do I need to give?"
5. **Get** exact passages from your document with clause and page numbers

## Limitations

- **Clause detection**: Works best with clearly numbered clauses (e.g., "4." or "Clause 4")
- **Pattern matching**: Summary uses simple patterns; unusual phrasing may show "Not specified"
- **Keyword search**: Flags may miss clauses written with unusual terminology
- **Scanned PDFs**: Documents without text layers are rejected
- **Language**: English only

## Technology Stack

- **Backend**: Flask (Python web framework)
- **PDF parsing**: pypdf library
- **Testing**: pytest
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Storage**: In-memory only (no database)

## Development

### Adding New Clause Categories

Edit `legallens/analysis.py` and add patterns to the `CATEGORIES` list:

```python
{
    "name": "Your Category",
    "keywords": ["keyword1", "keyword2"],
    "label": "Review",
    "explanation": "Why this clause needs attention"
}
```

### Extending Document Types

Update the `_detect_type()` function in `legallens/analysis.py` to recognize additional patterns.

## Deployment

⚠️ **For local use only** - The built-in Flask server is not production-ready.

For production deployment:
1. Use a WSGI server like `gunicorn` or `uWSGI`
2. Set up HTTPS with valid SSL certificates
3. Configure proper firewall rules
4. Enable rate limiting
5. Set up monitoring and logging

See `SECURITY.md` for detailed deployment guidelines.

## License

This project is provided for educational and personal use.

## Support

For issues or questions, check:
- `SECURITY.md` - Security guidelines
- `SETUP_GUIDE.md` - Installation troubleshooting
- `tests/test_core.py` - Usage examples

---

**Remember**: This tool provides general information, not legal advice. Always consult a qualified lawyer for legal matters.
