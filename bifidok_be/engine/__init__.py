"""
Autonomous Enterprise Discovery & Customer Prospecting Engine.
"""
from .offering_catalog import FLAGSHIP_OFFERINGS, decompose_custom_offering
from .candidate_pool import get_candidate_universe, find_candidate_by_name
from .prospecting_engine import CustomerProspectingEngine
from .anti_hallucination import verify_verbatim_quote

__all__ = [
    "FLAGSHIP_OFFERINGS",
    "decompose_custom_offering",
    "get_candidate_universe",
    "find_candidate_by_name",
    "CustomerProspectingEngine",
    "verify_verbatim_quote",
]

