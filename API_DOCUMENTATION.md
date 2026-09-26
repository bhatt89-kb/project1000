# 📚 LegalLens Lite API Documentation

## Overview

LegalLens Lite provides a RESTful API for document analysis, Q&A, comparison, and export. All endpoints are privacy-first with no authentication required.

**Base URL:** `https://legallens-lite.onrender.com` (or `http://localhost:5000` for local)

---

## 🔐 Security & Rate Limits

### Rate Limiting
All endpoints are rate-limited to prevent abuse:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/upload` | 10 requests | per minute |
| `/api/ask` | 30 requests | per minute |
| `/api/compare` | 5 requests | per minute |
| `/api/documents` | 100 requests | per minute |
| `/api/export/{id}` | 20 requests | per minute |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1640000000
```

### Security Headers
All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'self'`

---

## 📄 API Endpoints

### 1. Upload Document

Upload a legal document for analysis.

**Endpoint:** `POST /api/upload`

**Content-Type:** `multipart/form-data`

**Parameters:**
- `document` (file, required): PDF or TXT file (max 5 MB)

**Request Example:**
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "document=@rental_agreement.pdf"
```

**Response Example (200 OK):**
```json
{
  "id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "summary": {
    "type": "Rental agreement",
    "pages": 5,
    "duration": "12 months",
    "monthly_rent": "₹18,000",
    "security_deposit": "₹50,000",
    "notice_period": "2 months"
  },
  "risk_assessment": {
    "level": "Medium",
    "score": 6.2,
    "total_issues": 8,
    "high_priority": 2,
    "categories": {
      "liability": 8,
      "termination": 7,
      "penalties": 6,
      "renewal": 5
    }
  },
  "entities": {
    "dates": ["15/01/2024", "14/01/2025"],
    "amounts": ["₹18,000", "₹50,000"],
    "parties": ["Landlord", "Tenant"],
    "obligations": [
      "Tenant shall maintain the property",
      "Landlord must provide receipts"
    ]
  },
  "findings": [
    {
      "category": "liability",
      "label": "Liability",
      "risk_score": 8,
      "explanation": "Tenant is responsible for all damages...",
      "excerpt": "The tenant shall indemnify...",
      "page": 3,
      "clause": "7.2"
    }
  ],
  "checklist": [
    "Verify the monthly rent amount",
    "Check the security deposit refund conditions",
    "Review the notice period requirements"
  ],
  "disclaimer": "This is not legal advice..."
}
```

**Error Responses:**

**400 Bad Request - No file uploaded:**
```json
{
  "error": "Please choose a PDF or TXT file."
}
```

**400 Bad Request - Invalid file type:**
```json
{
  "error": "Only PDF and TXT files are supported."
}
```

**413 Payload Too Large:**
```json
{
  "error": "The file is larger than 5 MB."
}
```

**429 Too Many Requests:**
```json
{
  "error": "Rate limit exceeded. Try again in 60 seconds."
}
```

---

### 2. Ask Question

Ask a question about an uploaded document.

**Endpoint:** `POST /api/ask`

**Content-Type:** `application/json`

**Parameters:**
- `id` (string, required): Document ID from upload response
- `question` (string, required): Question to ask (max 500 characters)

**Request Example:**
```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "question": "What is the notice period?"
  }'
```

**Response Example (200 OK):**
```json
{
  "matches": [
    {
      "text": "The tenant must give 2 months written notice...",
      "page": 4,
      "clause": "9.1",
      "score": 3
    }
  ],
  "message": ""
}
```

**Response Example (No Matches):**
```json
{
  "matches": [],
  "message": "I couldn't find this information in the uploaded document."
}
```

**Error Responses:**

**400 Bad Request - Invalid document ID:**
```json
{
  "error": "Invalid document ID format."
}
```

**400 Bad Request - Question too short:**
```json
{
  "error": "Question is too short. Please provide more detail."
}
```

**404 Not Found:**
```json
{
  "error": "Document not found. Please upload it again."
}
```

---

### 3. Compare Documents

Compare two documents side-by-side.

**Endpoint:** `POST /api/compare`

**Content-Type:** `application/json`

**Parameters:**
- `id1` (string, required): First document ID
- `id2` (string, required): Second document ID

**Request Example:**
```bash
curl -X POST http://localhost:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "id1": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "id2": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7"
  }'
```

**Response Example (200 OK):**
```json
{
  "summary_comparison": {
    "duration": {
      "document1": "12 months",
      "document2": "6 months",
      "different": true
    },
    "monthly_rent": {
      "document1": "₹18,000",
      "document2": "₹20,000",
      "different": true
    },
    "security_deposit": {
      "document1": "₹50,000",
      "document2": "₹50,000",
      "different": false
    }
  },
  "risk_comparison": {
    "document1": {
      "level": "Medium",
      "score": 6.2,
      "total_issues": 8
    },
    "document2": {
      "level": "High",
      "score": 7.8,
      "total_issues": 12
    }
  },
  "differences": [
    "Document 1 has longer lease duration (12 months vs 6 months)",
    "Document 2 has higher monthly rent (₹20,000 vs ₹18,000)",
    "Document 2 has more risky clauses (12 vs 8)"
  ],
  "unique_clauses": {
    "document1": ["Maintenance responsibility", "Parking included"],
    "document2": ["Pet policy", "Late payment penalty"]
  }
}
```

