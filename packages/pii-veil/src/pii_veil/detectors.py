"""Zero-dependency regex detectors, used when Presidio is not installed.

These cover the structured PII that regex handles well (email, phone, card, IP).
Presidio adds the rest (names, locations, and so on) when it is available.
"""
from __future__ import annotations

import re

# Ordered: the more specific patterns run first so a phone pattern does not
# swallow an IP address or a card number.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL_ADDRESS", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("IP_ADDRESS", re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")),
    ("CREDIT_CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("PHONE_NUMBER", re.compile(r"\+?\d[\d ().-]{7,}\d")),
]


def regex_scrub(text: str) -> str:
    """Replace each detected span with a `<LABEL>` placeholder."""
    for label, pattern in PATTERNS:
        text = pattern.sub(f"<{label}>", text)
    return text
