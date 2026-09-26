"""
Database package for Enterprise AI Sales Intelligence Platform.
"""
from .schema import (
    Base,
    Company,
    ServiceOffering,
    SignalRule,
    SignalEvaluation,
    LeadScore,
    MCPApiKey,
    SignalWeightType,
    GUID,
)
from .session import (
    engine,
    SessionLocal,
    get_db,
    init_db,
)
from .repository import (
    upsert_company,
    upsert_signal_evaluation,
    upsert_lead_score,
    get_leads_by_service,
    upsert_service_offering,
    upsert_signal_rule,
    create_mcp_api_key,
    get_mcp_api_key,
    to_uuid,
)

__all__ = [
    "Base",
    "Company",
    "ServiceOffering",
    "SignalRule",
    "SignalEvaluation",
    "LeadScore",
    "MCPApiKey",
    "SignalWeightType",
    "GUID",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "upsert_company",
    "upsert_signal_evaluation",
    "upsert_lead_score",
    "get_leads_by_service",
    "upsert_service_offering",
    "upsert_signal_rule",
    "create_mcp_api_key",
    "get_mcp_api_key",
    "to_uuid",
]
