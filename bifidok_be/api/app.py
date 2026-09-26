"""
FastAPI Application Core for Orange Systems Sales Intelligence Platform.
Conforms to Section 2 and Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from api.auth import router as auth_router
    from api.routes_config import router as config_router
    from api.routes_leads import router as leads_router
    from api.routes_outreach import router as outreach_router
except ImportError:
    from bifidok_be.api.auth import router as auth_router
    from bifidok_be.api.routes_config import router as config_router
    from bifidok_be.api.routes_leads import router as leads_router
    from bifidok_be.api.routes_outreach import router as outreach_router

# Instantiate FastAPI application conforming to Section 2
app = FastAPI(
    title="Orange Systems Sales Intelligence API",
    version="1.0.0",
    description="Enterprise AI Sales Intelligence Platform API Core",
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


@app.get("/health")
def health():
    """
    Health check endpoint returning system status and current timestamp.
    """
    return {
        "status": "UP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
