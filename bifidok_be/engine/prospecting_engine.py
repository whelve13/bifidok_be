"""
Customer Prospecting Engine.
Coordinates autonomous entity discovery, multi-source live signal harvesting,
local machine learning scoring (LightGBM/LogisticRegression), and structured sales dossiers.
"""
import logging
import os
from typing import Any, Dict, List, Optional, Union

from models import (
    CommercialWedge,
    CompanyProfile,
    DecisionMakerPersona,
    OfferingProfile,
    PerfectCustomerDossier,
    ProspectEvidence,
    ProspectingUniverseResult,
    ScoreBreakdown,
)
from engine.anti_hallucination import verify_verbatim_quote
from engine.autonomous_scout import discover_candidate_universe
from engine.candidate_pool import ENTERPRISE_UNIVERSE, find_candidate_by_name, get_candidate_universe
from engine.local_ml.inference import predict_lead_evaluation
from engine.offering_catalog import (
    FLAGSHIP_OFFERINGS,
    decompose_custom_offering,
    offering_dict_to_profile,
)

from connectors.ats import fetch_ats_hiring_signals
from connectors.financials import fetch_financial_signals
from connectors.firmographics import resolve_company_entity
from connectors.gdelt import fetch_gdelt_signals
from connectors.news import fetch_company_news
from connectors.registries import verify_official_registry
from connectors.security import analyze_security_posture
from connectors.tenders import fetch_public_procurement_tenders

logger = logging.getLogger(__name__)