**Error Responses:**

**400 Bad Request - Same document:**
```json
{
  "error": "Cannot compare a document with itself."
}
```

**404 Not Found:**
```json
{
  "error": "One or both documents not found. Please upload them again."
}
```

---

### 4. List Documents

Get list of currently uploaded documents.

**Endpoint:** `GET /api/documents`

**Request Example:**
```bash
curl http://localhost:5000/api/documents
```

**Response Example (200 OK):**
```json
{
  "documents": [
    {
      "id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "type": "Rental agreement",
      "pages": 5
    },
    {
      "id": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7",
      "type": "Employment contract",
      "pages": 12
    }
  ]
}
```

---

### 5. Export Report

Export analysis as HTML report.

**Endpoint:** `GET /api/export/{document_id}`

**Parameters:**
- `document_id` (path, required): Document ID to export

**Request Example:**
```bash
curl http://localhost:5000/api/export/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6 \
  -o report.html
```

**Response:** HTML document with embedded CSS

**Headers:**
```
Content-Type: text/html; charset=utf-8
Content-Disposition: inline; filename="legal-analysis-report.html"
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "error": "Invalid document ID format."
}
```

**404 Not Found:**
```json
{
  "error": "Document not found."
}
```

---

## 🔄 Workflow Examples

### Example 1: Basic Document Analysis

```javascript
// 1. Upload document
const formData = new FormData();
formData.append('document', fileInput.files[0]);

const uploadResponse = await fetch('/api/upload', {
  method: 'POST',
  body: formData
});

const analysis = await uploadResponse.json();
console.log(`Risk Level: ${analysis.risk_assessment.level}`);
console.log(`Total Issues: ${analysis.risk_assessment.total_issues}`);

// 2. Ask a question
const questionResponse = await fetch('/api/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    id: analysis.id,
    question: 'What is the security deposit?'
  })
});

const answer = await questionResponse.json();
console.log(answer.matches[0].text);

// 3. Export report
window.open(`/api/export/${analysis.id}`, '_blank');
```

### Example 2: Compare Two Documents

```python
import requests

# Upload first document
with open('apartment_a.pdf', 'rb') as f:
    response1 = requests.post(
        'http://localhost:5000/api/upload',
        files={'document': f}
    )
    doc1_id = response1.json()['id']

# Upload second document
with open('apartment_b.pdf', 'rb') as f:
    response2 = requests.post(
        'http://localhost:5000/api/upload',
        files={'document': f}
    )
    doc2_id = response2.json()['id']

# Compare documents
comparison = requests.post(
    'http://localhost:5000/api/compare',
    json={'id1': doc1_id, 'id2': doc2_id}
).json()

# Print comparison
print(f"Document 1 Risk: {comparison['risk_comparison']['document1']['level']}")
print(f"Document 2 Risk: {comparison['risk_comparison']['document2']['level']}")
print("\nKey Differences:")
for diff in comparison['differences']:
    print(f"  - {diff}")
```

### Example 3: Batch Processing

```python
import requests
import glob

# Process all PDFs in a directory
pdf_files = glob.glob('contracts/*.pdf')
results = []

for pdf_file in pdf_files:
    with open(pdf_file, 'rb') as f:
        response = requests.post(
            'http://localhost:5000/api/upload',
            files={'document': f}
        )
        
        if response.status_code == 200:
            analysis = response.json()
            results.append({
                'filename': pdf_file,
                'risk_level': analysis['risk_assessment']['level'],
                'risk_score': analysis['risk_assessment']['score'],
                'total_issues': analysis['risk_assessment']['total_issues']
            })

# Sort by risk score (highest first)
results.sort(key=lambda x: x['risk_score'], reverse=True)

# Print summary
print("Risk Summary Report:")
print("-" * 60)
for result in results:
    print(f"{result['filename']}: {result['risk_level']} "
          f"({result['risk_score']}/10) - {result['total_issues']} issues")
```

---

## 🛠️ SDK Examples

### Python SDK Example

```python
class LegalLensClient:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.session = requests.Session()
    
    def upload_document(self, file_path):
        """Upload a document for analysis."""
        with open(file_path, 'rb') as f:
            response = self.session.post(
                f'{self.base_url}/api/upload',
                files={'document': f}
            )
        response.raise_for_status()
        return response.json()
    
    def ask_question(self, document_id, question):
        """Ask a question about a document."""
        response = self.session.post(
            f'{self.base_url}/api/ask',
            json={'id': document_id, 'question': question}
        )
        response.raise_for_status()
        return response.json()
    
    def compare_documents(self, doc_id1, doc_id2):
        """Compare two documents."""
        response = self.session.post(
            f'{self.base_url}/api/compare',
            json={'id1': doc_id1, 'id2': doc_id2}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = LegalLensClient()
analysis = client.upload_document('rental_agreement.pdf')
print(f"Risk: {analysis['risk_assessment']['level']}")

answer = client.ask_question(analysis['id'], 'What is the rent?')
print(answer['matches'][0]['text'])
```

