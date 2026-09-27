"""
PipStream Commercial Verifier & Anti-False-Positive Underwriting Engine.
Ensures candidate accounts have genuine operational alignment with the commercial offering,
preventing false-positive domain mismatches (e.g., pitching enterprise AI workflow automation
to physical food farms or artisanal bakeries).
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CommercialVerificationResult(BaseModel):
    """Structured verdict from the commercial underwriting and anti-false-positive check."""
    is_approved: bool = Field(True, description="True if company has genuine commercial fit")
    relevance_score: float = Field(0.85, ge=0.0, le=1.0, description="Semantic fit confidence score")
    domain_mismatch: bool = Field(False, description="True if target company is in an incompatible vertical")
    executive_angle: str = Field("", description="High-conviction value proposition angle for outreach")
    rejection_reason: Optional[str] = Field(None, description="Detailed explanation if rejected")
    confidence: float = Field(0.88, ge=0.0, le=1.0, description="Verification confidence")


def _deterministic_semantic_underwrite(
    offering_title: str,
    offering_desc: str,
    company_name: str,
    company_sector: str,
    company_description: str,
    evidence_snippets: List[str],
) -> CommercialVerificationResult:
    """
    Deterministic rule-based underwriting logic for environments without an active LLM key.
    Detects obvious domain mismatches and crafts authentic executive angles.
    """
    offering_text = f"{offering_title} {offering_desc}".lower()
    company_text = f"{company_name} {company_sector} {company_description} {' '.join(evidence_snippets)}".lower()

    # 1. Physical vs Pure Digital Disconnect
    is_physical_logistics_offering = any(
        w in offering_text for w in ["bike", "cargo", "fleet", "courier", "last-mile", "vehicle", "delivery hub"]
    )
    is_pure_software_company = any(
        w in company_text for w in [
            "software", "saas", "fintech", "financial", "trading", "hedge fund",
            "banking", "insurance", "consulting", "legal", "law firm", "capital management"
        ]
    ) and not any(
        w in company_text for w in ["logistics", "delivery", "transport", "fleet", "warehouse", "retail", "supermarket"]
    )

    if is_physical_logistics_offering and is_pure_software_company:
        return CommercialVerificationResult(
            is_approved=False,
            relevance_score=0.15,
            domain_mismatch=True,
            executive_angle="",
            rejection_reason=f"{company_name} is a knowledge-work / financial entity with no physical fleet or last-mile urban logistics footprint.",
            confidence=0.92,
        )

    # 2. Advanced Tech / Cyber / AI vs Pure Traditional Agriculture / Dairy / Local Food
    is_digital_ai_cyber_offering = any(
        w in offering_text for w in ["agentic", "automation", "soc", "cyber", "nis2", "cloud", "kubernetes", "devops", "software", "api", "ai"]
    )
    is_non_tech_traditional_commodity = any(
        w in company_sector.lower() for w in ["dairy", "poultry", "farming", "crop", "bakery", "artisanal"]
    ) or (
        any(w in company_text for w in ["milk production", "livestock", "flour milling", "artisanal bread"])
        and not any(w in company_text for w in ["digital", "enterprise", "supply chain software", "it infrastructure", "automation system"])
    )

    if is_digital_ai_cyber_offering and is_non_tech_traditional_commodity:
        return CommercialVerificationResult(
            is_approved=False,
            relevance_score=0.20,
            domain_mismatch=True,
            executive_angle="",
            rejection_reason=f"{company_name} operates in primary commodity / physical food production without sufficient knowledge-work or digital enterprise scale for {offering_title}.",
            confidence=0.90,
        )

    # 3. High Positive Synergies
    evidence_quote = evidence_snippets[0] if evidence_snippets else ""
    snippet_hint = f' noting recent reports that "{evidence_quote[:80]}..."' if evidence_quote else ""

    if "cyber" in offering_text or "soc" in offering_text or "security" in offering_text:
        executive_angle = (
            f"Leverage {offering_title} to fortify {company_name}'s {company_sector} compliance posture "
            f"and accelerate SOC response times under European regulatory frameworks (NIS2/DORA){snippet_hint}."
        )
    elif "cloud" in offering_text or "modernization" in offering_text or "devops" in offering_text:
        executive_angle = (
            f"Support {company_name}'s engineering leadership in containerizing legacy workloads "
            f"and optimizing cloud cost predictability across their {company_sector} digital platforms{snippet_hint}."
        )
    elif "bike" in offering_text or "fleet" in offering_text:
        executive_angle = (
            f"Equip {company_name}'s urban logistics operations with zero-emission cargo fleets, "
            f"reducing last-mile per-stop delivery costs across high-density European metropolitan zones."
        )
    else:
        executive_angle = (
            f"Deploy {offering_title} into {company_name}'s operational core to eliminate repetitive manual workflows "
            f"and deliver measurable efficiency gains for their {company_sector} teams{snippet_hint}."
        )

    return CommercialVerificationResult(
        is_approved=True,
        relevance_score=0.88,
        domain_mismatch=False,
        executive_angle=executive_angle,
        rejection_reason=None,
        confidence=0.86,
    )


def verify_commercial_fit(
    offering_title: str,
    offering_description: str,
    company_name: str,
    company_sector: str,
    company_description: str,
    evidence_snippets: Optional[List[str]] = None,
    operational_attributes: Optional[Dict[str, Any]] = None,
) -> CommercialVerificationResult:
    """
    Evaluates whether a prospective account represents a legitimate, high-conviction target
    for a given commercial offering using Gemini LLM reasoning (with robust deterministic fallback).
    """
    snippets = evidence_snippets or []
    sector = company_sector or "Enterprise & Industrial Operations"
    desc = company_description or "Commercial enterprise."

    # Check for Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _deterministic_semantic_underwrite(
            offering_title=offering_title,
            offering_desc=offering_description,
            company_name=company_name,
            company_sector=sector,
            company_description=desc,
            evidence_snippets=snippets,
        )

    # LLM-guided commercial sanity check
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        evidence_str = "\n".join(f"- {s}" for s in snippets[:3]) if snippets else "- No specific news headlines captured."

        prompt = f"""You are the Chief Commercial Underwriting Officer for PipStream, an enterprise B2B sales intelligence platform.
