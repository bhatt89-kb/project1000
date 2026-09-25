"""Rule-based analysis of a document: summary values, flagged clauses, and a checklist.

Every rule is a fixed keyword pattern, so results are predictable and easy to test.
The output is information to review, not legal advice.
"""

import re

NOT_SPECIFIED = "Not specified"
DISCLAIMER = (
    "LegalLens Lite gives general information about a document. It is not legal advice. "
    "Check important decisions with a qualified lawyer."
)

# (category, label, keyword pattern)
RISK_RULES = [
    ("liability", "Important", r"liab|indemnif"),
    ("financial", "Important", r"deposit"),
    ("termination", "Needs Review", r"terminat"),
    ("renewal", "Needs Review", r"renew"),
    ("penalty", "Potential Concern", r"penalt|late (?:payment|fee)|forfeit"),
    ("privacy", "Needs Review", r"privacy|personal data|confidential"),
    ("dispute", "Needs Review", r"arbitrat|dispute|jurisdiction|governing law"),
]

EXPLANATIONS = {
    "liability": "May affect who pays for losses or damage.",
    "financial": "May create a deposit or payment obligation.",
    "termination": "May set how and when the agreement can end.",
    "renewal": "May extend the agreement automatically.",
    "penalty": "May add a charge if a condition is not met.",
    "privacy": "May affect how personal information is used.",
    "dispute": "May decide how disagreements are settled.",
}

CHECKLIST = {
    "liability": "Review the liability clause.",
    "financial": "Confirm the deposit and payment conditions.",
    "termination": "Review the termination clause and notice requirements.",
    "renewal": "Check whether the agreement renews automatically.",
    "penalty": "Check for late payment fees or penalties.",
    "privacy": "Check how personal data is handled.",
    "dispute": "Check how disputes are resolved.",
}

DOCUMENT_TYPES = [
    ("Rental agreement", r"\b(?:tenant|landlord|lease|rental)\b"),
    ("Employment contract", r"\b(?:employee|employer)\b"),
    ("Non-disclosure agreement", r"non-disclosure"),
    ("Service agreement", r"\bservice provider\b"),
]

SENTENCE_SPLIT = re.compile(r"(?<=[.;!?])\s+(?=[A-Z])|\n+")
PERIOD_RE = re.compile(r"(\d{1,3})\s*(days?|months?|years?)\b", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(?:₹|Rs\.?|INR)\s?(\d[\d,]*(?:\.\d+)?)")


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
    """Return one finding per (clause, matching category)."""
    findings = []
    for chunk in chunks:
        for category, label, pattern in RISK_RULES:
            if re.search(pattern, chunk["text"], re.IGNORECASE):
                findings.append({
                    "category": category,
                    "label": label,
                    "explanation": EXPLANATIONS[category],
                    "clause": chunk["clause"],
                    "page": chunk["page"],
                    "excerpt": chunk["text"][:300],
                })
    return findings


def make_checklist(categories):
    items = [CHECKLIST[category] for category, _, _ in RISK_RULES if category in categories]
    items.append("Ask a qualified lawyer about any clause you do not understand.")
    return items


def analyze(pages, chunks):
    """Build the full analysis response for one document."""
    findings = flag_clauses(chunks)
    categories = {finding["category"] for finding in findings}
    return {
        "summary": summarize("\n".join(pages), len(pages)),
        "findings": findings,
        "checklist": make_checklist(categories),
        "disclaimer": DISCLAIMER,
    }
