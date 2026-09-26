"""
Anti-hallucination verification guardrails.
Enforces programmatic assertion that extracted LLM evidence quotes
exist verbatim within the original ingested source text (Annex Section 4.1).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_verbatim_quote(evidence_quote: Optional[str], source_text: Optional[str]) -> bool:
    """
    Programmatic anti-hallucination guardrail (Annex Section 4.1).
    Asserts that evidence_quote.strip().lower() exists as a verbatim substring
    inside source_text.lower().

    Args:
        evidence_quote: The candidate quote extracted by the LLM.
        source_text: The original raw source document or snippet.

    Returns:
        bool: True if matched verbatim, False otherwise.
    """
    if not isinstance(evidence_quote, str) or not isinstance(source_text, str):
        return False

    clean_quote = evidence_quote.strip()
    clean_source = source_text.strip()
    if not clean_quote or not clean_source:
        return False

    # 1. Exact or case-insensitive substring match
    if clean_quote.lower() in clean_source.lower():
        return True

    # 2. Stripped outer quotation marks (common LLM formatting artifact)
    unquoted = clean_quote.strip('"\'“”`')
    if unquoted and unquoted.lower() in clean_source.lower():
        return True

    # 3. Normalized whitespace match
    norm_quote = " ".join(unquoted.split()).lower()
    norm_source = " ".join(clean_source.split()).lower()
    if norm_quote and norm_quote in norm_source:
        return True

    logger.warning(
        "Anti-hallucination check failed: Quote '%s' not found verbatim in source text.",
        evidence_quote[:80],
    )
    return False