### JavaScript SDK Example

```javascript
class LegalLensAPI {
  constructor(baseURL = 'http://localhost:5000') {
    this.baseURL = baseURL;
  }

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('document', file);
    
    const response = await fetch(`${this.baseURL}/api/upload`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error);
    }
    
    return response.json();
  }

  async askQuestion(documentId, question) {
    const response = await fetch(`${this.baseURL}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: documentId, question })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error);
    }
    
    return response.json();
  }

  async compareDocuments(docId1, docId2) {
    const response = await fetch(`${this.baseURL}/api/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id1: docId1, id2: docId2 })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error);
    }
    
    return response.json();
  }
}

// Usage
const api = new LegalLensAPI();

const fileInput = document.getElementById('file-input');
const analysis = await api.uploadDocument(fileInput.files[0]);
console.log(`Risk: ${analysis.risk_assessment.level}`);

const answer = await api.askQuestion(analysis.id, 'What is the rent?');
console.log(answer.matches[0].text);
```

---

## 🧪 Testing the API

### Using Postman

1. **Import Collection:**
   - Download [LegalLens Postman Collection](./postman_collection.json)
   - Import into Postman

2. **Set Environment Variables:**
   - `base_url`: `http://localhost:5000` or production URL
   - `document_id`: Will be set automatically after upload

3. **Run Tests:**
   - Upload document
   - Ask question (uses `{{document_id}}`)
   - Compare documents
   - Export report

### Using cURL

See individual endpoint examples above or use the provided [test_api.sh](./scripts/test_api.sh) script:

```bash
chmod +x scripts/test_api.sh
./scripts/test_api.sh
```

---

## 📊 Response Schemas

### DocumentAnalysis Schema

```typescript
interface DocumentAnalysis {
  id: string;                    // UUID v4 format
  summary: Summary;
  risk_assessment: RiskAssessment;
  entities: Entities;
  findings: Finding[];
  checklist: string[];
  disclaimer: string;
}

interface Summary {
  type: string;                  // "Rental agreement", etc.
  pages: number;
  duration: string;
  monthly_rent: string;
  security_deposit: string;
  notice_period: string;
}

interface RiskAssessment {
  level: "Low" | "Medium" | "High";
  score: number;                 // 0-10
  total_issues: number;
  high_priority: number;
  categories: {
    [category: string]: number;  // 0-10 per category
  };
}

interface Entities {
  dates: string[];
  amounts: string[];
  parties: string[];
  obligations: string[];
}

interface Finding {
  category: string;
  label: string;
  risk_score: number;            // 1-10
  explanation: string;
  excerpt: string;
  page: number;
  clause: string | null;
}
```

---

## ⚠️ Error Handling

### Common Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid file type, missing parameters |
| 404 | Not Found | Document ID doesn't exist |
| 413 | Payload Too Large | File exceeds 5 MB |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Processing failed |

### Error Response Format

All errors follow this format:

```json
{
  "error": "Human-readable error message"
}
```

### Handling Errors in Code

```javascript
try {
  const response = await fetch('/api/upload', options);
  
  if (!response.ok) {
    const error = await response.json();
    
    switch (response.status) {
      case 400:
        alert(`Invalid request: ${error.error}`);
        break;
      case 413:
        alert('File too large. Maximum 5 MB.');
        break;
      case 429:
        alert('Rate limit exceeded. Please wait a minute.');
        break;
      default:
        alert(`Error: ${error.error}`);
    }
    return;
  }
  
  const data = await response.json();
  // Handle success
} catch (err) {
  console.error('Network error:', err);
  alert('Connection failed. Please check your internet.');
}
```

---

## 🔒 Privacy & Data Handling

### Data Retention
- **Documents**: Stored in-memory only, never written to disk
- **Maximum documents**: 50 (oldest auto-removed when exceeded)
- **Session persistence**: Documents cleared on server restart
- **No tracking**: Zero analytics, cookies, or user identification

### GDPR Compliance
- **No personal data collection**: We don't collect names, emails, or IPs
- **No data transfer**: Documents processed locally
- **No third parties**: Zero external API calls
- **Right to deletion**: Automatic (memory-only storage)

---

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/bhatt89-kb/project1000/issues)
- **Documentation**: [README.md](./README.md)
- **Deployment Guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **License**: [MIT License](./LICENSE)

---

**API Version:** v2.0  
**Last Updated:** December 2024  
**Status:** Production Ready 🚀
