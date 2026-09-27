"""
Leads and signal evidence API routes.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from db.session import get_db
    from services.leads_service import (
        query_prioritized_leads,
        query_signal_evidence,
        record_lead_feedback,
    )
except ImportError:
    from bifidok_be.db.session import get_db
    from bifidok_be.services.leads_service import (
        query_prioritized_leads,
        query_signal_evidence,
        record_lead_feedback,
    )

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadFeedbackRequest(BaseModel):
    is_accurate: Optional[bool] = Field(
        None,
        description="True for thumbs up (accurate qualification), False for thumbs down",
    )
    thumbs_up: Optional[bool] = Field(
        None,
        description="Alternative boolean field for thumbs up / thumbs down",
    )
    notes: Optional[str] = Field(
        "",
        description="Optional human-in-the-loop qualitative feedback notes",
    )


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]], include_in_schema=False)
def get_prioritized_leads(
    service_line: str = Query(
        default="Agentic Automation",
        description="Commercial service offering to query leads for",
    ),
    min_score: int = Query(
        default=70,
        ge=0,
        le=100,
        description="Minimum composite readiness score threshold",
    ),
    db: Session = Depends(get_db),
):
    """
    Discovers top enterprise leads prioritized by verified buying signals.
    """
    leads = query_prioritized_leads(service_line=service_line, min_score=min_score, session=db)
    return leads


@router.get("/{domain}/evidence", response_model=Dict[str, Any])
def get_lead_evidence(domain: str, db: Session = Depends(get_db)):
    """
    Retrieves exact verbatim quotes and source links justifying why a company is ready to buy.
    """
    clean_domain = str(domain or "").strip().lower()
    evidence = query_signal_evidence(clean_domain, session=db)
    return evidence


@router.post("/{lead_id}/feedback", response_model=Dict[str, Any])
def submit_lead_feedback(lead_id: str, feedback: LeadFeedbackRequest):
    """
    Captures thumbs up/down human-in-the-loop scoring feedback for continuous model calibration.
    """
    if feedback.is_accurate is not None:
        accurate = bool(feedback.is_accurate)
    elif feedback.thumbs_up is not None:
        accurate = bool(feedback.thumbs_up)
    else:
        accurate = True

    feedback_record = record_lead_feedback(
        lead_id=str(lead_id),
        is_accurate=accurate,
        notes=feedback.notes or "",
    )
    return feedback_record


class ProspectUniverseRequest(BaseModel):
    offering: str = Field(default="Agentic Automation", description="Target commercial mandate or offering")
    max_accounts: int = Field(default=8, ge=1, le=30, description="Max candidate accounts to evaluate")


@router.post("/prospect", response_model=Dict[str, Any])
def prospect_commercial_universe(request: ProspectUniverseRequest):
    """
    Triggers the autonomous prospecting engine across open sources,
    applying local ML models and the Gemini Commercial Verification anti-false-positive filter.
    """
    try:
        from engine.prospecting_engine import CustomerProspectingEngine
    except ImportError:
        from bifidok_be.engine.prospecting_engine import CustomerProspectingEngine

    engine = CustomerProspectingEngine()
    result = engine.prospect_universe(offering=request.offering, max_accounts=request.max_accounts)

    leads = []
    for d in result.ranked_customers:
        d_dict = d.model_dump()
        c = d.company
        leads.append({
            "id": f"lead-{c.domain.replace('.', '-')}",
            "company": c.name,
            "name": c.name,
            "domain": c.domain,
            "score": round(d.propensity_score, 1),
            "overallScore": round(d.propensity_score, 1),
            "industry": c.sector,
            "headcount": c.headcount,
            "headquarters": c.country,
            "logo": f"https://logo.clearbit.com/{c.domain}",
            "website": f"https://www.{c.domain}",
            "summary": d.operational_rationale,
            "tier": d.tier,
            "is_disqualified": d.is_disqualified,
            "disqualification_reason": d.disqualification_reason,
            "commercial_wedge": d.primary_commercial_wedge.name,
            "estimated_commercial_scope": d.estimated_commercial_scope,
            "strategic_pitch": d.strategic_pitch_narrative,
            "commercial_verification": d_dict.get("commercial_verification"),
            "signals": [
                {
                    "id": f"sig-{c.domain.replace('.', '-')}-{i}",
                    "title": e.title,
                    "snippet": e.snippet,
                    "source": e.source,
                    "category": e.category,
                    "impact": f"+{int(e.points_awarded)} pts" if e.points_awarded > 0 else "+15 pts",
                    "type": "positive",
                }
                for i, e in enumerate(d.evidence_citations)
            ],
            "keyDecisionMakers": [
                {"name": dm.full_name, "role": dm.title, "focus": dm.seniority}
                for dm in d.target_buying_committee
            ],
            "outreachDraft": {
                "channel": "Executive Email",
                "subject": f"Commercial Synergy: {result.offering.title} for {c.name}",
                "body": d.strategic_pitch_narrative,
            },
        })

    return {
        "status": "COMPLETED",
        "offering_title": result.offering.title,
        "total_evaluated": result.total_evaluated,
        "tier1_count": result.tier1_count,
        "tier2_count": result.tier2_count,
        "leads": leads,
    }

