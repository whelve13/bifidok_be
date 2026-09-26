"""
Prospecting Engine utilities for resolving commercial offerings and prospecting universes.
"""
from typing import Any, Dict, Optional, Union

from engine.offering_catalog import (
    FLAGSHIP_OFFERINGS,
    OfferingProfile,
    decompose_custom_offering,
    offering_dict_to_profile,
)


class CustomerProspectingEngine:
    """
    Lightweight commercial offering resolver and prospect pipeline orchestrator.
    """

    def _resolve_offering(self, offering_input: Union[str, Dict[str, Any], OfferingProfile]) -> OfferingProfile:
        if isinstance(offering_input, OfferingProfile):
            return offering_input
        if isinstance(offering_input, dict):
            return offering_dict_to_profile(offering_input)
        if isinstance(offering_input, str):
            clean = offering_input.strip()
            if clean in FLAGSHIP_OFFERINGS:
                return FLAGSHIP_OFFERINGS[clean]
            # Search case-insensitively
            for key, off in FLAGSHIP_OFFERINGS.items():
                if key.lower() == clean.lower() or off.title.lower() == clean.lower():
                    return off
            # Otherwise decompose custom offering
            compiled = decompose_custom_offering(clean)
            return offering_dict_to_profile(compiled)
        raise ValueError(f"Cannot resolve offering from: {offering_input}")
