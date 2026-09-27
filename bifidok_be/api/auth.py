"""
Authentication and API key management for Orange Systems Sales Intelligence Platform.
Conforms to Section 2 and Section 5.2 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
"""
import hashlib
import os
import secrets
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

try:
    from db.repository import create_mcp_api_key, get_mcp_api_key
    from db.schema import MCPApiKey
    from db.session import get_db
except ImportError:
    from bifidok_be.db.repository import create_mcp_api_key, get_mcp_api_key
    from bifidok_be.db.schema import MCPApiKey
    from bifidok_be.db.session import get_db

security = HTTPBearer(auto_error=False)


def generate_api_key(
    tenant_name: str,
    session: Session,
    key_prefix: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Creates an API key with prefix 'orange_sk_' (or 'pip_sk_'), computes SHA-256 hash,
    stores in mcp_api_keys table, and returns (raw_key, key_hash).
    """
    clean_tenant = str(tenant_name or "").strip()
    if not clean_tenant:
        raise ValueError("tenant_name must be a non-empty string.")

    prefix = key_prefix or ("pip_sk" if "pip" in clean_tenant.lower() else "orange_sk")
    if prefix.endswith("_"):
        prefix = prefix[:-1]
    raw_key = f"{prefix}_{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    create_mcp_api_key(
        session=session,
        data={
            "tenant_name": clean_tenant,
            "key_hash": key_hash,
            "is_active": True,
        },
    )

    return raw_key, key_hash


def get_authenticated_tenant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    session: Session = Depends(get_db),
) -> MCPApiKey:
    """
    FastAPI Security dependency extracting Bearer token from Authorization header,
    hashing it, and verifying active tenant in mcp_api_keys.
    If STRICT_PRODUCTION=False and token is orange_dev_token, allow development bypass.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
    elif request and "authorization" in request.headers:
        raw_header = request.headers["authorization"].strip()
        if raw_header.lower().startswith("bearer "):
            token = raw_header[7:].strip()
        else:
            token = raw_header

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    strict_production = os.getenv("STRICT_PRODUCTION", "False").lower() in ("true", "1", "yes")

    # Development bypass for local testing and debugging
    if not strict_production and token in ("orange_dev_token", "pip_dev_token", "pipstream_dev_token"):
        return MCPApiKey(
            id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            tenant_name="dev_tenant",
            key_hash=hashlib.sha256(b"orange_dev_token").hexdigest(),
            is_active=True,
        )

    # Compute SHA-256 hash of provided Bearer token and check DB
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    tenant = get_mcp_api_key(session, token_hash)

    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tenant


# Optional REST endpoints for API key provisioning and token verification
router = APIRouter(prefix="/api/auth", tags=["auth"])


class ApiKeyProvisionRequest(BaseModel):
    tenant_name: str = Field(..., description="Organization or tenant name")
    key_prefix: Optional[str] = Field(None, description="Optional key prefix (e.g. 'pip_sk' or 'orange_sk')")


class ApiKeyProvisionResponse(BaseModel):
    tenant_name: str
    raw_key: str
    key_hash: str


@router.post("/keys", response_model=ApiKeyProvisionResponse)
def provision_api_key(
    request: ApiKeyProvisionRequest,
    session: Session = Depends(get_db),
):
    """
    Provisions a new API key for external agent access (Section 2 & Section 5.2).
    """
    raw_key, key_hash = generate_api_key(request.tenant_name, session, key_prefix=request.key_prefix)
    return ApiKeyProvisionResponse(
        tenant_name=request.tenant_name,
        raw_key=raw_key,
        key_hash=key_hash,
    )


@router.get("/keys")
def list_api_keys(session: Session = Depends(get_db)):
    """
    Lists provisioned active API keys (masked for security).
    """
    try:
        keys = session.query(MCPApiKey).filter(MCPApiKey.is_active.is_(True)).limit(10).all()
        return [
            {
                "tenant_name": k.tenant_name,
                "key_prefix": "pip_sk_...",
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if hasattr(k, "created_at") and k.created_at else None,
            }
            for k in keys
        ]
    except Exception:
        return []


@router.get("/verify")
def verify_token(tenant: MCPApiKey = Depends(get_authenticated_tenant)):
    """
    Verifies that the provided Bearer token is valid and active.
    """
    return {
        "status": "AUTHENTICATED",
        "tenant_name": tenant.tenant_name,
        "is_active": tenant.is_active,
    }
