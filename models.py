from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TargetICP(BaseModel):
    regions: List[str] = Field(default_factory=list)
    min_headcount: int = 50
    sectors: List[str] = Field(default_factory=list)

class AlignmentCriterion(BaseModel):
    signal_id: str
    category: str  # financial, ats_hiring, news, security_osint, developer_sentiment, tenders
    indicator: Optional[str] = None
    keywords: Optional[List[str]] = None
    weight: float = 0.33
    likelihood_ratio: float = 4.0
    description: str = ""

class SolutionSpec(BaseModel):
    solution_id: str
    solution_name: str
    target_icp: TargetICP
    alignment_criteria: List[AlignmentCriterion]
    disqualifiers: List[str] = Field(default_factory=list)
    value_proposition_template: str

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

class SignalEvidence(BaseModel):
    signal_id: str
    category: str
    strength: float = 0.0  # 0.0 to 1.0
    log_odds_delta: float = 0.0
    score_points_awarded: float = 0.0
    evidence_text: str = ""
    source: str = ""
    confidence: float = 0.0

class SolutionAlignment(BaseModel):
    solution_id: str
    solution_name: str
    alignment_score: float  # 0.0 to 100.0
    tier: str  # "Tier 1 - Hot", "Tier 2 - Warm", "Cold / Low Fit", "Disqualified"
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    evidence_trail: List[SignalEvidence] = Field(default_factory=list)
    tailored_pitch: str = ""

class CompanyAnalysisResult(BaseModel):
    company: CompanyProfile
    ranked_solutions: List[SolutionAlignment]
    best_solution: Optional[SolutionAlignment] = None
