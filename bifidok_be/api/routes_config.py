"""
API configuration routes for custom commercial offering compilation.
Exposes REST endpoints for web/React frontend configurators.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from engine.offering_catalog import decompose_custom_offering

router = APIRouter(prefix="/api/offerings", tags=["offerings"])


class CompileOfferingRequest(BaseModel):
    user_input: Optional[str] = Field(None, description="Commercial product or service description to sell")
    offering_text: Optional[str] = Field(None, description="Alternative key for offering text")
    query: Optional[str] = Field(None, description="Alternative query key")

    def get_text(self) -> str:
        return (self.user_input or self.offering_text or self.query or "").strip()


class CompileOfferingResponse(BaseModel):
    offering_name: str
    description: str
    signal_rules: List[Dict[str, Any]]
    connector_queries: Dict[str, List[str]]
    disqualifiers: List[str]


@router.post("/compile", response_model=CompileOfferingResponse)
def compile_offering(request: CompileOfferingRequest):
    """
    Compiles an arbitrary user commercial mandate into an editable JSON draft
    with structured signal rules, weights, connector search queries, and disqualifiers.
    """
    text = request.get_text()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Offering description ('user_input' or 'offering_text') is required.",
        )

    compiled = decompose_custom_offering(text)
    return compiled


# Optional standalone FastAPI app for testing and hosting
app = FastAPI(
    title="Orange Systems Sales Intelligence Configuration API",
    version="1.0.0",
)
app.include_router(router)
