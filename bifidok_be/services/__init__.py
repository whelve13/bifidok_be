"""
Services package for Orange Systems sales intelligence platform.
"""
from .cache import (
    get_cache,
    set_cache,
    delete_cache,
    update_job_status,
    get_job_status,
    get_redis_client,
)
from .leads_service import (
    query_prioritized_leads,
    query_signal_evidence,
    format_grounded_pitch,
    queue_sales_outreach,
    OUTREACH_QUEUE,
)


def __getattr__(name: str):
    if name == "run_async_ingestion":
        from .ingestion_coordinator import run_async_ingestion
        return run_async_ingestion
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "get_cache",
    "set_cache",
    "delete_cache",
    "update_job_status",
    "get_job_status",
    "get_redis_client",
    "run_async_ingestion",
    "query_prioritized_leads",
    "query_signal_evidence",
    "format_grounded_pitch",
    "queue_sales_outreach",
    "OUTREACH_QUEUE",
]
