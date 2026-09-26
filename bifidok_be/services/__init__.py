"""
Services package for Orange Systems sales intelligence platform.
"""
from .leads_service import (
    query_prioritized_leads,
    query_signal_evidence,
    format_grounded_pitch,
    queue_sales_outreach,
    OUTREACH_QUEUE,
)

__all__ = [
    "query_prioritized_leads",
    "query_signal_evidence",
    "format_grounded_pitch",
    "queue_sales_outreach",
    "OUTREACH_QUEUE",
]
