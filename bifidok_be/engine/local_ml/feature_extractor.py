"""
Feature Extractor for Local Machine Learning Models.
Transforms heterogeneous company data, financial metrics, and live public signals
into a normalized numerical vector for local regressors and classifiers.
"""
import math
import numpy as np
from typing import Any, Dict, List, Optional


FEATURE_NAMES = [
    "headcount_log",
    "operating_margin",
    "is_solvent",
    "ats_role_count",
    "has_active_tender",
    "has_official_ted_award",
    "has_news_signals",
    "security_resilience_grade",
    "missing_headers_count",
    "cisa_kev_active_count",
    "github_repo_count",
    "semantic_relevance",
    "requires_physical_mismatch",
    "sector_alignment",
    "tech_stack_breadth",
    "has_enterprise_erp",
    "has_leadership_catalyst",
    "hiring_velocity_score",
]


def extract_feature_vector(
    company: Dict[str, Any],
    signals: Dict[str, Any],
    offering: Optional[Any] = None,
) -> np.ndarray:
    """
    Extracts a 14-dimensional feature vector from company profile and live harvested signals.

    Args:
        company: Company metadata (headcount, operating_margin, is_solvent, sector, attributes).
        signals: Aggregated connector signals (ATS roles, tenders, news, security, KEV).
        offering: OfferingProfile object or dict (optional).

    Returns:
        1D numpy array of shape (14,)
    """
    # 1. Headcount (log-scaled)
    raw_headcount = company.get("headcount") or 500
    headcount_log = math.log10(max(1, raw_headcount))

    # 2. Operating margin
    op_margin = company.get("operating_margin")
    if op_margin is None:
        op_margin = 0.12  # European enterprise median baseline
    operating_margin = float(op_margin)

    # 3. Solvency flag (1 = Solvent, 0 = Insolvent)
    is_solvent = 1.0 if company.get("is_solvent", True) else 0.0

    # 4. ATS role count
    ats_roles = signals.get("matched_roles") or signals.get("ats_roles") or []
    ats_role_count = float(len(ats_roles))

    # 5. Active tender detected
    has_tender = 1.0 if signals.get("has_tenders") or signals.get("active_tender_rfp") else 0.0

    # 6. Official TED tender award
    has_official_ted = 1.0 if signals.get("has_official_award") else 0.0

    # 7. News signals detected
    news_items = signals.get("news_items") or signals.get("news") or []
    has_news = 1.0 if (signals.get("has_news") or len(news_items) > 0) else 0.0

    # 8. Security resilience grade (A=4, B=3, C=2, D=1, F=0)
    grade_map = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
    sec_grade = str(signals.get("security_grade", "B")).upper()
    security_resilience_grade = grade_map.get(sec_grade, 2.5)

    # 9. Missing security headers count
    missing_hdrs = signals.get("missing_headers") or []
    missing_headers_count = float(len(missing_hdrs))

    # 10. CISA KEV weaponized zero-days count
    cisa_count = float(signals.get("cisa_kev_count", 0))

    # 11. GitHub public repos count
    github_repos = float(signals.get("github_repo_count", 0))

    # 12. Semantic relevance confidence (from LLM extraction or keyword matching)
    semantic_rel = float(signals.get("semantic_relevance", 0.70))

    # 13. Physical footprint mismatch (1.0 if mismatch, 0.0 if aligned)
    req_physical = False
    if offering:
        req_physical = getattr(offering, "requires_physical_presence", False)
        if isinstance(offering, dict):
            req_physical = offering.get("requires_physical_presence", False)

    op_attrs = company.get("operational_attributes", {})
    is_remote_only = bool(op_attrs.get("remote_only", False)) or "remote" in str(company.get("description", "")).lower()
    requires_physical_mismatch = 1.0 if (req_physical and is_remote_only) else 0.0

    # 14. Sector alignment
    sector_align = 0.8  # baseline fit
    if offering:
        target_sectors = getattr(offering, "target_sectors", [])
        if isinstance(offering, dict):
            target_sectors = offering.get("target_sectors", [])
        comp_sector = str(company.get("sector", "")).lower()
        if any(ts.lower() in comp_sector or comp_sector in ts.lower() for ts in target_sectors):
            sector_align = 1.0

    # 15. Tech stack breadth (number of detected cloud/ERP/infrastructure systems)
    tech_breadth = float(signals.get("tech_stack_breadth") or len(signals.get("detected_tech", [])))
    if tech_breadth == 0 and signals.get("github_repo_count", 0) > 0:
        tech_breadth = min(5.0, float(signals.get("github_repo_count", 0)) / 10.0)

    # 16. Has enterprise ERP (SAP, Oracle, Salesforce)
    has_erp = 1.0 if (signals.get("has_enterprise_erp") or any(t in str(signals.get("detected_tech", [])) for t in ["SAP", "Salesforce", "Oracle"])) else 0.0

    # 17. Has leadership catalyst (new CIO/CISO/CTO appointment)
    has_leadership = 1.0 if (signals.get("has_leadership_change") or signals.get("has_leadership_catalyst")) else 0.0

    # 18. Hiring velocity score
    hiring_vel = float(signals.get("hiring_velocity_score") or min(1.0, ats_role_count * 0.25))

    return np.array([
        headcount_log,
        operating_margin,
        is_solvent,
        ats_role_count,
        has_tender,
        has_official_ted,
        has_news,
        security_resilience_grade,
        missing_headers_count,
        cisa_count,
        github_repos,
        semantic_rel,
        requires_physical_mismatch,
        sector_align,
        tech_breadth,
        has_erp,
        has_leadership,
        hiring_vel,
    ], dtype=np.float32)
