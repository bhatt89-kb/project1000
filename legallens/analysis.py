"""Rule-based analysis of a document: summary values, flagged clauses, entity extraction, and risk scoring.

Every rule is a fixed keyword pattern, so results are predictable and easy to test.
The output is information to review, not legal advice.
"""

import re
from datetime import datetime
from typing import List, Dict, Any

NOT_SPECIFIED = "Not specified"
DISCLAIMER = (
    "Legal Document Assistant provides general information about documents. It is not legal advice. "
    "Always consult a qualified lawyer for important legal decisions."
)

# Enhanced risk rules with severity scoring (category, label, pattern, risk_score)
RISK_RULES = [
    ("liability", "High Priority", r"liab|indemnif|hold harmless", 9),
    ("financial", "Important", r"deposit|payment|fee|charge", 7),
    ("termination", "Needs Review", r"terminat|cancel|end agreement", 8),
    ("renewal", "Needs Review", r"renew|auto.*renew|automatic.*extension", 6),
    ("penalty", "Potential Concern", r"penalt|late (?:payment|fee)|forfeit|damages", 7),
    ("privacy", "Needs Review", r"privacy|personal data|confidential|information", 6),
    ("dispute", "Needs Review", r"arbitrat|dispute|jurisdiction|governing law|mediation", 7),
    ("maintenance", "Note", r"maintain|repair|upkeep", 5),
    ("insurance", "Important", r"insurance|coverage|insure", 7),
    ("modification", "Note", r"amend|modify|change|alter", 5),
    ("assignment", "Needs Review", r"assign|transfer|sublease|sublet", 6),
    ("force_majeure", "Note", r"force majeure|act of god|unforeseeable", 5),
]

EXPLANATIONS = {
    "liability": "Defines responsibility for losses, damages, or injuries. May shift significant risk to one party.",
    "financial": "Creates payment obligations beyond base rent. Review all fees and conditions carefully.",
    "termination": "Specifies how and when either party can end the agreement. Critical for exit planning.",
    "renewal": "May automatically extend the agreement unless notice is given. Check renewal terms and deadlines.",
    "penalty": "Imposes additional charges for specific actions or omissions. Understand all penalty triggers.",
    "privacy": "Governs collection, use, and sharing of personal information. Important for data protection.",
    "dispute": "Determines how disagreements are resolved (court, arbitration, mediation). Affects your legal options.",
    "maintenance": "Specifies who is responsible for repairs and upkeep. Clarify obligations to avoid disputes.",
    "insurance": "Requires specific insurance coverage. Verify requirements and obtain necessary policies.",
    "modification": "Describes how the agreement can be changed. Usually requires written consent from both parties.",
    "assignment": "Controls whether you can transfer your rights or obligations to another party.",
    "force_majeure": "Excuses performance during unforeseeable events. Understand what events qualify.",
}

CHECKLIST = {
    "liability": "Review the liability clause and understand your exposure to risk.",
    "financial": "Confirm all deposits, fees, and payment conditions.",
    "termination": "Review termination clause, notice requirements, and any penalties.",
    "renewal": "Check whether the agreement renews automatically and how to opt out.",
    "penalty": "Identify all late fees, penalties, and conditions that trigger them.",
    "privacy": "Understand how personal data is collected, used, and shared.",
    "dispute": "Review dispute resolution process and jurisdiction requirements.",
    "maintenance": "Clarify maintenance responsibilities and response times.",
    "insurance": "Verify required insurance types, coverage amounts, and beneficiaries.",
    "modification": "Understand the process for amending the agreement.",
    "assignment": "Check whether you can sublease, transfer, or assign the agreement.",
    "force_majeure": "Review which events excuse performance and notice requirements.",
}

DOCUMENT_TYPES = [
    ("Rental agreement", r"\b(?:tenant|landlord|lease|rental)\b"),
    ("Employment contract", r"\b(?:employee|employer)\b"),
    ("Non-disclosure agreement", r"non-disclosure"),
    ("Service agreement", r"\bservice provider\b"),
]

