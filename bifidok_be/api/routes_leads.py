"""
Leads and signal evidence API routes.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import concurrent.futures

try:
    from cli import get_prospecting_engine
except ImportError:
    from bifidok_be.cli import get_prospecting_engine

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

class ProspectRequest(BaseModel):
    offering: str = "agentic_automation"
    max_accounts: int = 8
    geographies: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    min_headcount: Optional[int] = 1000

class BestOfferRequest(BaseModel):
    company: str
    domain: Optional[str] = None

class AnalyzeAccountRequest(BaseModel):
    company: str
    offering: str = "agentic_automation"
    domain: Optional[str] = None

@router.post("/prospect", response_model=Dict[str, Any])
def prospect_leads(req: ProspectRequest):
    engine = get_prospecting_engine()
    result = engine.prospect_universe(req.offering)
    
    ranked = result.ranked_customers
    # Apply optional ICP filters
    if req.min_headcount:
        ranked = [c for c in ranked if (c.company.headcount or 0) >= req.min_headcount]
    if req.industries:
        ranked = [c for c in ranked if any(ind.lower() in (c.company.sector or "").lower() for ind in req.industries)]
    if req.geographies:
        ranked = [c for c in ranked if any(geo.lower() in (c.company.country or "").lower() for geo in req.geographies)]
        
    ranked = ranked[:req.max_accounts]
    
    leads_payload = []
    for d in ranked:
        leads_payload.append({
            "id": f"lead-{d.company.domain.replace('.', '-')}",
            "name": d.company.name,
            "domain": d.company.domain,
            "industry": d.company.sector,
            "headquarters": d.company.country,
            "headcount": d.company.headcount or 0,
            "overallScore": round(d.propensity_score, 1),
            "tier": d.tier,
            "commercial_wedge": d.primary_commercial_wedge.name if d.primary_commercial_wedge else "Enterprise Co-Delivery",
            "wedge_value_driver": d.primary_commercial_wedge.value_driver if d.primary_commercial_wedge else "",
            "estimated_commercial_scope": d.estimated_commercial_scope,
            "operational_rationale": d.operational_rationale,
            "scoreBreakdown": {
                "operational_fit": round(d.score_breakdown.operational_fit, 1),
                "timing_urgency": round(d.score_breakdown.timing_urgency, 1),
                "purchasing_scale": round(d.score_breakdown.purchasing_scale, 1),
                "hiring_intent": round(d.score_breakdown.hiring_intent, 1),
                "composite_score": round(d.score_breakdown.composite_score, 1),
            },
            "signals": [
                {
                    "id": f"sig-{i}",
                    "category": ev.category.upper(),
                    "snippet": ev.snippet,
                    "source": "Live Public Filing / Connector",
                    "source_url": getattr(ev, "source_url", f"https://news.google.com/search?q={d.company.name}"),
                    "impact": f"+{int(ev.confidence * 30)} pts",
                    "type": "positive",
                }
                for i, ev in enumerate(d.evidence_citations[:4])
            ],
            "keyDecisionMakers": [
                {"name": p.title, "role": p.department, "focus": p.mandate}
                for p in d.target_buying_committee
            ],
            "outreachDraft": {
                "channel": "Executive Email",
                "subject": f"Commercial Partnership: {result.offering.title} for {d.company.name}",
                "body": d.strategic_pitch_narrative,
            },
        })
        
    return {
        "success": True,
        "offering_title": result.offering.title,
        "total_evaluated": result.total_evaluated,
        "tier1_count": result.tier1_count,
        "tier2_count": result.tier2_count,
        "leads": leads_payload,
    }

@router.post("/best-offer", response_model=Dict[str, Any])
def evaluate_best_offer(req: BestOfferRequest):
    engine = get_prospecting_engine()
    clean_company = req.company.strip()
    candidate_offerings = [
        ("agentic_automation", "Agentic Process Automation & AI Workforce"),
        ("managed_soc", "Managed SOC & NIS2 Cyber Resilience"),
        ("cloud_modernization", "Cloud Architecture & Modernization"),
        ("commercial_bikes", "Commercial Fleet & Last-Mile Logistics"),
    ]
    
    evaluations = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_off = {
            executor.submit(engine.evaluate_single_company, clean_company, off_key, req.domain): (off_key, off_title)
            for off_key, off_title in candidate_offerings
        }
        for fut in concurrent.futures.as_completed(future_to_off):
            off_key, off_title = future_to_off[fut]
            try:
                dossier = fut.result()
                evaluations.append((off_key, off_title, dossier))
            except Exception as exc:
                continue
                
    if not evaluations:
        raise HTTPException(status_code=404, detail=f"Could not resolve entity '{clean_company}'")
        
    evaluations.sort(key=lambda item: (not item[2].is_disqualified, item[2].propensity_score), reverse=True)
    
    formatted_evals = []
    for i, (off_key, off_title, d) in enumerate(evaluations):
        formatted_evals.append({
            "offeringKey": off_key,
            "offeringTitle": off_title,
            "score": round(d.propensity_score, 1),
            "tier": d.tier,
            "wedge": d.primary_commercial_wedge.name if d.primary_commercial_wedge else "-",
            "wedgeValueDriver": d.primary_commercial_wedge.value_driver if d.primary_commercial_wedge else "",
            "estimatedScope": d.estimated_commercial_scope,
            "isDisqualified": d.is_disqualified,
            "disqualificationReason": d.disqualification_reason or "",
            "isTopMatch": (i == 0 and not d.is_disqualified),
        })
        
    best_key, best_title, best_d = evaluations[0]
    return {
        "company": {
            "name": best_d.company.name,
            "domain": best_d.company.domain,
            "sector": best_d.company.sector,
            "country": best_d.company.country,
            "headcount": best_d.company.headcount or 0,
        },
        "bestOffering": formatted_evals[0],
        "evaluations": formatted_evals,
    }

@router.post("/analyze", response_model=Dict[str, Any])
def analyze_account(req: AnalyzeAccountRequest):
    engine = get_prospecting_engine()
    dossier = engine.evaluate_single_company(req.company.strip(), req.offering.strip(), req.domain)
    
    return {
        "company": {
            "name": dossier.company.name,
            "domain": dossier.company.domain,
            "sector": dossier.company.sector,
            "country": dossier.company.country,
            "headcount": dossier.company.headcount or 0,
            "is_solvent": dossier.company.is_solvent,
        },
        "offering": req.offering,
        "propensity_score": round(dossier.propensity_score, 1),
        "tier": dossier.tier,
        "is_disqualified": dossier.is_disqualified,
        "disqualification_reason": dossier.disqualification_reason or "",
        "commercial_wedge": dossier.primary_commercial_wedge.name if dossier.primary_commercial_wedge else "Enterprise Co-Delivery",
        "wedge_value_driver": dossier.primary_commercial_wedge.value_driver if dossier.primary_commercial_wedge else "",
        "estimated_commercial_scope": dossier.estimated_commercial_scope,
        "operational_rationale": dossier.operational_rationale,
        "score_breakdown": {
            "operational_fit": round(dossier.score_breakdown.operational_fit, 1),
            "timing_urgency": round(dossier.score_breakdown.timing_urgency, 1),
            "purchasing_scale": round(dossier.score_breakdown.purchasing_scale, 1),
            "hiring_intent": round(dossier.score_breakdown.hiring_intent, 1),
            "composite_score": round(dossier.score_breakdown.composite_score, 1),
        },
        "evidence_citations": [
            {
                "category": ev.category.upper(),
                "snippet": ev.snippet,
                "confidence": round(ev.confidence, 2),
                "source_url": getattr(ev, "source_url", f"https://news.google.com/search?q={dossier.company.name}"),
            }
            for ev in dossier.evidence_citations
        ],
        "target_buying_committee": [
            {
                "title": p.title,
                "department": p.department,
                "mandate": p.mandate,
                "outreach_hook": p.outreach_hook,
            }
            for p in dossier.target_buying_committee
        ],
        "strategic_pitch_narrative": dossier.strategic_pitch_narrative,
    }
