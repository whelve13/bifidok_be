"""
Anti-Hallucination Verbatim Guardrail Module.
Ensures every extracted quote exists verbatim in public source documents.
"""
import re
from typing import Optional


def verify_verbatim_quote(quote: str, source_text: str, min_length: int = 15) -> bool:
    """
    Symbolic assertion verifying that the extracted evidence quote exists
    verbatim (character-level or normalized whitespace) within the source text.

    Args:
        quote: Extracted evidence quote string.
        source_text: Raw ingested text stream.
        min_length: Minimum character length to prevent trivial single-word matches.

    Returns:
        True if quote exists verbatim, False otherwise.
    """
    if not quote or not source_text:
        return False

    clean_quote = quote.strip().strip("\"'")
    if len(clean_quote) < min_length:
        return False

    # 1. Exact string containment
    if clean_quote in source_text:
        return True

    # 2. Whitespace-normalized containment
    norm_quote = re.sub(r"\s+", " ", clean_quote.lower()).strip()
    norm_source = re.sub(r"\s+", " ", source_text.lower()).strip()

    if norm_quote in norm_source:
        return True

    # 3. Punctuation-relaxed containment
    punct_quote = re.sub(r"[^\w\s]", "", norm_quote).strip()
    punct_source = re.sub(r"[^\w\s]", "", norm_source).strip()

    if len(punct_quote) >= min_length and punct_quote in punct_source:
        return True

    return False
