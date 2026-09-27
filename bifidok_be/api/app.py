"""
FastAPI Application Core for Orange Systems Sales Intelligence Platform.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

try:
    from api.auth import router as auth_router
    from api.routes_config import router as config_router
    from api.routes_leads import router as leads_router
    from api.routes_outreach import router as outreach_router
    from api.routes_data import router as data_router
    from api.routes_prospect import router as prospect_router
    from db.schema import Company
    from db.seed import seed_database
    from db.session import SessionLocal
    from services.diagnostics import run_preflight_checks
except ImportError:
    from bifidok_be.api.auth import router as auth_router
    from bifidok_be.api.routes_config import router as config_router
    from bifidok_be.api.routes_leads import router as leads_router
    from bifidok_be.api.routes_outreach import router as outreach_router
    from bifidok_be.api.routes_data import router as data_router
    from bifidok_be.api.routes_prospect import router as prospect_router
    from bifidok_be.db.schema import Company
    from bifidok_be.db.seed import seed_database
    from bifidok_be.db.session import SessionLocal
    from bifidok_be.services.diagnostics import run_preflight_checks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler. Automatically seeds database with canonical
    benchmark entities on cold-start if database is empty.
    """
    try:
        session = SessionLocal()
        try:
            if session.query(Company).count() == 0:
                logger.info("Database empty on startup. Automatically seeding canonical datasets...")
                seed_database(session)
                logger.info("Canonical database seeding completed successfully.")
        finally:
            session.close()
    except Exception as exc:
        logger.warning("Startup database check/seed encountered exception: %s", exc)
    yield


# Instantiate FastAPI application conforming to Section 2
app = FastAPI(
    title="Orange Systems Sales Intelligence API",
    version="1.0.0",
    description="Enterprise AI Sales Intelligence Platform API Core",
    lifespan=lifespan,
)

# Add CORSMiddleware allowing all origins for dev/dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core platform routers
app.include_router(config_router)
app.include_router(leads_router)
app.include_router(outreach_router)
app.include_router(auth_router)
app.include_router(data_router)
app.include_router(prospect_router)

try:
    from mcp_server import mcp
    app.mount("/mcp", mcp.sse_app())
except Exception as exc:
    logger.warning("FastMCP SSE mount skipped: %s", exc)


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    """
    Health check endpoint returning system status and current timestamp.
    """
    return {
        "status": "UP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.api_route("/healthz", methods=["GET", "HEAD"])
def healthz(response: Response):
    """
    Comprehensive preflight health check probing Database, Redis, and Gemini.
    Returns 200 OK if Database is UP, or 503 SERVICE UNAVAILABLE if Database is DOWN.
    """
    diag = run_preflight_checks()
    db_comp = diag.get("components", {}).get("database", {})
    if db_comp.get("status") == "DOWN":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return diag


@app.api_route("/", methods=["GET", "HEAD"])
def root():
    """
    Root API discovery endpoint providing platform metadata and core endpoints.
    """
    return {
        "name": "Orange Systems Sales Intelligence Platform API",
        "version": "1.0.0",
        "status": "ONLINE",
        "docs_url": "/docs",
        "health_url": "/healthz",
        "endpoints": {
            "leads": "/api/leads",
            "compile_offering": "/api/offerings/compile",
            "outreach": "/api/outreach",
            "auth": "/api/auth/token",
        },
    }


@app.post("/api/admin/seed", tags=["admin"])
def seed_admin_database():
    """
    Administrative endpoint to seed the database with canonical companies,
    flagship commercial offerings, and signal rules. Safe and idempotent.
    """
    try:
        session = SessionLocal()
        try:
            counts = seed_database(session)
            return {"status": "SUCCESS", "seeded": counts}
        finally:
            session.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