Your job is to prevent embarrassing false-positive pitches by verifying domain compatibility.

COMMERCIAL OFFERING:
Title: {offering_title}
Description: {offering_description}

TARGET CANDIDATE:
Company Name: {company_name}
Industry / Sector: {sector}
Business Description: {desc}
Operational Attributes: {json.dumps(operational_attributes or {})}
Captured Market Signals:
{evidence_str}

TASK:
1. Conduct a rigorous sanity check: Does this company have a real business case for purchasing this offering?
2. Detect domain mismatches (e.g. pitching agentic AI / SOC cybersecurity to an agricultural farm or artisanal bakery; or pitching cargo bikes to a pure digital SaaS company).
3. If approved, construct a high-conviction 1-2 sentence executive angle tailored to their leadership.
4. If rejected, clearly state the domain mismatch reason.

Output strictly valid JSON with this schema:
{{
  "is_approved": true,
  "relevance_score": 0.92,
  "domain_mismatch": false,
  "executive_angle": "High-conviction value angle...",
  "rejection_reason": null,
  "confidence": 0.95
}}
"""
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Clean markdown codeblocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if match:
            raw_text = match.group(1)

        data = json.loads(raw_text)
        return CommercialVerificationResult(
            is_approved=bool(data.get("is_approved", True)),
            relevance_score=float(data.get("relevance_score", 0.85)),
            domain_mismatch=bool(data.get("domain_mismatch", False)),
            executive_angle=str(data.get("executive_angle", "")).strip(),
            rejection_reason=data.get("rejection_reason"),
            confidence=float(data.get("confidence", 0.90)),
        )
    except Exception as exc:
        logger.debug("Gemini commercial verification failed, applying deterministic underwrite: %s", exc)
        return _deterministic_semantic_underwrite(
            offering_title=offering_title,
            offering_desc=offering_description,
            company_name=company_name,
            company_sector=sector,
            company_description=desc,
            evidence_snippets=snippets,
        )
