from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CompanyProfile(BaseModel):
    name: str
    domain: str
    legal_name: Optional[str] = None
    country: Optional[str] = "DE"
    headcount: Optional[int] = None
    sector: Optional[str] = "Technology / Enterprise"
    ticker: Optional[str] = None
    description: Optional[str] = None
    is_solvent: bool = True

# =====================================================================
# AUTONOMOUS CUSTOMER PROSPECTING & INTENT ENGINE DATA MODELS
# =====================================================================

class CommercialWedge(BaseModel):
    name: str
    target_archetype: str
    description: str
    value_driver: str

class DecisionMakerPersona(BaseModel):
    title: str
    department: str
    mandate: str
    outreach_hook: str

class OfferingProfile(BaseModel):
    offering_id: str
    title: str
    category: Optional[str] = None
    description: str
    target_sectors: List[str] = Field(default_factory=list)
    target_wedges: List[CommercialWedge] = Field(default_factory=list)
    signal_keywords: List[str] = Field(default_factory=list)
    ats_roles: List[str] = Field(default_factory=list)
    tender_keywords: List[str] = Field(default_factory=list)
    min_headcount: int = 50
    requires_physical_presence: bool = False
    disqualifiers: List[str] = Field(default_factory=list)

class ScoreBreakdown(BaseModel):
    operational_fit: float = 0.0  # 0 to 35 pts
    timing_urgency: float = 0.0   # 0 to 30 pts
    purchasing_scale: float = 0.0 # 0 to 20 pts
    hiring_intent: float = 0.0    # 0 to 15 pts
    composite_score: float = 0.0  # 0 to 100.0

class ProspectEvidence(BaseModel):
    category: str
    title: str
    snippet: str
    source: str
    confidence: float = 0.8
    points_awarded: float = 0.0

class PerfectCustomerDossier(BaseModel):
    company: CompanyProfile
    offering_id: str
    offering_title: str
    propensity_score: float  # 0.0 to 100.0
    tier: str  # "Tier 1 - Prime Target", "Tier 2 - Strategic Opportunity", "Tier 3 - Nurture", "Disqualified"
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    score_breakdown: ScoreBreakdown
    primary_commercial_wedge: CommercialWedge
    operational_rationale: str
    evidence_citations: List[ProspectEvidence] = Field(default_factory=list)
    target_buying_committee: List[DecisionMakerPersona] = Field(default_factory=list)
    estimated_commercial_scope: str
    strategic_pitch_narrative: str

class ProspectingUniverseResult(BaseModel):
    offering: OfferingProfile
    total_evaluated: int
    tier1_count: int
    tier2_count: int
    ranked_customers: List[PerfectCustomerDossier]
