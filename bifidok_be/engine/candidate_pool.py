"""
Candidate Pool & Enterprise Universe Module.

DEPRECATED & DROPPED:
The candidate pool feature has been decommissioned to ensure the customer prospecting
engine remains unbiased and dynamically discovers companies across any industry or geography.
"""
from typing import Any, Dict, List, Optional

# Deprecated: Candidate pool dropped to eliminate bias towards predefined enterprise accounts.
ENTERPRISE_UNIVERSE: List[Dict[str, Any]] = []


def get_candidate_universe() -> List[Dict[str, Any]]:
    """
    Deprecated: Returns an empty list as the candidate pool feature has been dropped.
    All prospect accounts are now discovered dynamically.
    """
    return []


def find_candidate_by_name(name_or_domain: str) -> Optional[Dict[str, Any]]:
    """
    Deprecated: Returns None as the candidate pool feature has been dropped.
    Company accounts are now resolved dynamically via live firmographic and registry connectors.
    """
    return None
