# Security Guide - Legal Document Assistant

This document outlines the security measures implemented in the Legal Document Assistant.

## Security Architecture

### Privacy-First Design

✅ **No external API calls** - All processing happens locally  
✅ **No data transmission** - Documents never leave your machine  
✅ **Memory-only storage** - Documents are never written to disk  
✅ **Auto-cleanup** - Oldest documents removed when limit (50) is reached  
✅ **No persistence** - All data lost on restart (by design)  

## Input Validation

### File Upload Security

| Control | Implementation |
|---|---|
| File size limit | 5 MB maximum |
| File type validation | PDF and TXT only |
| Extension checking | Validates `.pdf` and `.txt` extensions |
| Content verification | pypdf validates PDF structure |

### Request Validation

- **Question length**: Maximum 500 characters
- **Document limit**: Maximum 50 documents in memory
- **JSON parsing**: Silent failure with fallback to empty object
- **Error handling**: Generic error messages, no sensitive info leaked

## Data Handling

### Document Lifecycle

```
Upload → Memory Storage → Analysis → Query → Auto-Cleanup
   ↓                                              ↓
Never touches disk                         Removed after 50 docs
```

### What We Store (In Memory Only)

- Document text chunks with page numbers
- Analysis results (summary, findings, checklist)
- Document UUID for session tracking

### What We DON'T Store

- Original file bytes (discarded after parsing)
- User information or IP addresses
- API keys or credentials (none needed!)
- Analytics or tracking data

## HTTP Security Headers

All responses include these security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```

### Header Explanations

- **X-Content-Type-Options**: Prevents MIME-type sniffing
- **X-Frame-Options**: Prevents clickjacking attacks
- **Referrer-Policy**: Doesn't leak URLs to external sites
- **CSP**: Only allows scripts/styles from same origin

## Frontend Security

### Safe Rendering

✅ Uses `textContent` instead of `innerHTML`  
✅ No user input rendered as HTML  
✅ Document text treated as plain text only  
✅ No eval() or dynamic code execution  

### Form Validation

- Client-side validation for file types
- Maxlength attribute on text inputs
- HTTPS-only in production (recommended)

## Production Deployment

### Pre-Deployment Checklist

- [ ] Use production WSGI server (gunicorn, uWSGI)
- [ ] Set up HTTPS with valid SSL certificate
- [ ] Configure firewall to allow only ports 80/443
- [ ] Enable rate limiting (Flask-Limiter recommended)
- [ ] Set up monitoring and logging
- [ ] Configure proper CORS if needed
- [ ] Review and tighten CSP headers
- [ ] Set environment to production mode

### Production Server Example

```bash
# Install gunicorn
pip install gunicorn

# Run with proper configuration
gunicorn --bind 0.0.0.0:8000 \
         --workers 4 \
         --timeout 120 \
         --access-logfile /var/log/app/access.log \
         --error-logfile /var/log/app/error.log \
         app:app
```

### Environment Configuration

```bash
# Production settings
FLASK_ENV=production
MAX_DOCUMENTS=50
MAX_UPLOAD_SIZE=5242880  # 5 MB in bytes
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Upload size limit
        client_max_body_size 5M;
    }
}
```

## Monitoring & Logging

### What to Log

✅ Request timestamps and endpoints  
✅ Upload file sizes and types  
✅ Error conditions and stack traces  
✅ Response times and performance metrics  

### What NOT to Log

❌ Document contents  
❌ User questions or answers  
❌ Personal information  
❌ Full file paths (use relative paths)  

### Example Logging Setup

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## Rate Limiting

Protect against abuse with rate limiting:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@limiter.limit("10 per minute")
@app.post("/api/upload")
def upload():
    # ... existing code ...
```

## Security Incident Response

If you suspect a security issue:

1. **Identify** - Determine the scope and impact
2. **Contain** - Restart the service (clears all in-memory data)
3. **Investigate** - Check logs for unusual activity
4. **Remediate** - Apply fixes or updates
5. **Document** - Record the incident and response

## Common Threats & Mitigations

| Threat | Mitigation |
|---|---|
| File upload exploits | Size limits, type validation, no disk writes |
| XSS attacks | textContent rendering, CSP headers |
| Clickjacking | X-Frame-Options: DENY |
| MIME confusion | X-Content-Type-Options: nosniff |
| DoS attacks | Rate limiting, document count limits |
| Data leakage | Memory-only storage, no logging of content |

## Testing Security

```bash
# Run tests including security checks
python -m pytest tests/

# Check for common vulnerabilities
pip install bandit
bandit -r legallens/ app.py

# Scan dependencies
pip install safety
safety check
```

## Updates & Patches

Keep dependencies updated:

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade flask

# Update all packages (carefully!)
pip install --upgrade -r requirements.txt
```

## Compliance Notes

- **GDPR**: No personal data collected or stored
- **Data retention**: Documents deleted automatically (memory-only)
- **Right to erasure**: Simply restart the application
- **Data portability**: Not applicable (no persistent storage)

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Contact the development team privately
3. Provide detailed reproduction steps
4. Allow time for a fix before disclosure

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/en/stable/security/)
- [Web Security Basics](https://developer.mozilla.org/en-US/docs/Web/Security)

---

**Security Status**: ✅ Hardened for local use  
**Last Updated**: 2026  
**Review Frequency**: Quarterly
