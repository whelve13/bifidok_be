"""
Data access repository for Enterprise AI Sales Intelligence Platform.
Implements bounded upsert operations and query helpers conforming to Section 3.2
and the 500MB storage budget constraint.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .schema import (
    Company,
    LeadScore,
    MCPApiKey,
    ServiceOffering,
    SignalEvaluation,
    SignalRule,
    SignalWeightType,
)


def to_uuid(val: Any) -> Optional[uuid.UUID]:
    """Coerces a string or UUID object into a Python uuid.UUID instance."""
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError, AttributeError):
        return None


def to_dict(data: Any) -> Dict[str, Any]:
    """Normalizes Pydantic models, dicts, or objects with attributes into a dictionary."""
    if hasattr(data, "model_dump"):
        return data.model_dump()
    if hasattr(data, "dict"):
        return data.dict()
    if isinstance(data, dict):
        return data.copy()
    try:
        return dict(data)
    except (TypeError, ValueError):
        return {
            key: getattr(data, key)
            for key in dir(data)
            if not key.startswith("_") and not callable(getattr(data, key))
        }


def upsert_company(session: Session, data: Union[Dict[str, Any], Any]) -> Company:
    """
    Inserts or updates a Company record by unique domain.
    """
    data_dict = to_dict(data)
    domain = str(data_dict.get("domain") or "").strip().lower()
    if not domain:
        raise ValueError("Company domain is required for upsert.")

    company = session.query(Company).filter(Company.domain == domain).first()
    if company:
        if "name" in data_dict and data_dict["name"] is not None:
            company.name = data_dict["name"]
        if "industry" in data_dict:
            company.industry = data_dict["industry"]
        if "geography" in data_dict:
            company.geography = data_dict["geography"]
        if "employee_count" in data_dict:
            company.employee_count = data_dict["employee_count"]
    else:
        comp_id = to_uuid(data_dict.get("id")) or uuid.uuid4()
        company = Company(
            id=comp_id,
            name=data_dict.get("name") or domain,
            domain=domain,
            industry=data_dict.get("industry"),
            geography=data_dict.get("geography"),
            employee_count=data_dict.get("employee_count"),
            created_at=data_dict.get("created_at") or datetime.now(timezone.utc),
        )
        session.add(company)

    session.commit()
    session.refresh(company)
    return company


def upsert_signal_evaluation(
    session: Session,
    data: Union[Dict[str, Any], Any],
) -> Optional[SignalEvaluation]:
    """
    Upserts a signal evaluation on conflict for (company_id, rule_id, source_url).

    Budget Guardrail (500MB):
    - Discards record (returns None) if detected is False or confidence < 0.50.
    - Truncates evidence_quote to max 280 characters.
    - Truncates reasoning to max 200 characters.
    """
    data_dict = to_dict(data)

    detected = data_dict.get("detected")
    if isinstance(detected, str):
        detected = detected.strip().lower() in ("true", "1", "yes")
    else:
        detected = bool(detected)

    try:
        confidence = float(data_dict.get("confidence", 0.0) or 0.0)
    except (ValueError, TypeError):
        confidence = 0.0

    # 500MB storage constraint: drop non-signals or low-confidence noise
    if not detected or confidence < 0.50:
        return None

    # Length truncations for bounded storage footprint
    raw_quote = str(data_dict.get("evidence_quote") or "")
    evidence_quote = raw_quote[:280]

    raw_reasoning = str(data_dict.get("reasoning") or "")
    reasoning = raw_reasoning[:200]

    company_id = to_uuid(data_dict.get("company_id"))
    rule_id = to_uuid(data_dict.get("rule_id"))
    source_url = str(data_dict.get("source_url") or "").strip()

    if not company_id or not rule_id or not source_url:
        raise ValueError(
            "company_id, rule_id, and source_url are required for signal evaluation upsert."
        )

    evaluation = (
        session.query(SignalEvaluation)
        .filter(
            SignalEvaluation.company_id == company_id,
            SignalEvaluation.rule_id == rule_id,
            SignalEvaluation.source_url == source_url,
        )
        .first()
    )

    if evaluation:
        evaluation.detected = detected
        evaluation.confidence = confidence
        evaluation.evidence_quote = evidence_quote
        evaluation.reasoning = reasoning
        if "evaluated_at" in data_dict and data_dict["evaluated_at"] is not None:
            evaluation.evaluated_at = data_dict["evaluated_at"]
        else:
            evaluation.evaluated_at = datetime.now(timezone.utc)
    else:
        eval_id = to_uuid(data_dict.get("id")) or uuid.uuid4()
        evaluated_at = data_dict.get("evaluated_at") or datetime.now(timezone.utc)
        evaluation = SignalEvaluation(
            id=eval_id,
            company_id=company_id,
            rule_id=rule_id,
            source_url=source_url,
            detected=detected,
            confidence=confidence,
            evidence_quote=evidence_quote,
            reasoning=reasoning,
            evaluated_at=evaluated_at,
        )
        session.add(evaluation)

    session.commit()
    session.refresh(evaluation)
    return evaluation


def upsert_lead_score(
    session: Session,
    data: Union[Dict[str, Any], Any],
) -> LeadScore:
    """
    Upserts an aggregated lead score on conflict for (company_id, service_id).
    """
    data_dict = to_dict(data)

    company_id = to_uuid(data_dict.get("company_id"))
    service_id = to_uuid(data_dict.get("service_id"))

    if not company_id or not service_id:
        raise ValueError(
            "Both company_id and service_id are required for lead score upsert."
        )

    composite_score = int(data_dict.get("composite_score", 0))
    composite_score = max(0, min(100, composite_score))
    is_disqualified = bool(data_dict.get("is_disqualified", False))
    disqualification_reason = data_dict.get("disqualification_reason")
    executive_summary = data_dict.get("executive_summary")
    updated_at = data_dict.get("updated_at") or datetime.now(timezone.utc)

    lead = (
        session.query(LeadScore)
        .filter(
            LeadScore.company_id == company_id,
            LeadScore.service_id == service_id,
        )
        .first()
    )

    if lead:
        lead.composite_score = composite_score
        lead.is_disqualified = is_disqualified
        lead.disqualification_reason = disqualification_reason
        lead.executive_summary = executive_summary
        lead.updated_at = updated_at
    else:
        lead_id = to_uuid(data_dict.get("id")) or uuid.uuid4()
        lead = LeadScore(
            id=lead_id,
            company_id=company_id,
            service_id=service_id,
            composite_score=composite_score,
            is_disqualified=is_disqualified,
            disqualification_reason=disqualification_reason,
            executive_summary=executive_summary,
            updated_at=updated_at,
        )
        session.add(lead)

    session.commit()
    session.refresh(lead)
    return lead


def get_leads_by_service(
    session: Session,
    service_id: Union[uuid.UUID, str],
    min_score: int = 0,
) -> List[LeadScore]:
    """
    Retrieves prioritized lead scores for a given service line filtered by min_score,
    sorted in descending order of composite readiness score.
    """
    svc_id = to_uuid(service_id)
    if not svc_id:
        return []

    return (
        session.query(LeadScore)
        .filter(
            LeadScore.service_id == svc_id,
            LeadScore.composite_score >= int(min_score),
        )
        .order_by(LeadScore.composite_score.desc())
        .all()
    )


def upsert_service_offering(
    session: Session,
    data: Union[Dict[str, Any], Any],
) -> ServiceOffering:
    """
    Helper to upsert a service offering by unique name.
    """
    data_dict = to_dict(data)
    name = str(data_dict.get("name") or "").strip()
    if not name:
        raise ValueError("ServiceOffering name is required.")

    offering = session.query(ServiceOffering).filter(ServiceOffering.name == name).first()
    if offering:
        if "description" in data_dict:
            offering.description = data_dict["description"]
    else:
        offering_id = to_uuid(data_dict.get("id")) or uuid.uuid4()
        offering = ServiceOffering(
            id=offering_id,
            name=name,
            description=data_dict.get("description"),
        )
        session.add(offering)

    session.commit()
    session.refresh(offering)
    return offering


def upsert_signal_rule(
    session: Session,
    data: Union[Dict[str, Any], Any],
) -> SignalRule:
    """
    Helper to insert or update a SignalRule.
    """
    data_dict = to_dict(data)
    service_id = to_uuid(data_dict.get("service_id"))
    question = str(data_dict.get("question") or "").strip()
    rule_id = to_uuid(data_dict.get("id"))

    if not service_id or not question:
        raise ValueError("service_id and question are required for signal rule.")

    rule = None
    if rule_id:
        rule = session.query(SignalRule).filter(SignalRule.id == rule_id).first()
    if not rule:
        rule = (
            session.query(SignalRule)
            .filter(
                SignalRule.service_id == service_id,
                SignalRule.question == question,
            )
            .first()
        )

    weight = data_dict.get("weight", SignalWeightType.MEDIUM)
    if isinstance(weight, str):
        weight = SignalWeightType(weight.upper())
    is_negative = bool(data_dict.get("is_negative", False))
    guidance = data_dict.get("guidance_notes")

    if rule:
        rule.guidance_notes = guidance
        rule.weight = weight
        rule.is_negative = is_negative
    else:
        rule = SignalRule(
            id=rule_id or uuid.uuid4(),
            service_id=service_id,
            question=question,
            guidance_notes=guidance,
            weight=weight,
            is_negative=is_negative,
            created_at=data_dict.get("created_at") or datetime.now(timezone.utc),
        )
        session.add(rule)

    session.commit()
    session.refresh(rule)
    return rule


def create_mcp_api_key(
    session: Session,
    data: Union[Dict[str, Any], Any],
) -> MCPApiKey:
    """
    Helper to create an MCP API key entry.
    """
    data_dict = to_dict(data)
    key_hash = str(data_dict.get("key_hash") or "").strip()
    tenant_name = str(data_dict.get("tenant_name") or "").strip()

    if not key_hash or not tenant_name:
        raise ValueError("tenant_name and key_hash are required.")

    api_key = session.query(MCPApiKey).filter(MCPApiKey.key_hash == key_hash).first()
    if api_key:
        api_key.tenant_name = tenant_name
        api_key.is_active = bool(data_dict.get("is_active", True))
    else:
        key_id = to_uuid(data_dict.get("id")) or uuid.uuid4()
        api_key = MCPApiKey(
            id=key_id,
            tenant_name=tenant_name,
            key_hash=key_hash,
            is_active=bool(data_dict.get("is_active", True)),
            created_at=data_dict.get("created_at") or datetime.now(timezone.utc),
        )
        session.add(api_key)

    session.commit()
    session.refresh(api_key)
    return api_key


def get_mcp_api_key(session: Session, key_hash: str) -> Optional[MCPApiKey]:
    """
    Retrieves active MCP API key record by SHA-256 key hash.
    """
    return (
        session.query(MCPApiKey)
        .filter(MCPApiKey.key_hash == key_hash, MCPApiKey.is_active.is_(True))
        .first()
    )
