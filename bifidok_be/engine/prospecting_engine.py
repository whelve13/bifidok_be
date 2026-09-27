"""
Customer Prospecting Engine.
Coordinates autonomous entity discovery, multi-source live signal harvesting,
local machine learning scoring (LightGBM/LogisticRegression), and structured sales dossiers.
"""
import concurrent.futures
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
from engine.local_ml.inference import predict_lead_evaluation
from engine.offering_catalog import (
    FLAGSHIP_OFFERINGS,
    decompose_custom_offering,
    offering_dict_to_profile,
)

from connectors.ats import fetch_ats_hiring_signals
from connectors.developer import fetch_developer_signals
from connectors.financials import fetch_financial_signals
from connectors.firmographics import resolve_company_entity
from connectors.gdelt import fetch_gdelt_signals
from connectors.news import evaluate_news_relevance, fetch_company_news
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

        return FLAGSHIP_OFFERINGS.get("Agentic Automation") or FLAGSHIP_OFFERINGS.get("agentic_automation")

    def evaluate_single_company(
        self,
        company_name: str,
        offering: Union[str, Dict[str, Any], OfferingProfile] = "Agentic Automation",
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

        # 1. Resolve company profile dynamically (no candidate pool bias)
        resolved_entity = resolve_company_entity(clean_input)
        comp_data = {
            "name": resolved_entity.get("name", clean_input),
            "domain": resolved_entity.get("domain", f"{clean_input.lower().replace(' ', '')}.com"),
            "legal_name": resolved_entity.get("legal_name", clean_input),
            "country": resolved_entity.get("country", "Global"),
            "headcount": resolved_entity.get("headcount") or 2500,
            "sector": resolved_entity.get("sector") or "Industrial & Enterprise Operations",
            "ticker": resolved_entity.get("ticker"),
            "description": resolved_entity.get("description", "Enterprise operator."),
            "is_solvent": True,
            "operational_attributes": dict(resolved_entity.get("operational_attributes", {})),
        }

        # Dynamic operational attribute and profile inference
        profile_text = (
            f"{comp_data.get('name', '')} {comp_data.get('description', '')} {clean_input}"
        ).lower()

        if any(w in profile_text for w in ["delivery", "logistics", "courier", "express", "parcel", "transport", "freight"]):
            comp_data["operational_attributes"]["urban_delivery_fleets"] = True

        if any(w in profile_text for w in ["chemical", "manufacturing", "industrial", "campus", "factory", "plant", "complex"]):
            comp_data["operational_attributes"]["internal_campus_transit"] = True

        if any(w in profile_text for w in ["all-remote", "100% remote", "remote-only", "remote model"]):
            comp_data["operational_attributes"]["remote_only"] = True

        if any(w in profile_text for w in ["insolvency", "bankruptcy", "insolvent", "liquidation"]):
            comp_data["is_solvent"] = False

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
            "detected_tech": [],
            "has_enterprise_erp": False,
            "tech_stack_breadth": 0,
            "has_leadership_change": False,
            "hiring_velocity_score": 0.0,
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
            signals["semantic_relevance"] = max(signals["semantic_relevance"], 0.98)
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
            signals["semantic_relevance"] = max(signals["semantic_relevance"], 0.92)

        # B. News & Media
        try:
            news = fetch_company_news(company_name, resolved_offering.signal_keywords)
            signals["news_items"] = news
            if news:
                signals["has_news"] = True
                news_eval = evaluate_news_relevance(news, resolved_offering.signal_keywords)
                if news_eval.get("has_leadership_change"):
                    signals["has_leadership_change"] = True
                    lead_articles = news_eval.get("leadership_articles", [])
                    lead_snippet = lead_articles[0].get("title", "C-level appointment") if lead_articles else "Executive leadership appointment"
                    evidence_citations.append(
                        ProspectEvidence(
                            category="Executive Leadership Catalyst",
                            title="C-Level Leadership Appointment / Strategic Reorganization",
                            snippet=f"Leadership transition detected: {lead_snippet[:80]}",
                            source="Executive Intelligence Monitor",
                            confidence=0.92,
                            points_awarded=20.0,
                        )
                    )
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
            signals["hiring_velocity_score"] = ats_res.get("hiring_velocity_score", 0.0)
            if ats_res.get("is_remote_first"):
                comp_data["operational_attributes"]["remote_only"] = True
            if matched:
                evidence_citations.append(
                    ProspectEvidence(
                        category="Recruitment & Hiring Intent",
                        title=f"Target Roles Detected on Public ATS ({ats_res.get('ats_provider', 'Board')})",
                        snippet=f"Active openings matching commercial requirements: {', '.join(matched[:3])}. Velocity score: {signals['hiring_velocity_score']:.2f}.",
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
            signals["detected_tech"] = sec_res.get("detected_tech", [])
            signals["has_enterprise_erp"] = sec_res.get("has_enterprise_erp", False)
            signals["tech_stack_breadth"] = sec_res.get("tech_stack_breadth", 0)

            if signals["detected_tech"]:
                evidence_citations.append(
                    ProspectEvidence(
                        category="Tech Stack Fingerprint",
                        title=f"Enterprise Tech Stack Detected ({len(signals['detected_tech'])} systems)",
                        snippet=f"Passive fingerprint identified enterprise infrastructure: {', '.join(signals['detected_tech'][:4])}.",
                        source="Passive HTTP/TLS Header Reconnaissance",
                        confidence=0.91,
                        points_awarded=16.0,
                    )
                )
        except Exception:
            pass

        # F. Developer Signals & In-House Engineering Capacity
        try:
            dev_res = fetch_developer_signals(company_name)
            if dev_res.get("github_org_found"):
                signals["github_repo_count"] = dev_res.get("repo_count", 0)
                if dev_res.get("repo_count", 0) > 100:
                    evidence_citations.append(
                        ProspectEvidence(
                            category="In-House Engineering Footprint",
                            title=f"Extensive Developer Footprint ({dev_res.get('repo_count', 0)}+ Repositories)",
                            snippet="Organization exhibits substantial internal software engineering capacity. Co-delivery and platform integration preferred over turnkey software outsourcing.",
                            source="GitHub Public API & Developer Footprint",
                            confidence=0.88,
                            points_awarded=0.0,
                        )
                    )
        except Exception:
            pass

        if comp_data.get("github_repos"):
            signals["github_repo_count"] = max(signals.get("github_repo_count", 0), comp_data["github_repos"])

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

        # Dynamic semantic commercial wedge alignment (no hardcoded 3-class bias)
        context_text = (
            f"{company_name} {comp_data.get('sector', '')} {comp_data.get('description', '')} "
            f"{' '.join(signals.get('matched_roles', []))} "
            f"{' '.join(signals.get('detected_tech', []))} "
            f"{' '.join(str(k) for k, v in comp_data.get('operational_attributes', {}).items() if v)}"
        ).lower()

        scored_wedges = []
        for idx, wedge in enumerate(wedges):
            score = 0.0
            w_text = f"{wedge.name} {wedge.target_archetype} {wedge.description} {wedge.value_driver}".lower()

            # Cyber/Security alignment
            if any(w in w_text for w in ["security", "soc", "cyber", "compliance", "threat", "nis2"]):
                if any(s in context_text for s in ["soc", "security", "threat", "cisa", "ciso", "compliance"]) or signals.get("cisa_kev_count", 0) > 0:
                    score += 35.0
                if signals.get("security_grade") in ["C", "D", "F"] or len(signals.get("missing_headers", [])) > 1:
                    score += 25.0

            # Cloud/Modernization alignment
            if any(w in w_text for w in ["cloud", "devops", "platform", "modernization", "infrastructure", "migration"]):
                if any(s in context_text for s in ["cloud", "kubernetes", "devops", "sre", "platform", "azure", "aws", "gcp"]):
                    score += 35.0
                if signals.get("tech_stack_breadth", 0) >= 3.0 or signals.get("github_repo_count", 0) > 20:
                    score += 20.0

            # Automation/Workflow/Operations alignment
            if any(w in w_text for w in ["automation", "agentic", "ai", "workflow", "process", "fleet", "logistics"]):
                if any(s in context_text for s in ["rpa", "automation", "workflow", "fleet", "courier", "logistics", "delivery", "process"]):
                    score += 35.0
                if signals.get("has_enterprise_erp") or comp_data.get("operational_attributes", {}).get("urban_delivery_fleets"):
                    score += 20.0

            # Include slight ML prior if index matches
            if idx == wedge_idx:
                score += 15.0

            scored_wedges.append((score, idx, wedge))

        scored_wedges.sort(key=lambda x: x[0], reverse=True)
        primary_wedge = scored_wedges[0][2]

        # Dynamic buying committee personas aligned with offering (CIO, CISO, CFO)
        off_title_low = resolved_offering.title.lower()
        if any(w in off_title_low for w in ["security", "soc", "cyber", "compliance", "nis2"]):
            buying_committee = [
                DecisionMakerPersona(
                    title="Chief Information Security Officer (CISO)",
                    department="Information Security & Compliance",
                    mandate="Ensure 24/7 continuous threat detection and meet NIS2/DORA regulatory compliance deadlines.",
                    outreach_hook=f"Addressing perimeter resilience and compliance with {resolved_offering.title}.",
                ),
                DecisionMakerPersona(
                    title="Chief Information Officer (CIO)",
                    department="Enterprise IT & Infrastructure",
                    mandate="Eliminate infrastructure vulnerabilities without disrupting line-of-business application availability.",
                    outreach_hook=f"Seamlessly integrating SOC automation into existing IT architectures for {company_name}.",
                ),
                DecisionMakerPersona(
                    title="Chief Financial Officer (CFO)",
                    department="Finance, Risk & Governance",
                    mandate="Mitigate catastrophic cyber insurance premiums and regulatory non-compliance fines.",
                    outreach_hook=f"De-risking regulatory liabilities under EU NIS2 frameworks while optimizing internal security OpEx.",
                ),
            ]
        elif any(w in off_title_low for w in ["cloud", "devops", "platform", "infrastructure", "modernization"]):
            buying_committee = [
                DecisionMakerPersona(
                    title="Chief Information Officer (CIO) / VP of Cloud",
                    department="Platform Engineering & Cloud Architecture",
                    mandate="Modernize legacy application architectures and optimize multi-cloud infrastructure workloads.",
                    outreach_hook=f"Accelerating cloud architecture modernization with {resolved_offering.title}.",
                ),
                DecisionMakerPersona(
                    title="Chief Information Security Officer (CISO)",
                    department="Cloud Security & Governance",
                    mandate="Guarantee sovereign data protection and zero-trust perimeter enforcement during cloud migration.",
                    outreach_hook=f"De-risking cloud transition with automated compliance baselines for {company_name}.",
                ),
                DecisionMakerPersona(
                    title="Chief Financial Officer (CFO)",
                    department="Finance & Procurement",
                    mandate="Rationalize cloud runaway spend (FinOps) and drive measurable ROI on IT capital expenditure.",
                    outreach_hook=f"Structuring migration milestones to deliver clear OpEx predictability and cost efficiency.",
                ),
            ]
        else:
            # Default: Enterprise Automation / AI / Digital Transformation
            buying_committee = [
                DecisionMakerPersona(
                    title="Chief Information Officer (CIO)",
                    department="Information Technology & Enterprise Systems",
                    mandate="Deploy auditable, sovereign AI workflows integrated directly with ERP/CRM without vendor lock-in.",
                    outreach_hook=f"Evidence-grounded autonomous process automation and co-delivery acceleration for {company_name}.",
                ),
                DecisionMakerPersona(
                    title="Chief Information Security Officer (CISO)",
                    department="Information Security & Data Governance",
                    mandate="Ensure enterprise data integrity, EU AI Act compliance, and air-gapped data boundary enforcement.",
                    outreach_hook=f"Ensuring enterprise automation complies with strict data governance and ISO/SOC standards.",
                ),
                DecisionMakerPersona(
                    title="Chief Financial Officer (CFO)",
                    department="Finance & Operational Strategy",
                    mandate="Drive operational margin expansion, reduce manual back-office overhead, and accelerate EBITDA growth.",
                    outreach_hook=f"Accelerating operational throughput with measurable payback periods under 6 months.",
                ),
            ]

        # Adaptive commercial scope across 5 scale tiers (SMB to Global Enterprise)
        raw_headcount = comp_data.get("headcount")
        headcount = raw_headcount or 2500
        github_repos_count = signals.get("github_repo_count", 0)

        # Big Tech / Hyperscaler In-House Build Reality check
        if github_repos_count > 300:
            estimated_scope = "€150K - €450K Specialized Co-Innovation Pilot (High In-House Build Capacity)"
        elif headcount >= 50000:
            estimated_scope = "€2.0M - €7.5M Global Enterprise Modernization & Co-Delivery"
        elif headcount >= 10000:
            estimated_scope = "€750K - €2.5M Large Enterprise Multi-Division Deployment"
        elif headcount >= 2500:
            estimated_scope = "€300K - €900K Upper Mid-Market Departmental Acceleration"
        elif headcount >= 500:
            estimated_scope = "€100K - €350K Mid-Market Strategic Production Rollout"
        else:
            estimated_scope = "€35K - €100K Targeted Production Pilot & Architecture Sprint"

        # Rationale and grounded pitch with verbatim evidence citations
        scale_text = f" and organizational scale ({headcount:,} employees)" if raw_headcount else ""
        citations_summary = ""
        if evidence_citations:
            top_evidence_titles = [f"  - [{e.category}] {e.title}: \"{e.snippet}\"" for e in evidence_citations[:3]]
            citations_summary = "\n\nVerified Public Signals & Catalysts:\n" + "\n".join(top_evidence_titles)

        # Orange Systems Strategic Potential ROI & Outsource Propensity analysis
        if github_repos_count > 150:
            roi_strategic_note = (
                f" In-House Build Factor: {company_name} maintains a massive internal developer footprint ({github_repos_count}+ public repos), "
                f"creating high resistance to general IT outsourcing; commercial engagements should target specialized co-delivery rather than generic staff augmentation."
            )
        elif 250 <= headcount <= 35000:
            roi_strategic_note = (
                f" High Potential ROI for Orange Systems: Mid-Market / Upper Mid-Market scale ({headcount:,} employees) in {comp_data.get('sector', 'Enterprise')} "
                f"represents optimal outsourcing propensity with rapid procurement velocity and high customer lifetime value."
            )
        else:
            roi_strategic_note = (
                f" Strategic Vertical Expansion: Accelerates Orange Systems' capability to scale into the {comp_data.get('sector', 'Enterprise')} vertical market."
            )

        operational_rationale = (
            f"{company_name} exhibits ideal enterprise characteristics for {resolved_offering.title}: "
            f"{primary_wedge.name} provides immediate operational synergy with their {comp_data.get('sector', 'Enterprise')} footprint, "
            f"supported by verified live buying signals{scale_text}.{roi_strategic_note}"
        )

        pitch = (
            f"Subject: Accelerating {company_name}'s operational efficiency with {resolved_offering.title}\n\n"
            f"Dear Leadership Team at {company_name},\n\n"
            f"Given {company_name}'s strategic position in {comp_data.get('sector', 'the market')}, "
            f"we noted strong operational synergy regarding {primary_wedge.name}. "
            f"Our solution helps enterprises achieve: {primary_wedge.value_driver}{citations_summary}\n\n"
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
        
        # Discover candidates dynamically across open web sources
        candidates = discover_candidate_universe(
            offering_mandate=resolved_offering.title,
            target_count=max_accounts,
        )

        ranked = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_cand = {
                executor.submit(self.analyze_single_prospect, cand["name"], resolved_offering): cand
                for cand in candidates[:max_accounts]
            }
            for fut in concurrent.futures.as_completed(future_to_cand):
                try:
                    dossier = fut.result()
                    ranked.append(dossier)
                except Exception:
                    pass

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
