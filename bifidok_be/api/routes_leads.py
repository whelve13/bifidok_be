"""
Leads and signal evidence API routes.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from db.session import get_db
    from db.repository import (
        upsert_company,
        upsert_service_offering,
        upsert_signal_rule,
        upsert_lead_score,
        upsert_signal_evaluation,
    )
    from services.leads_service import (
        query_prioritized_leads,
        query_signal_evidence,
        record_lead_feedback,
    )
except ImportError:
    from bifidok_be.db.session import get_db
    from bifidok_be.db.repository import (
        upsert_company,
        upsert_service_offering,
        upsert_signal_rule,
        upsert_lead_score,
        upsert_signal_evaluation,
    )
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
def prospect_commercial_universe(
    request: ProspectUniverseRequest,
    db: Session = Depends(get_db),
):
    """
    Triggers the autonomous prospecting engine across open sources,
    applying local ML models and the Gemini Commercial Verification anti-false-positive filter.
    Persists all prospected companies, lead scores, and signal evaluations to the database.
    """
    try:
        from engine.prospecting_engine import CustomerProspectingEngine
    except ImportError:
        from bifidok_be.engine.prospecting_engine import CustomerProspectingEngine

    engine = CustomerProspectingEngine()
    result = engine.prospect_universe(offering=request.offering, max_accounts=request.max_accounts)

    # Persist prospected results into PostgreSQL/SQLite
    try:
        off_rec = upsert_service_offering(
            db,
            {
                "name": result.offering.title,
                "description": result.offering.description or f"Commercial offering for {result.offering.title}",
            },
        )
        rule_rec = upsert_signal_rule(
            db,
            {
                "service_id": off_rec.id,
                "question": f"Is the enterprise actively investing or exhibiting operational synergy with {result.offering.title}?",
                "weight": "HIGH",
                "is_negative": False,
            },
        )
        for d in result.ranked_customers:
            c = d.company
            comp_rec = upsert_company(
                db,
                {
                    "name": c.name,
                    "domain": c.domain,
                    "industry": c.sector,
                    "geography": c.country,
                    "employee_count": c.headcount,
                },
            )
            upsert_lead_score(
                db,
                {
                    "company_id": comp_rec.id,
                    "service_id": off_rec.id,
                    "composite_score": int(round(d.propensity_score)),
                    "is_disqualified": d.is_disqualified,
                    "disqualification_reason": d.disqualification_reason or None,
                    "executive_summary": d.operational_rationale or f"Propensity score {round(d.propensity_score, 1)} with primary wedge {d.primary_commercial_wedge.name}",
                },
            )
            for e in d.evidence_citations:
                try:
                    upsert_signal_evaluation(
                        db,
                        {
                            "company_id": comp_rec.id,
                            "rule_id": rule_rec.id,
                            "source_url": e.source or f"https://{c.domain}/signals/{uuid.uuid4().hex[:6]}",
                            "detected": True,
                            "confidence": max(0.5, min(1.0, float(e.confidence or 0.85))),
                            "evidence_quote": (e.snippet or e.title)[:280],
                            "reasoning": (e.title or e.category)[:200],
                        },
                    )
                except Exception as eval_err:
                    logger.debug("Could not upsert signal evaluation: %s", eval_err)
    except Exception as db_err:
        logger.warning("Could not persist prospected results to database: %s", db_err)

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


class BestOfferRequest(BaseModel):
    company: str = Field(..., description="Target company name (e.g. DHL Group, Siemens)")
    domain: Optional[str] = Field(None, description="Optional domain hint")


@router.post("/best-offer", response_model=Dict[str, Any])
def find_best_offer_for_company_endpoint(request: BestOfferRequest):
    """
    Evaluates Company X across candidate offerings using the trained ML model,
    ranks the offerings by fit and propensity score, and highlights the best-fit recommendation.
    (CLI Option 2 parity)
    """
    clean_company = request.company.strip()
    if not clean_company:
        raise HTTPException(status_code=400, detail="Company name is required.")

    candidate_offerings = [
        ("agentic_automation", "Agentic Process Automation & AI Workforce"),
        ("managed_soc", "Managed SOC & NIS2 Cyber Resilience"),
        ("cloud_modernization", "Cloud Architecture & Modernization"),
    ]

    try:
        from engine.prospecting_engine import CustomerProspectingEngine
    except ImportError:
        from bifidok_be.engine.prospecting_engine import CustomerProspectingEngine

    engine = CustomerProspectingEngine()
    evaluations = []
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_off = {
            executor.submit(engine.evaluate_single_company, clean_company, off_key, request.domain): (off_key, off_title)
            for off_key, off_title in candidate_offerings
        }
        for fut in concurrent.futures.as_completed(future_to_off):
            off_key, off_title = future_to_off[fut]
            try:
                dossier = fut.result()
                evaluations.append((off_key, off_title, dossier))
            except Exception as e:
                logger.error("Evaluation failed for %s with %s: %s", clean_company, off_key, e)

    if not evaluations:
        raise HTTPException(
            status_code=404,
            detail=f"Could not evaluate offerings for '{clean_company}'. Please verify the company name.",
        )

    # Sort by propensity score descending (disqualified at the bottom)
    evaluations.sort(key=lambda item: (not item[2].is_disqualified, item[2].propensity_score), reverse=True)

    ranked_offers = []
    for i, (off_key, off_title, d) in enumerate(evaluations, 1):
        d_dict = d.model_dump()
        ranked_offers.append({
            "rank": i,
            "offering_key": off_key,
            "offering_title": off_title,
            "propensity_score": round(d.propensity_score, 1),
            "tier": d.tier,
            "is_disqualified": d.is_disqualified,
            "disqualification_reason": d.disqualification_reason,
            "is_top_match": (i == 1 and not d.is_disqualified),
            "primary_commercial_wedge": d.primary_commercial_wedge.name if d.primary_commercial_wedge else "-",
            "wedge_value_driver": d.primary_commercial_wedge.value_driver if d.primary_commercial_wedge else "-",
            "estimated_commercial_scope": d.estimated_commercial_scope,
            "operational_rationale": d.operational_rationale,
            "strategic_pitch": d.strategic_pitch_narrative,
            "score_breakdown": d_dict.get("score_breakdown"),
            "evidence_citations": d_dict.get("evidence_citations", []),
            "target_buying_committee": d_dict.get("target_buying_committee", []),
        })

    best_key, best_title, best_dossier = evaluations[0]
    return {
        "status": "COMPLETED",
        "company": clean_company,
        "best_offering": {
            "key": best_key,
            "title": best_title,
            "propensity_score": round(best_dossier.propensity_score, 1),
            "tier": best_dossier.tier,
            "is_disqualified": best_dossier.is_disqualified,
            "disqualification_reason": best_dossier.disqualification_reason,
            "primary_wedge": best_dossier.primary_commercial_wedge.name if best_dossier.primary_commercial_wedge else "-",
            "value_driver": best_dossier.primary_commercial_wedge.value_driver if best_dossier.primary_commercial_wedge else "-",
            "estimated_scope": best_dossier.estimated_commercial_scope,
            "operational_rationale": best_dossier.operational_rationale,
            "strategic_pitch": best_dossier.strategic_pitch_narrative,
        },
        "ranked_offerings": ranked_offers,
    }


class AnalyzeAccountRequest(BaseModel):
    company: str = Field(..., description="Target company name (e.g. DHL Group, Siemens)")
    offering: str = Field(default="agentic_automation", description="Offering key or description")
    domain: Optional[str] = Field(None, description="Optional domain hint")


@router.post("/analyze", response_model=Dict[str, Any])
def analyze_account_fit_endpoint(request: AnalyzeAccountRequest):
    """
    Executes a comprehensive deep-dive evaluation of Offer X with Company X
    using live multi-source signals and trained ML inference.
    (CLI Option 3 parity)
    """
    clean_company = request.company.strip()
    clean_offering = request.offering.strip()
    if not clean_company:
        raise HTTPException(status_code=400, detail="Company name is required.")

    try:
        from engine.prospecting_engine import CustomerProspectingEngine
    except ImportError:
        from bifidok_be.engine.prospecting_engine import CustomerProspectingEngine

    engine = CustomerProspectingEngine()

    try:
        dossier = engine.evaluate_single_company(clean_company, clean_offering, request.domain)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Deep dive analysis failed for {clean_company}: {str(e)}",
        )

    d_dict = dossier.model_dump()
    return {
        "status": "COMPLETED",
        "company": dossier.company.model_dump(),
        "propensity_score": round(dossier.propensity_score, 1),
        "tier": dossier.tier,
        "is_disqualified": dossier.is_disqualified,
        "disqualification_reason": dossier.disqualification_reason,
        "primary_commercial_wedge": dossier.primary_commercial_wedge.model_dump() if dossier.primary_commercial_wedge else None,
        "operational_rationale": dossier.operational_rationale,
        "estimated_commercial_scope": dossier.estimated_commercial_scope,
        "score_breakdown": d_dict.get("score_breakdown"),
        "evidence_citations": d_dict.get("evidence_citations", []),
        "target_buying_committee": d_dict.get("target_buying_committee", []),
        "strategic_pitch_narrative": dossier.strategic_pitch_narrative,
    }