SENTENCE_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=[A-Z])|\n+")
PERIOD_RE = re.compile(r"(\d{1,3})\s*(days?|months?|years?)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR|USD|\$)\s?(\d[\d,]*(?:\.\d+)?)")
DATE_RE = re.compile(
    r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|"
    r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})|"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE
)
PARTY_RE = re.compile(
    r"\b(?:between|party|tenant|landlord|lessor|lessee|employer|employee|"
    r"client|contractor|vendor|supplier|buyer|seller)[\s:]+([A-Z][a-zA-Z\s&.]+?)(?=\s*(?:and|,|\(|$))",
    re.IGNORECASE
)


def sentences(text):
    """Split text into sentences, keeping decimals like 'Rs. 18,000' intact."""
    return [part.strip() for part in SENTENCE_SPLIT.split(text) if part and part.strip()]


def _period(sentence):
    match = PERIOD_RE.search(sentence)
    return f"{match.group(1)} {match.group(2).lower()}" if match else None


def _amount(sentence):
    match = AMOUNT_RE.search(sentence)
    return f"₹{match.group(1)}" if match else None


def _find_value(sentence_list, keyword, extract):
    """Return the first value found in a sentence that mentions the keyword."""
    for sentence in sentence_list:
        if re.search(rf"\b(?:{keyword})\b", sentence, re.IGNORECASE):
            value = extract(sentence)
            if value:
                return value
    return NOT_SPECIFIED


def _document_type(text):
    for name, pattern in DOCUMENT_TYPES:
        if re.search(pattern, text, re.IGNORECASE):
            return name
    return "Legal document"


def summarize(text, page_count):
    """Extract the type, duration, rent, deposit, and notice period where stated."""
    sentence_list = sentences(text)
    return {
        "type": _document_type(text),
        "pages": page_count,
        "duration": _find_value(sentence_list, "term|duration", _period),
        "monthly_rent": _find_value(sentence_list, "rent|rental", _amount),
        "security_deposit": _find_value(sentence_list, "deposit", _amount),
        "notice_period": _find_value(sentence_list, "notice", _period),
    }


