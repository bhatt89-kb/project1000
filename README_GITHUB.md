# ⚖️ Legal Document Assistant

A modern, privacy-first web application for analyzing rental and lease agreements. Upload a document and get instant analysis with plain-language summaries, flagged clauses, and Q&A capabilities.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

## ✨ Features

- 📄 **Document Upload** - Support for PDF and TXT files (up to 5 MB)
- 📊 **Smart Analysis** - Extracts key terms: rent, deposit, duration, notice period
- 🔍 **Clause Detection** - Identifies 7 categories of important clauses
- 💬 **Q&A System** - Ask questions and get exact passages with citations
- ✅ **Pre-Signing Checklist** - Action items to review before signing
- 🔒 **100% Private** - All processing happens locally, no data leaves your machine

## 🎨 Modern UI

- Beautiful gradient design with smooth animations
- Card-based layout with professional styling
- Mobile-responsive and accessible (WCAG compliant)
- Loading states and real-time feedback
- Dark purple gradient background

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
