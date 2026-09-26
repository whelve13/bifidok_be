"""
Preflight system health and readiness diagnostics for Orange Systems platform.
Probes Database, Redis, and Gemini API connectivity and configurations.
"""
import logging
import os
import sys
from typing import Any, Dict

# Ensure bifidok_be root package is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def run_preflight_checks() -> Dict[str, Any]:
    """
    Executes deep health checks across Database, Redis, and Gemini LLM.

    Returns:
        Dict[str, Any] containing component statuses, details, and overall status:
        'HEALTHY' | 'DEGRADED' | 'UNHEALTHY'.
    """
    try:
        from config import DATABASE_URL, GEMINI_API_KEY, REDIS_URL
    except ImportError:
        DATABASE_URL = os.getenv("DATABASE_URL", "")
        REDIS_URL = os.getenv("REDIS_URL", "")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    diagnostics = {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
    }

    # -------------------------------------------------------------------------
    # 1. Database Diagnostic (PostgreSQL / SQLite fallback)
    # -------------------------------------------------------------------------
    db_info = {
        "status": "DOWN",
        "dialect": "unknown",
        "company_count": 0,
        "tables_present": [],
        "missing_tables": [],
        "error": None,
    }

    try:
        import sqlalchemy as sa
        from db.schema import (
            Company,
            LeadScore,
            MCPApiKey,
            ServiceOffering,
            SignalEvaluation,
            SignalRule,
        )
        from db.session import SessionLocal, engine

        with engine.connect() as conn:
            inspector = sa.inspect(conn)
            tables = set(inspector.get_table_names())
            db_info["tables_present"] = sorted(list(tables))
            db_info["dialect"] = engine.dialect.name

            expected_tables = {
                "companies",
                "service_offerings",
                "signal_rules",
                "signal_evaluations",
                "lead_scores",
                "mcp_api_keys",
            }
            missing = expected_tables - tables
            db_info["missing_tables"] = sorted(list(missing))

        session = SessionLocal()
        try:
            db_info["company_count"] = session.query(Company).count()
            if not missing:
                db_info["status"] = "UP"
            else:
                db_info["status"] = "DEGRADED"
                db_info["error"] = f"Missing schema tables: {db_info['missing_tables']}"
        finally:
            session.close()

    except Exception as exc:
        logger.error("Preflight DB check failed: %s", exc)
        db_info["status"] = "DOWN"
        db_info["error"] = str(exc)

    diagnostics["components"]["database"] = db_info

    # -------------------------------------------------------------------------
    # 2. Redis Diagnostic
    # -------------------------------------------------------------------------
    redis_info = {
        "status": "NOT_CONFIGURED",
        "ping": False,
        "url": REDIS_URL or None,
        "error": None,
    }

    redis_host = os.getenv("REDIS_HOST")
    redis_url = os.getenv("REDIS_URL")

    if redis_host or redis_url:
        try:
            from services.leads_service import get_redis_client
            client = get_redis_client()
            if client and client.ping():
                redis_info["status"] = "UP"
                redis_info["ping"] = True
            else:
                redis_info["status"] = "DOWN"
                redis_info["error"] = "Redis ping returned False or client unavailable."
        except Exception as exc:
            redis_info["status"] = "DOWN"
            redis_info["error"] = str(exc)
    else:
        redis_info["status"] = "NOT_CONFIGURED"

    diagnostics["components"]["redis"] = redis_info

    # -------------------------------------------------------------------------
    # 3. Gemini API Diagnostic
    # -------------------------------------------------------------------------
    gemini_key = GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY", "")
    gemini_info = {
        "status": "NOT_CONFIGURED",
        "initialized": False,
        "error": None,
    }

    if gemini_key:
        clean_key = gemini_key.strip()
        if len(clean_key) >= 16:
            try:
                import google.generativeai as genai
                genai.configure(api_key=clean_key)
                gemini_info["status"] = "CONFIGURED"
                gemini_info["initialized"] = True
            except Exception as exc:
                gemini_info["status"] = "ERROR"
                gemini_info["error"] = str(exc)
        else:
            gemini_info["status"] = "INVALID"
            gemini_info["error"] = "GEMINI_API_KEY does not appear to be a valid API key (too short)."
    else:
        gemini_info["status"] = "NOT_CONFIGURED"

    diagnostics["components"]["gemini"] = gemini_info

    # -------------------------------------------------------------------------
    # Overall Status Synthesis
    # -------------------------------------------------------------------------
    if db_info["status"] == "DOWN":
        diagnostics["status"] = "UNHEALTHY"
    elif db_info["status"] == "DEGRADED" or redis_info["status"] in ("DOWN", "NOT_CONFIGURED") or gemini_info["status"] in ("NOT_CONFIGURED", "INVALID", "ERROR"):
        diagnostics["status"] = "DEGRADED"
    else:
        diagnostics["status"] = "HEALTHY"

    return diagnostics
