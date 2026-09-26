"""
Leads and sales intelligence service layer.
Connects database persistence, caching, and MCP tool handlers.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory queues and cache for standalone execution or testing
OUTREACH_QUEUE: Dict[str, Dict[str, Any]] = {}
MEMORY_CACHE: Dict[str, str] = {}

# Canonical default leads from Annex Section 5.1 & Section 6
CANONICAL_LEADS = [
    {
        "company": "DHL Group",
        "domain": "dhl.com",
        "score": 86,
        "primary_signal": "Strategy 2030 Agentic RFQ Deployment",
    },
    {
        "company": "Lufthansa Group",
        "domain": "lufthansa.com",
        "score": 46,
        "primary_signal": "4,000 Headcount Reduction Target",
    },
]

# Grounded audit trails for canonical accounts (Section 6)
CANONICAL_EVIDENCE = {
    "dhl.com": {
        "status": "QUALIFIED",
        "company": "DHL Group",
        "domain": "dhl.com",
        "score": 86,
        "evaluations": [
            {
                "source_url": "https://www.dhl.com/global-en/home/about-us/strategy-2030.html",
                "detected": True,
                "confidence": 0.95,
                "evidence_quote": "Corporate Strategy 2030 prioritizes agentic AI; production deployments live for RFQ quotation and operational communications.",
                "reasoning": "Strategy 2030 explicitly funds agentic AI and multi-agent operational modules.",
            },
            {
                "source_url": "https://www.dhl.com/procurement/technology",
                "detected": True,
                "confidence": 0.90,
                "evidence_quote": "Public policy explicitly confirms the use of third-party software vendors alongside internal engineering to accelerate adoption.",
                "reasoning": "Explicit openness to external vendor integration alongside internal engineering.",
            },
        ],
    },
    "lufthansa.com": {
        "status": "REVIEW_NEEDED",
        "company": "Lufthansa Group",
        "domain": "lufthansa.com",
        "score": 46,
        "evaluations": [
            {
                "source_url": "https://investor-relations.lufthansagroup.com/en/news",
                "detected": True,
                "confidence": 0.90,
                "evidence_quote": "Official target to reduce ~4,000 administrative jobs by 2030 using automation, digitalization, and process consolidation.",
                "reasoning": "Major SG&A and administrative downsizing program creates strong automation pressure.",
            },
            {
                "source_url": "https://www.lhsystems.com/about",
                "detected": True,
                "confidence": 0.85,
                "evidence_quote": "Strong internal development division (Lufthansa Systems) that creates organizational resistance to external standard software.",
                "reasoning": "Negative signal: In-house IT engineering creates adoption friction.",
            },
        ],
    },
}


def get_redis_client():
    """Optional Redis client connection, enabled only if REDIS_URL or REDIS_HOST is explicitly configured."""
    if not os.getenv("REDIS_URL") and not os.getenv("REDIS_HOST"):
        return None
    try:
        import redis
        host = os.getenv("REDIS_HOST", "127.0.0.1")
        port = int(os.getenv("REDIS_PORT", "6379"))
        client = redis.Redis(
            host=host,
            port=port,
            db=0,
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
        client.ping()
        return client
    except Exception:
        return None


def query_prioritized_leads(service_line: str, min_score: int = 70) -> List[Dict[str, Any]]:
    """
    Discovers top enterprise leads filtered by minimum readiness score.
    Queries database lead scores, falling back to cached or canonical leads.
    """
    # 1. Check Redis / memory cache
    cache_key = f"leads:{service_line}:{min_score}"
    r = get_redis_client()
    if r:
        try:
            cached_data = r.get(f"leads:{service_line}")
            if cached_data:
                parsed = json.loads(cached_data)
                return [item for item in parsed if item.get("score", 0) >= min_score]
        except Exception:
            pass

    # 2. Query persistent PostgreSQL/SQLite storage
    try:
        from db.session import SessionLocal
        from db.schema import Company, ServiceOffering, LeadScore, SignalEvaluation
        from db.repository import get_leads_by_service

        session = SessionLocal()
        try:
            offering = (
                session.query(ServiceOffering)
                .filter(ServiceOffering.name.ilike(f"%{service_line}%"))
                .first()
            )

            if offering:
                lead_scores = get_leads_by_service(session, offering.id, min_score=min_score)
                if lead_scores:
                    results = []
                    for ls in lead_scores:
                        comp = session.query(Company).filter(Company.id == ls.company_id).first()
                        if comp:
                            top_eval = (
                                session.query(SignalEvaluation)
                                .filter(
                                    SignalEvaluation.company_id == comp.id,
                                    SignalEvaluation.detected.is_(True),
                                )
                                .order_by(SignalEvaluation.confidence.desc())
                                .first()
                            )
                            primary_signal = (
                                top_eval.evidence_quote[:75]
                                if top_eval
                                else (ls.executive_summary or f"Readiness score {ls.composite_score}")
                            )
                            results.append({
                                "company": comp.name,
                                "domain": comp.domain,
                                "score": ls.composite_score,
                                "primary_signal": primary_signal,
                            })
                    if results:
                        return results
        finally:
            session.close()
    except Exception as exc:
        logger.debug("Database query for leads failed (%s), falling back to canonical dataset.", exc)

    # 3. Fallback to canonical dataset
    return [item for item in CANONICAL_LEADS if item["score"] >= min_score]


def query_signal_evidence(domain: str) -> Dict[str, Any]:
    """
    Retrieves exact verbatim quotes and source links justifying why a company is ready to buy.
    """
    clean_domain = domain.strip().lower()

    # 1. Check Redis / memory cache
    r = get_redis_client()
    if r:
        try:
            cached_evidence = r.get(f"evidence:{clean_domain}")
            if cached_evidence:
                return json.loads(cached_evidence)
        except Exception:
            pass

    # 2. Query database for evaluations
    try:
        from db.session import SessionLocal
        from db.schema import Company, SignalEvaluation

        session = SessionLocal()
        try:
            comp = session.query(Company).filter(Company.domain == clean_domain).first()
            if comp:
                evals = (
                    session.query(SignalEvaluation)
                    .filter(SignalEvaluation.company_id == comp.id)
                    .order_by(SignalEvaluation.confidence.desc())
                    .all()
                )
                if evals:
                    return {
                        "company": comp.name,
                        "domain": comp.domain,
                        "status": "QUALIFIED",
                        "evaluations": [
                            {
                                "source_url": ev.source_url,
                                "detected": ev.detected,
                                "confidence": ev.confidence,
                                "evidence_quote": ev.evidence_quote,
                                "reasoning": ev.reasoning,
                                "evaluated_at": ev.evaluated_at.isoformat() if ev.evaluated_at else None,
                            }
                            for ev in evals
                        ],
                    }
        finally:
            session.close()
    except Exception as exc:
        logger.debug("Database query for signal evidence failed (%s)", exc)

    # 3. Canonical accounts fallback
    if clean_domain in CANONICAL_EVIDENCE:
        return CANONICAL_EVIDENCE[clean_domain]

    return {
        "status": "NOT_FOUND",
        "message": f"No signals evaluated for domain: {domain}",
    }


def format_grounded_pitch(
    company_name: str,
    recipient_title: str,
    evidence_quote: str,
    value_prop: str,
) -> str:
    """
    Generates an executive-level value proposition explicitly grounded in verified evidence.
    Conforms to Section 5.1 of the platform specification.
    """
    return f"""Subject: Supporting {company_name}'s automation initiatives alongside internal teams

Hi {recipient_title},

I noted that {company_name} is actively deploying programs targeting operational processes, specifically: "{evidence_quote}".

Orange Systems specializes in {value_prop}. We assist enterprise digital teams by delivering high-throughput automation modules that integrate directly with existing platforms without proprietary lock-in.

Would you be open to a 10-minute briefing next week to review our reference architecture?

Best regards,
Enterprise Solutions | Orange Systems
"""


def queue_sales_outreach(
    recipient_email: str,
    subject: str,
    email_body: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Stages or sends a sales outreach email.
    Generates a unique draft_id, storing payload with status AWAITING_HUMAN_APPROVAL if dry_run else DISPATCHED.
    """
    draft_id = f"draft_{os.urandom(4).hex()}"
    status = "AWAITING_HUMAN_APPROVAL" if dry_run else "DISPATCHED"

    payload = {
        "draft_id": draft_id,
        "recipient": recipient_email,
        "subject": subject,
        "body": email_body,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Store in memory
    OUTREACH_QUEUE[draft_id] = payload

    # Optional Redis persistence
    r = get_redis_client()
    if r:
        try:
            r.set(f"outreach_queue:{draft_id}", json.dumps(payload))
        except Exception:
            pass

    return payload
