"""
Sales outreach queue and approval API routes.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

try:
    from services.leads_service import OUTREACH_QUEUE, get_redis_client, queue_sales_outreach
except ImportError:
    from bifidok_be.services.leads_service import OUTREACH_QUEUE, get_redis_client, queue_sales_outreach

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


class StageOutreachRequest(BaseModel):
    recipient_email: str = Field(..., description="Target contact email address")
    subject: str = Field(..., description="Outreach email subject line")
    email_body: str = Field(..., description="Outreach email text body")
    dry_run: bool = Field(True, description="When True, stages draft for human review")


class ApproveDraftResponse(BaseModel):
    status: str
    message: str
    draft: Dict[str, Any]


@router.get("/queue", response_model=List[Dict[str, Any]])
def get_outreach_queue():
    """
    Returns all staged drafts in OUTREACH_QUEUE or Redis with status AWAITING_HUMAN_APPROVAL.
    """
    staged_items: List[Dict[str, Any]] = []
    seen_ids = set()

    # 1. Fetch from Redis if available
    r = get_redis_client()
    if r:
        try:
            keys = r.keys("outreach_queue:*")
            for key in keys:
                raw_data = r.get(key)
                if raw_data:
                    item = json.loads(raw_data)
                    if item.get("status") == "AWAITING_HUMAN_APPROVAL":
                        draft_id = item.get("draft_id") or key.split(":")[-1]
                        item["draft_id"] = draft_id
                        staged_items.append(item)
                        seen_ids.add(draft_id)
        except Exception as exc:
            logger.debug("Failed querying Redis outreach queue: %s", exc)

    # 2. Fetch from in-memory OUTREACH_QUEUE
    for draft_id, draft in OUTREACH_QUEUE.items():
        if draft.get("status") == "AWAITING_HUMAN_APPROVAL":
            if draft_id not in seen_ids:
                item = dict(draft)
                item["draft_id"] = draft_id
                staged_items.append(item)
                seen_ids.add(draft_id)

    return staged_items


@router.post("/{draft_id}/approve", response_model=ApproveDraftResponse)
def approve_outreach_draft(draft_id: str):
    """
    Updates draft status to DISPATCHED and simulates dispatch.
    """
    draft: Optional[Dict[str, Any]] = None
    r = get_redis_client()

    # Check in-memory store
    if draft_id in OUTREACH_QUEUE:
        draft = OUTREACH_QUEUE[draft_id]
    elif r:
        try:
            raw_val = r.get(f"outreach_queue:{draft_id}")
            if raw_val:
                draft = json.loads(raw_val)
        except Exception:
            pass

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outreach draft '{draft_id}' not found in queue.",
        )

    # Transition status to DISPATCHED and record simulated delivery timestamp
    draft["status"] = "DISPATCHED"
    draft["dispatched_at"] = datetime.now(timezone.utc).isoformat()
    draft["simulated_dispatch"] = True

    # Persist updated draft in memory
    OUTREACH_QUEUE[draft_id] = draft

    # Persist in Redis if active
    if r:
        try:
            r.set(f"outreach_queue:{draft_id}", json.dumps(draft))
        except Exception:
            pass

    return ApproveDraftResponse(
        status="DISPATCHED",
        message=f"Draft {draft_id} approved and dispatched successfully.",
        draft=draft,
    )


@router.post("/stage", response_model=Dict[str, Any])
@router.post("", response_model=Dict[str, Any], include_in_schema=False)
def stage_new_outreach(request: StageOutreachRequest):
    """
    Stages or sends a new sales outreach email draft.
    """
    return queue_sales_outreach(
        recipient_email=request.recipient_email,
        subject=request.subject,
        email_body=request.email_body,
        dry_run=request.dry_run,
    )
