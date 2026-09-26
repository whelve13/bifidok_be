"""
Engine package for scoring, offering catalog, prospecting, and anti-hallucination guardrails.
"""
from .gemini_extractor import (
    extract_signal_evidence,
    verify_verbatim_quote,
    get_genai_client,
)
from .scoring_service import (
    calculate_deterministic_score,
    compute_composite_3layer_score,
    record_lead_feedback,
    get_lead_feedback,
    clear_lead_feedback,
)

__all__ = [
    "extract_signal_evidence",
    "verify_verbatim_quote",
    "get_genai_client",
    "calculate_deterministic_score",
    "compute_composite_3layer_score",
    "record_lead_feedback",
    "get_lead_feedback",
    "clear_lead_feedback",
from .anti_hallucination import verify_verbatim_quote

__all__ = [
    "verify_verbatim_quote",
]
