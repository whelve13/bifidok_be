"""
Autonomous Enterprise Discovery & Commercial Offering Engine.
"""
from .anti_hallucination import verify_verbatim_quote
from .offering_catalog import (
    FLAGSHIP_OFFERINGS,
    decompose_custom_offering,
    offering_dict_to_profile,
)
from .prospecting_engine import CustomerProspectingEngine

__all__ = [
    "verify_verbatim_quote",
    "FLAGSHIP_OFFERINGS",
    "decompose_custom_offering",
    "offering_dict_to_profile",
    "CustomerProspectingEngine",
]
