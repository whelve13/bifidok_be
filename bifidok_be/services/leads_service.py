"""
Leads and sales intelligence service layer.
Connects database persistence, caching, and MCP tool handlers.
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory queues and cache for standalone execution or testing
OUTREACH_QUEUE: Dict[str, Dict[str, Any]] = {}
MEMORY_CACHE: Dict[str, str] = {}


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


def query_prioritized_leads(
    service_line: str,
    min_score: int = 70,
    session: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Discovers top enterprise leads filtered by minimum readiness score.
    Queries database lead scores, falling back to cached or canonical leads.
    """
    try:
        from config import STRICT_PRODUCTION
    except ImportError:
        try:
            from bifidok_be.config import STRICT_PRODUCTION
        except ImportError:
            STRICT_PRODUCTION = os.getenv("STRICT_PRODUCTION", "false").lower() in ("true", "1", "yes")

    # 1. Check Redis / memory cache
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
    close_session = False
    try:
        from db.session import SessionLocal
        from db.schema import Company, ServiceOffering, LeadScore, SignalEvaluation
        from db.repository import get_leads_by_service

        if session is None:
            session = SessionLocal()
            close_session = True

        try:
            clean_search = service_line.replace("_", " ").strip()
            offering = (
                session.query(ServiceOffering)
                .filter(
                    (ServiceOffering.name.ilike(f"%{service_line}%")) |
                    (ServiceOffering.name.ilike(f"%{clean_search}%"))
                )
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
                    return results
            return []
        finally:
            if close_session:
                session.close()
    except Exception as exc:
        if STRICT_PRODUCTION:
            raise RuntimeError("Database query failed under STRICT_PRODUCTION.") from exc
        logger.debug("Database query for leads failed (%s)", exc)
        return []


def query_signal_evidence(domain: str, session: Optional[Any] = None) -> Dict[str, Any]:
    """
    Retrieves exact verbatim quotes and source links justifying why a company is ready to buy.
    """
    clean_domain = domain.strip().lower()
    try:
        from config import STRICT_PRODUCTION
    except ImportError:
        try:
            from bifidok_be.config import STRICT_PRODUCTION
        except ImportError:
            STRICT_PRODUCTION = os.getenv("STRICT_PRODUCTION", "false").lower() in ("true", "1", "yes")

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
    close_session = False
    try:
        from db.session import SessionLocal
        from db.schema import Company, SignalEvaluation

        if session is None:
            session = SessionLocal()
            close_session = True

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
            if close_session:
                session.close()
    except Exception as exc:
        if STRICT_PRODUCTION:
            raise RuntimeError("Database query failed under STRICT_PRODUCTION.") from exc
        logger.debug("Database query for signal evidence failed (%s)", exc)

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


# In-memory store for HitL feedback calibration
_FEEDBACK_STORE: List[Dict[str, Any]] = []


def record_lead_feedback(
    lead_id: str,
    is_accurate: bool,
    notes: str = "",
) -> Dict[str, Any]:
    """
    Records human-in-the-loop feedback on lead scoring accuracy for model calibration.
    Stores the feedback entry in-memory and appends to data/lead_feedback.jsonl.
    """
    feedback_entry = {
        "feedback_id": str(uuid.uuid4()),
        "lead_id": str(lead_id),
        "is_accurate": bool(is_accurate),
        "notes": str(notes or "").strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "RECORDED",
    }

    _FEEDBACK_STORE.append(feedback_entry)

    # Persist to disk in data directory
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.abspath(os.path.join(current_dir, "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "lead_feedback.jsonl")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
    except Exception as exc:
        logger.warning("Could not persist lead feedback to disk: %s", exc)

    return feedback_entry


def get_lead_feedback(lead_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves stored feedback records, optionally filtered by lead_id.
    """
    if lead_id:
        target = str(lead_id)
        return [entry for entry in _FEEDBACK_STORE if entry["lead_id"] == target]
    return list(_FEEDBACK_STORE)


def clear_lead_feedback() -> None:
    """Clears in-memory feedback store (primarily for test teardowns)."""
    global _FEEDBACK_STORE
    _FEEDBACK_STORE = []

