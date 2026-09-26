"""
Connectors package for external data harvesting, registries, news feeds, and signals.
"""
from .gdelt import fetch_gdelt_signals
from .tenders import fetch_public_procurement_tenders, is_official_contract_award
from .financials import fetch_financial_signals
from .news import fetch_company_news, evaluate_news_relevance
from .security import analyze_security_posture
from .ats import fetch_ats_hiring_signals
from .registries import verify_official_registry
from .developer import fetch_developer_signals
from .vulnerabilities import evaluate_vulnerability_exposure
from .firmographics import resolve_company_entity

__all__ = [
    "fetch_gdelt_signals",
    "fetch_public_procurement_tenders",
    "is_official_contract_award",
    "fetch_financial_signals",
    "fetch_company_news",
    "evaluate_news_relevance",
    "analyze_security_posture",
    "fetch_ats_hiring_signals",
    "verify_official_registry",
    "fetch_developer_signals",
    "evaluate_vulnerability_exposure",
    "resolve_company_entity",
]
