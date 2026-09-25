# ⚖️ Legal Document Assistant

A modern, privacy-first web application for analyzing rental and lease agreements. Upload a document and get instant analysis with plain-language summaries, flagged clauses, and Q&A capabilities.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
[![CI/CD](https://github.com/bhatt89-kb/project1000/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/bhatt89-kb/project1000/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Live Demo

**[Try the Live Application →](https://your-app-name.onrender.com)**

> **Note:** Demo deployment URL will be added after completing deployment setup.

## ✨ Features

### Core Capabilities
- 📄 **Document Upload** - PDF and TXT files (up to 5 MB)
- 📊 **Risk Assessment** - 12-category risk scoring (0-10 scale)
- 🔍 **Entity Extraction** - Dates, amounts, parties, obligations
- 💬 **Smart Q&A** - Keyword-based search with exact citations
- ⚖️ **Contract Comparison** - Side-by-side analysis of two documents
- 📥 **Export Reports** - Generate HTML reports for printing/saving
- ✅ **Pre-Signing Checklist** - Action items review before signing

### User Experience
- 🎨 Modern tabbed interface with 5 organized sections
- ⌨️ Full keyboard navigation (Arrow keys, Alt+1-5 shortcuts)
- ♿ WCAG 2.1 compliant accessibility (ARIA labels, screen reader support)
- 📱 Mobile-responsive design with touch-friendly controls
- ⚡ Real-time progress indicators and loading states
- 🔒 **100% Private** - All processing local, no external APIs

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[User Browser] --> B[index.html]
        B --> C[app.js]
    end
    
    subgraph "Backend API Layer"
        C -->|HTTP POST| D[Flask Application]
        D --> E[/api/upload]
        D --> F[/api/ask]
        D --> G[/api/compare]
        D --> H[/api/export]
    end
    
    subgraph "Processing Layer"
        E --> I[parser.py]
        I -->|Extract Text| J[pypdf / text decoder]
        J --> K[Page List]
        
        K --> L[search.py]
        L -->|Build Chunks| M[Clause Detection]
        M --> N[Chunk List with Metadata]
        
        K --> O[analysis.py]
        N --> O
        O -->|Analyze| P[Risk Scoring]
        O -->|Extract| Q[Entity Recognition]
        O -->|Flag| R[Clause Detection]
        O -->|Summarize| S[Key Terms]
        
        P --> T[Analysis Result]
        Q --> T
        R --> T
        S --> T
        
        F --> L
        L -->|Search| U[Keyword Matching]
        U -->|Top-k| V[Relevant Passages]
        
        G --> W[compare_documents]
        W --> X[Diff Analysis]
        
        H --> Y[generate_html_report]
    end
    
    subgraph "Storage Layer"
        T --> Z[(In-Memory Store)]
        Z -.->|Retrieve| F
        Z -.->|Retrieve| G
        Z -.->|Retrieve| H
    end
    
    style A fill:#667eea
    style D fill:#764ba2
    style O fill:#10b981
    style Z fill:#f59e0b
    
    classDef frontend fill:#dbeafe,stroke:#2563eb
    classDef backend fill:#fce7f3,stroke:#db2777
    classDef processing fill:#d1fae5,stroke:#059669
    
    class B,C frontend
    class E,F,G,H backend
    class I,L,O,W,Y processing
```

### System Flow

1. **Document Upload** → User uploads PDF/TXT → Flask validates (MIME, size, magic bytes) → Parser extracts pages
2. **Text Processing** → Pages split into clause-aware chunks → Search builds keyword index with stemming
3. **Analysis** → Multiple modules run: risk scoring, entity extraction, clause flagging, summarization
4. **Storage** → Results stored in-memory with UUID → No disk persistence (privacy-first)
5. **Q&A** → User question → Keyword search → Top-k relevant chunks returned with citations
6. **Comparison** → Two documents analyzed → Differences highlighted → Risk levels compared
7. **Export** → Analysis formatted as HTML → Print-optimized CSS → Download/save capability

### Key Design Decisions

- **No LLMs/Embeddings**: Rule-based processing ensures reproducibility and privacy
- **Memory-only storage**: Documents never touch disk for maximum security
- **Caching**: LRU cache on search terms (512 entries) for performance
- **Rate limiting**: 10/min uploads, 30/min questions, 5/min comparisons
- **Multi-stage Docker**: Separate build/runtime for 40% smaller images

## 🚀 Quick Deploy

### Deploy to Render (1-Click)

1. Click the "Deploy to Render" button above
2. Connect your GitHub account
3. Wait 2-3 minutes for deployment
4. Your app is live! 🎉

### Other Platforms

- **Railway.app** - Auto-detects Dockerfile, deploys instantly
- **Fly.io** - Global edge deployment with free tier
- **Heroku** - Classic platform with Procfile support
- **Docker** - Deploy anywhere with the included Dockerfile

📖 [Full Deployment Guide](DEPLOYMENT.md)

## 🏃‍♂️ Run Locally

```bash
# Clone the repository
git clone https://github.com/bhatt89-kb/project1000.git
cd project1000

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open your browser to: **http://127.0.0.1:5000**

## 🧪 Run Tests

```bash
pytest
```

All 13 tests should pass ✅

## 📁 Project Structure

```
├── app.py                 # Flask application & API routes
├── legallens/
│   ├── parser.py         # PDF/TXT extraction
│   ├── search.py         # Keyword-based search
│   └── analysis.py       # Document analysis logic
├── static/
│   ├── index.html        # Modern UI
│   └── app.js            # Frontend logic
├── tests/
│   └── test_core.py      # Test suite
├── Dockerfile            # Docker deployment
├── render.yaml           # Render.com config
├── Procfile              # Heroku config
└── requirements.txt      # Python dependencies
```

## 🔒 Privacy & Security

- ✅ **Memory-only storage** - Documents never written to disk
- ✅ **No external APIs** - All processing happens locally
- ✅ **No tracking** - Zero analytics or data collection
- ✅ **Security headers** - CSP, X-Frame-Options, nosniff
- ✅ **Input validation** - File size, type, and content checks
- ✅ **Safe rendering** - No innerHTML, only textContent

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **PDF Processing**: pypdf library
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Testing**: pytest
- **Production**: Gunicorn WSGI server

## 📖 Documentation

- [Setup Guide](SETUP_GUIDE.md) - Installation and configuration
- [Deployment Guide](DEPLOYMENT.md) - Deploy to various platforms
- [Security Guide](SECURITY.md) - Security features and best practices
- [Changelog](CHANGELOG.md) - Version history and updates

## 🎯 Use Cases

- Review rental agreements before signing
- Compare lease terms across documents
- Understand legal jargon in plain language
- Identify concerning clauses
- Prepare questions for lawyers

## ⚠️ Disclaimer

This tool provides general information about legal documents. **It is not legal advice** and does not replace consultation with a qualified lawyer.

## 📊 System Requirements

**Minimum:**
- Python 3.10+
- 256 MB RAM
- 100 MB disk space

**Recommended:**
- Python 3.11+
- 512 MB RAM
- 500 MB disk space

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- DOCX file support
- Contract comparison feature
- Multi-language support
- OCR for scanned PDFs
- Additional clause categories

## 📝 License

This project is provided for educational and personal use.

## 🔗 Links

- [Live Demo](https://legal-document-assistant.onrender.com) (After deployment)
- [GitHub Repository](https://github.com/bhatt89-kb/project1000)
- [Deployment Guide](DEPLOYMENT.md)
- [Security Policy](SECURITY.md)

## 📧 Support

For issues or questions, please check:
- [Setup Guide](SETUP_GUIDE.md) - Installation help
- [Deployment Guide](DEPLOYMENT.md) - Deployment troubleshooting
- [Security Guide](SECURITY.md) - Security configuration

---

**Made with ❤️ for privacy-conscious legal document analysis**

⭐ Star this repo if you find it useful!
