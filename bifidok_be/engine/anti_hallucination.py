"""
Anti-hallucination verification guardrails.
Enforces programmatic assertion that extracted LLM evidence quotes
exist verbatim within the original ingested source text (Section 4.1).
"""
import logging

logger = logging.getLogger(__name__)


def verify_verbatim_quote(evidence_quote: str, source_text: str) -> bool:
    """
    Verifies that evidence_quote exists as an exact verbatim substring within source_text.
    Comparison is case-insensitive and ignores surrounding whitespace.

    Args:
        evidence_quote: The candidate quote extracted by the LLM.
        source_text: The original raw source document or snippet.

    Returns:
        bool: True if evidence_quote is a non-empty verbatim substring of source_text,
              False otherwise (rejecting the extraction).
    """
    if not isinstance(evidence_quote, str) or not isinstance(source_text, str):
        return False

    clean_quote = evidence_quote.strip().lower()
    if not clean_quote:
        return False

    clean_source = source_text.lower()
    if clean_quote in clean_source:
        return True

    logger.warning(
        "Anti-hallucination check failed: Quote '%s' not found verbatim in source text.",
        evidence_quote[:80],
    )
    return False
