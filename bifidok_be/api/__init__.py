"""
API package for Orange Systems sales intelligence endpoints.
"""
from .app import app
from .auth import generate_api_key, get_authenticated_tenant
from .routes_config import router as config_router
from .routes_leads import router as leads_router
from .routes_outreach import router as outreach_router

__all__ = [
    "app",
    "generate_api_key",
    "get_authenticated_tenant",
    "config_router",
    "leads_router",
    "outreach_router",
]
