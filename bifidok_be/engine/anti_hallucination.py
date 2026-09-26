"""
Anti-hallucination verification guardrails.
Enforces programmatic assertion that extracted LLM evidence quotes
exist verbatim within the original ingested source text (Section 4.1).
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def verify_verbatim_quote(evidence_quote: Optional[str], source_text: Optional[str]) -> bool:
    """
    Programmatic anti-hallucination guardrail (Annex Section 4.1).
    Asserts that the extracted evidence quote exists verbatim within the source passage.

    Handles case-insensitivity, surrounding whitespace, outer quotation marks,
    and normalized internal whitespace/linebreaks.

    Args:
        evidence_quote: The candidate quote extracted by the LLM.
        source_text: The original raw source document or snippet.

    Returns:
        bool: True if evidence_quote is a non-empty verbatim substring of source_text,
              False otherwise (rejecting the extraction).
    """
    if not isinstance(evidence_quote, str) or not isinstance(source_text, str):
        return False

    quote = evidence_quote.strip()
    source = source_text.strip()
    if not quote or not source:
        return False

    # 1. Exact or case-insensitive substring match
    if quote in source_text or quote.lower() in source_text.lower():
        return True

    # 2. Stripped outer quotation marks (common LLM formatting artifact)
    clean_quote = quote.strip('"\'“”`')
    if clean_quote and (clean_quote in source_text or clean_quote.lower() in source_text.lower()):
        return True

    # 3. Normalized whitespace match (collapses tabs, multiple spaces, line-breaks)
    norm_quote = " ".join(clean_quote.split()).lower()
    norm_source = " ".join(source_text.split()).lower()
    if norm_quote and norm_quote in norm_source:
        return True

    logger.warning(
        "Anti-hallucination check failed: Quote '%s' not found verbatim in source text.",
        evidence_quote[:80],
    )
    return False
