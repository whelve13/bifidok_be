"""
Engine package for scoring, offering catalog, prospecting, and anti-hallucination guardrails.
"""
from .anti_hallucination import verify_verbatim_quote

__all__ = [
    "verify_verbatim_quote",
]