def flag_clauses(chunks):
    """Return one finding per (clause, matching category) with risk scoring."""
    findings = []
    seen = set()  # Avoid duplicate findings for same clause/category
    
    for chunk in chunks:
        for category, label, pattern, risk_score in RISK_RULES:
            if re.search(pattern, chunk["text"], re.IGNORECASE):
                key = (chunk["clause"], category)
                if key not in seen:
                    seen.add(key)
                    findings.append({
                        "category": category,
                        "label": label,
                        "explanation": EXPLANATIONS[category],
                        "clause": chunk["clause"],
                        "page": chunk["page"],
                        "excerpt": chunk["text"][:300],
                        "risk_score": risk_score,
                    })
    
    # Sort by risk score (highest first), then by page number
    findings.sort(key=lambda x: (-x["risk_score"], x["page"]))
    return findings


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract key entities from the document: dates, amounts, parties, and obligations."""
    entities = {
        "dates": [],
        "amounts": [],
        "parties": [],
        "obligations": []
    }
    
    # Extract dates
    date_matches = DATE_RE.findall(text)
    for match in date_matches:
        date_str = next(d for d in match if d)
        if date_str not in entities["dates"]:
            entities["dates"].append(date_str)
    
    # Extract amounts
    amount_matches = AMOUNT_RE.findall(text)
    for amount in amount_matches:
        formatted_amount = f"₹{amount}" if not any(c in amount for c in ['$', '₹']) else amount
        if formatted_amount not in entities["amounts"]:
            entities["amounts"].append(formatted_amount)
    
    # Extract parties (names after keywords)
    party_matches = PARTY_RE.findall(text)
    for party in party_matches:
        party = party.strip()
        if len(party) > 2 and party not in entities["parties"] and len(entities["parties"]) < 10:
            entities["parties"].append(party)
    
    # Extract obligations (sentences with "shall", "must", "required to")
    obligation_pattern = re.compile(
        r"([^.;!?]*(?:shall|must|required to|obligated to|agrees to)[^.;!?]*[.;!?])",
        re.IGNORECASE
    )
    obligation_matches = obligation_pattern.findall(text)
    for obligation in obligation_matches[:10]:  # Limit to top 10
        clean_obligation = obligation.strip()
        if len(clean_obligation) > 20 and len(clean_obligation) < 200:
            entities["obligations"].append(clean_obligation)
    
    # Limit results
    entities["dates"] = entities["dates"][:10]
    entities["amounts"] = entities["amounts"][:15]
    entities["parties"] = entities["parties"][:6]
    
    return entities


def make_checklist(categories):
    items = [CHECKLIST[category] for category, _, _, _ in RISK_RULES if category in categories]
    items.append("Ask a qualified lawyer about any clause you do not understand.")
    return items


def analyze(pages, chunks):
    """Build the full analysis response for one document."""
    full_text = "\n".join(pages)
    findings = flag_clauses(chunks)
    categories = {finding["category"] for finding in findings}
    entities = extract_entities(full_text)
    
    # Calculate overall risk score
    total_risk = sum(f["risk_score"] for f in findings)
    avg_risk = total_risk / len(findings) if findings else 0
    risk_level = "High" if avg_risk >= 7 else "Medium" if avg_risk >= 5 else "Low"
    
    return {
        "summary": summarize(full_text, len(pages)),
        "findings": findings,
        "checklist": make_checklist(categories),
        "entities": entities,
        "risk_assessment": {
            "level": risk_level,
            "score": round(avg_risk, 1),
            "total_issues": len(findings),
            "high_priority": sum(1 for f in findings if f["risk_score"] >= 8)
        },
        "disclaimer": DISCLAIMER,
    }


def compare_documents(doc1_result: Dict[str, Any], doc2_result: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two document analysis results and highlight key differences."""
    comparison = {
        "summary_comparison": {},
        "risk_comparison": {},
        "differences": []
    }
    
    # Compare summaries
    sum1 = doc1_result["summary"]
    sum2 = doc2_result["summary"]
    
    for key in ["duration", "monthly_rent", "security_deposit", "notice_period"]:
        val1 = sum1.get(key, NOT_SPECIFIED)
        val2 = sum2.get(key, NOT_SPECIFIED)
        comparison["summary_comparison"][key] = {
            "document1": val1,
            "document2": val2,
            "different": val1 != val2
        }
    
    # Compare risk levels
    risk1 = doc1_result.get("risk_assessment", {})
    risk2 = doc2_result.get("risk_assessment", {})
    
    comparison["risk_comparison"] = {
        "document1": {
            "level": risk1.get("level", "Unknown"),
            "score": risk1.get("score", 0),
            "issues": risk1.get("total_issues", 0)
        },
        "document2": {
            "level": risk2.get("level", "Unknown"),
            "score": risk2.get("score", 0),
            "issues": risk2.get("total_issues", 0)
        }
    }
    
    # Compare clause categories
    cats1 = {f["category"] for f in doc1_result.get("findings", [])}
    cats2 = {f["category"] for f in doc2_result.get("findings", [])}
    
    only_in_doc1 = cats1 - cats2
    only_in_doc2 = cats2 - cats1
    
    if only_in_doc1:
        comparison["differences"].append({
            "type": "clauses_only_in_doc1",
            "categories": list(only_in_doc1),
            "description": f"Document 1 contains {len(only_in_doc1)} clause type(s) not found in Document 2"
        })
    
    if only_in_doc2:
        comparison["differences"].append({
            "type": "clauses_only_in_doc2",
            "categories": list(only_in_doc2),
            "description": f"Document 2 contains {len(only_in_doc2)} clause type(s) not found in Document 1"
        })
    
    # Highlight major differences
    for key, comp in comparison["summary_comparison"].items():
        if comp["different"] and comp["document1"] != NOT_SPECIFIED and comp["document2"] != NOT_SPECIFIED:
            comparison["differences"].append({
                "type": "summary_difference",
                "field": key.replace("_", " ").title(),
                "document1_value": comp["document1"],
                "document2_value": comp["document2"],
                "description": f"{key.replace('_', ' ').title()} differs between documents"
            })
    
    return comparison
