"""Mask PII in query results before they reach the LLM or the screen.

Powered by Microsoft Presidio when it is installed; falls back to built-in regex
detectors otherwise, so it always does something useful and never needs a model
download to get started. Operates on the result data, never on a live database.
"""
from __future__ import annotations

from .detectors import regex_scrub


class Veil:
    """Scrubs PII from text and from result rows.

    Args:
        use_presidio: try to use Presidio for detection (names, locations, and
            the structured types). When False, or when Presidio is not
            installed, the built-in regex detectors are used instead.
        language: language code passed to Presidio's analyzer.
    """

    def __init__(self, use_presidio: bool = True, language: str = "en"):
        self.language = language
        self._analyzer = None
        self._anonymizer = None
        if use_presidio:
            try:
                from presidio_analyzer import AnalyzerEngine
                from presidio_anonymizer import AnonymizerEngine

                self._analyzer = AnalyzerEngine()
                self._anonymizer = AnonymizerEngine()
            except Exception:
                # Presidio (or its spaCy model) is unavailable; use regex.
                self._analyzer = None
                self._anonymizer = None

    @property
    def backend(self) -> str:
        return "presidio" if self._analyzer is not None else "regex"

    def scrub_text(self, text):
        """Return the text with detected PII replaced by `<LABEL>` placeholders."""
        if not isinstance(text, str) or not text:
            return text
        if self._analyzer is not None:
            results = self._analyzer.analyze(text=text, language=self.language)
            return self._anonymizer.anonymize(text=text, analyzer_results=results).text
        return regex_scrub(text)

    def scrub_value(self, value):
        """Scrub a single cell. Non-string values pass through unchanged."""
        return self.scrub_text(value) if isinstance(value, str) else value

    def scrub_rows(self, rows, columns=None):
        """Scrub a list of row dicts.

        If ``columns`` is given, only those columns are scrubbed; otherwise every
        string cell is. Numbers, dates, and other non-strings pass through.
        """
        out = []
        for row in rows:
            if columns is None:
                out.append({k: self.scrub_value(v) for k, v in row.items()})
            else:
                cols = set(columns)
                out.append({k: (self.scrub_value(v) if k in cols else v) for k, v in row.items()})
        return out
