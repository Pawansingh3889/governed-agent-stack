"""pii-veil: mask PII in SQL query results before they reach the LLM or the screen.

Part of the Governed Agent Stack. Powered by Microsoft Presidio when installed,
with a zero-dependency regex fallback. Operates on result data, on-prem.
"""
from .veil import Veil

__all__ = ["Veil"]
__version__ = "0.1.0"
