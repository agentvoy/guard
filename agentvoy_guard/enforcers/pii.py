"""
PII (Personally Identifiable Information) detector.
Detects SSNs, credit cards, emails, phone numbers, and more.
"""

from __future__ import annotations
import re
import warnings
from ..exceptions import PIIDetectedError

PII_PATTERNS: list[tuple[str, str]] = [
    # US Social Security Number
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
    (r"\b\d{9}\b(?=\s|$)", "SSN (unformatted)"),

    # Credit card numbers (Visa, MC, Amex, Discover)
    (r"\b4[0-9]{12}(?:[0-9]{3})?\b", "credit card (Visa)"),
    (r"\b5[1-5][0-9]{14}\b", "credit card (Mastercard)"),
    (r"\b3[47][0-9]{13}\b", "credit card (Amex)"),
    (r"\b6(?:011|5[0-9]{2})[0-9]{12}\b", "credit card (Discover)"),

    # Email addresses
    (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", "email address"),

    # US phone numbers
    (r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b", "phone number"),

    # Passport-like numbers (US format)
    (r"\b[A-Z]{1,2}\d{6,9}\b", "passport number"),

    # IP addresses (private/internal)
    (r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b", "private IP"),

    # AWS access keys
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key"),

    # Generic API key pattern
    (r"\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9\-_]{20,}['\"]?", "API key"),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in PII_PATTERNS]


def detect_pii(text: str) -> list[str]:
    """Returns list of PII type labels found in text. Empty = clean."""
    found = []
    for pattern, label in _COMPILED:
        if pattern.search(text):
            if label not in found:
                found.append(label)
    return found


def enforce_pii(text: str, mode: str):
    """
    Enforce PII policy based on mode:
    - 'off': do nothing
    - 'warn': print warning
    - 'block': raise PIIDetectedError
    """
    if mode == "off":
        return

    pii_types = detect_pii(text)
    if not pii_types:
        return

    if mode == "warn":
        warnings.warn(
            f"[agentvoy-guard] PII detected in text: {', '.join(pii_types)}",
            stacklevel=3,
        )
    elif mode == "block":
        raise PIIDetectedError(pii_types)