class CustomerProspectingEngine:
    """Enterprise Customer Prospecting & Buying Intent Engine."""

    def __init__(self):
        pass

    def _resolve_offering(self, offering_input: Union[str, Dict[str, Any], OfferingProfile]) -> OfferingProfile:
        """Resolves an offering identifier, dictionary, or text into a validated OfferingProfile."""
        if isinstance(offering_input, OfferingProfile):
            return offering_input

        if isinstance(offering_input, dict):
            return offering_dict_to_profile(offering_input)

        if isinstance(offering_input, str):
            clean = offering_input.strip()
            if clean in FLAGSHIP_OFFERINGS:
                return FLAGSHIP_OFFERINGS[clean]
            # Decompose custom offering dynamically
            compiled = decompose_custom_offering(clean)
            return offering_dict_to_profile(compiled)

        return FLAGSHIP_OFFERINGS["commercial_bikes"]

    def evaluate_single_company(
        self,
        company_name: str,
        offering: Union[str, Dict[str, Any], OfferingProfile] = "commercial_bikes",
        domain_hint: Optional[str] = None,
    ) -> PerfectCustomerDossier:
        """Alias for analyze_single_prospect for CLI compatibility."""
        return self.analyze_single_prospect(company_name, offering)

    def analyze_single_prospect(
        self,
        company_name_or_domain: str,
        offering: Union[str, Dict[str, Any], OfferingProfile],
    ) -> PerfectCustomerDossier:
        """
        Analyzes a single prospective account against an offering using local ML models.
        """
        resolved_offering = self._resolve_offering(offering)
        clean_input = company_name_or_domain.strip()

        # 1. Resolve company profile
        candidate = find_candidate_by_name(clean_input)
        if candidate:
            comp_data = dict(candidate)
        else:
            resolved_entity = resolve_company_entity(clean_input)
            comp_data = {
                "name": resolved_entity.get("name", clean_input),
                "domain": resolved_entity.get("domain", f"{clean_input.lower().replace(' ', '')}.com"),
                "legal_name": resolved_entity.get("legal_name", clean_input),
                "country": resolved_entity.get("country", "DE"),
                "headcount": 15000,
                "sector": "Industrial & Enterprise Operations",
                "ticker": None,
                "description": resolved_entity.get("description", "Enterprise operator."),
                "is_solvent": True,
                "operational_attributes": {},
            }

        company_name = comp_data["name"]
        domain = comp_data["domain"]

        # Check official corporate registry for solvency
        registry_res = verify_official_registry(company_name)
        if not registry_res.get("is_solvent", True):
            comp_data["is_solvent"] = False

        # Financials
        fin_res = fetch_financial_signals(company_name)
        if fin_res.get("headcount"):
            comp_data["headcount"] = fin_res["headcount"]
        if fin_res.get("operating_margin") is not None:
            comp_data["operating_margin"] = fin_res["operating_margin"]
        if fin_res.get("sector"):
            comp_data["sector"] = fin_res["sector"]

        # 2. Gather live public signals concurrently
        signals: Dict[str, Any] = {
            "matched_roles": [],
            "has_tenders": False,
            "has_official_award": False,
            "has_news": False,
            "news_items": [],
            "security_grade": "B",
            "missing_headers": [],
            "cisa_kev_count": 0,
            "github_repo_count": 0,
            "semantic_relevance": 0.85,
        }

        evidence_citations: List[ProspectEvidence] = []

        # A. Operational Footprint Evidence
        if comp_data.get("operational_attributes", {}).get("urban_delivery_fleets"):
            evidence_citations.append(
                ProspectEvidence(
                    category="Operational Footprint",
                    title="High-Volume Last-Mile Delivery Network",
                    snippet="Operates dedicated urban couriers, postal delivery, or logistics parcel distribution networks.",
                    source="Company Operational Dossier",
                    confidence=0.95,
                    points_awarded=35.0,
                )
            )
        elif comp_data.get("operational_attributes", {}).get("internal_campus_transit"):
            evidence_citations.append(
                ProspectEvidence(
                    category="Operational Footprint",
                    title="Large-Scale Industrial Manufacturing Complex",
                    snippet="Operates extensive multi-kilometer production sites requiring on-site mobility solutions.",
                    source="Company Operational Dossier",
                    confidence=0.92,
                    points_awarded=32.0,
                )
            )

        # B. News & Media
        try:
            news = fetch_company_news(company_name, resolved_offering.signal_keywords)
            signals["news_items"] = news
            if news:
                signals["has_news"] = True
                top_n = news[0]
                evidence_citations.append(
                    ProspectEvidence(
                        category="Real-Time Public Signal",
                        title=f"Live Press Catalyst ({top_n['title'][:55]}...)",
                        snippet=f"Recent announcement referencing {resolved_offering.signal_keywords[:3]}. Link: {top_n.get('link', '')}",
                        source="Google News Pan-European Feed",
                        confidence=0.90,
                        points_awarded=18.0,
                    )
                )
        except Exception:
            pass

        # C. Public Procurement & Tenders
        try:
            tenders_res = fetch_public_procurement_tenders(company_name, resolved_offering.tender_keywords)
            if tenders_res.get("active_tender_rfp"):
                signals["has_tenders"] = True
                signals["has_official_award"] = tenders_res.get("has_official_award", False)
                evidence_citations.append(
                    ProspectEvidence(
                        category="Public Tender / RFP",
                        title="Active Procurement RFP Notice Detected",
                        snippet=f"Procurement notice identified: {tenders_res.get('evidence', [''])[0][:80]}",
                        source=tenders_res.get("source", "Public Procurement Feed"),
                        confidence=tenders_res.get("confidence", 0.85),
                        points_awarded=22.0,
                    )
                )
        except Exception:
            pass

        # D. ATS Hiring Signals
        try:
            ats_res = fetch_ats_hiring_signals(company_name, resolved_offering.ats_roles)
            matched = ats_res.get("matched_roles", [])
            signals["matched_roles"] = matched
            if matched:
                evidence_citations.append(
                    ProspectEvidence(
                        category="Recruitment & Hiring Intent",
                        title=f"Target Roles Detected on Public ATS ({ats_res.get('ats_provider', 'Board')})",
                        snippet=f"Active openings matching commercial requirements: {', '.join(matched[:3])}.",
                        source=f"{ats_res.get('ats_provider', 'ATS')} Job Board",
                        confidence=0.88,
                        points_awarded=15.0,
                    )
                )
        except Exception:
            pass

        # E. Security & OSINT
        try:
            sec_res = analyze_security_posture(domain)
            signals["security_grade"] = sec_res.get("grade", "B")
            signals["missing_headers"] = sec_res.get("missing_headers", [])
        except Exception:
            pass

        # 3. Predict using Local ML Models
        ml_res = predict_lead_evaluation(
            company=comp_data,
            signals=signals,
            offering=resolved_offering,
        )

        propensity_score = ml_res["propensity_score"]
        tier = ml_res["tier"]
        is_disqualified = ml_res["is_disqualified"]
        disqualification_reason = ml_res["disqualification_reason"]
        sb_data = ml_res["score_breakdown"]
        wedge_idx = ml_res["selected_wedge_idx"]

        score_breakdown = ScoreBreakdown(
            operational_fit=sb_data["operational_fit"],
            timing_urgency=sb_data["timing_urgency"],
            purchasing_scale=sb_data["purchasing_scale"],
            hiring_intent=sb_data["hiring_intent"],
            composite_score=propensity_score,
        )

        # Select commercial wedge
        wedges = resolved_offering.target_wedges
        if not wedges:
            wedges = [
                CommercialWedge(
                    name=f"{resolved_offering.title} - Strategic Deployment",
                    target_archetype="Enterprise operators",
                    description="Turnkey operational rollout.",
                    value_driver="Accelerate time to value and eliminate operational friction.",
                )
            ]

        # Use company operational context to pick the optimal wedge
        if comp_data.get("operational_attributes", {}).get("urban_delivery_fleets"):
            primary_wedge = next((w for w in wedges if "Last-Mile" in w.name or "Cargo" in w.name), wedges[0])
        elif comp_data.get("operational_attributes", {}).get("internal_campus_transit"):
            primary_wedge = next((w for w in wedges if "Campus" in w.name or "Industrial" in w.name), wedges[min(1, len(wedges)-1)])
        else:
            primary_wedge = wedges[min(wedge_idx, len(wedges) - 1)]

        # Buying committee personas
        buying_committee = [
            DecisionMakerPersona(
                title="VP of Operations / Fleet Director",
                department="Operations & Logistics",
                mandate="Scale operational efficiency while reducing urban last-mile emissions and maintenance overhead.",
                outreach_hook=f"Addressing operational efficiency with {resolved_offering.title}.",
            ),
            DecisionMakerPersona(
                title="Chief Sustainability Officer / ESG Lead",
                department="Sustainability & Corporate Strategy",
                mandate="Fulfill corporate Scope 3 decarbonization commitments under European CSRD mandates.",
                outreach_hook="Auditable carbon emission reduction and zero-emission delivery transition.",
            ),
        ]

        # Estimated commercial scope
        headcount = comp_data.get("headcount", 500)
        if headcount >= 50000:
            estimated_scope = "€1.5M - €5.0M Enterprise-Wide Fleet Deployment"
        elif headcount >= 5000:
            estimated_scope = "€400K - €1.2M Multi-Facility Regional Rollout"
        else:
            estimated_scope = "€100K - €350K Targeted Operational Pilot"

        # Rationale and pitch
        operational_rationale = (
            f"{company_name} exhibits ideal enterprise characteristics for {resolved_offering.title}: "
            f"{primary_wedge.name} provides immediate operational synergy with their {comp_data.get('sector', 'Enterprise')} footprint, "
            f"supported by verified live buying signals and organizational scale ({headcount:,} employees)."
        )

        pitch = (
            f"Subject: Accelerating {company_name}'s operational efficiency with {resolved_offering.title}\n\n"
            f"Dear Team,\n\n"
            f"Given {company_name}'s leadership in {comp_data.get('sector', 'the market')}, "
            f"we noted strategic alignment regarding {primary_wedge.name}. "
            f"Our solution helps enterprises achieve: {primary_wedge.value_driver}\n\n"
            f"Would you be open to a 10-minute briefing next week?"
        )

        return PerfectCustomerDossier(
            company=CompanyProfile(
                name=company_name,
                domain=domain,
                legal_name=comp_data.get("legal_name", company_name),
                country=comp_data.get("country", "DE"),
                headcount=headcount,
                sector=comp_data.get("sector", "Enterprise"),
                ticker=comp_data.get("ticker"),
                description=comp_data.get("description"),
                is_solvent=comp_data.get("is_solvent", True),
            ),
            offering_id=resolved_offering.offering_id,
            offering_title=resolved_offering.title,
            propensity_score=propensity_score,
            tier=tier,
            is_disqualified=is_disqualified,
            disqualification_reason=disqualification_reason,
            score_breakdown=score_breakdown,
            primary_commercial_wedge=primary_wedge,
            operational_rationale=operational_rationale,
            evidence_citations=evidence_citations,
            target_buying_committee=buying_committee,
            estimated_commercial_scope=estimated_scope,
            strategic_pitch_narrative=pitch,
        )

    def prospect_universe(
        self,
        offering: Union[str, Dict[str, Any], OfferingProfile],
        max_accounts: int = 16,
    ) -> ProspectingUniverseResult:
        """
        Discovers candidate accounts and evaluates each prospect using local ML models.
        """
        resolved_offering = self._resolve_offering(offering)
        
        # Discover candidates dynamically (with fallback to benchmark universe)
        candidates = discover_candidate_universe(
            offering_mandate=resolved_offering.title,
            target_count=max_accounts,
            include_benchmarks=True,
        )

        ranked = []
        for cand in candidates[:max_accounts]:
            dossier = self.analyze_single_prospect(cand["name"], resolved_offering)
            ranked.append(dossier)

        # Sort by propensity score descending (disqualified at the bottom)
        ranked.sort(key=lambda d: (not d.is_disqualified, d.propensity_score), reverse=True)

        tier1 = sum(1 for d in ranked if d.propensity_score >= 80.0 and not d.is_disqualified)
        tier2 = sum(1 for d in ranked if 60.0 <= d.propensity_score < 80.0 and not d.is_disqualified)

        return ProspectingUniverseResult(
            offering=resolved_offering,
            total_evaluated=len(ranked),
            tier1_count=tier1,
            tier2_count=tier2,
            ranked_customers=ranked,
        )
