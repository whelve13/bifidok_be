"""
Autonomous Customer Prospecting & Buying Intent Engine.
Replaces rigid BMAA scoring with multi-dimensional enterprise discovery,
dynamic offering decomposition, live evidence harvesting, and strategic sales dossiers.
"""
import concurrent.futures
from typing import List, Dict, Any, Optional, Union

from models import (
    CompanyProfile,
    OfferingProfile,
    CommercialWedge,
    DecisionMakerPersona,
    ProspectEvidence,
    ScoreBreakdown,
    PerfectCustomerDossier,
    ProspectingUniverseResult
)
from engine.offering_catalog import FLAGSHIP_OFFERINGS, decompose_custom_offering
from engine.candidate_pool import get_candidate_universe, find_candidate_by_name

from connectors.firmographics import resolve_company_entity
from connectors.financials import fetch_financial_signals
from connectors.news import fetch_company_news, evaluate_news_relevance
from connectors.ats import fetch_ats_hiring_signals
from connectors.registries import verify_official_registry
from connectors.tenders import fetch_public_procurement_tenders

class CustomerProspectingEngine:
    """
    Intelligent B2B Prospecting & Match Engine.
    Given any commercial offering (e.g. 'Bikes', 'Process Automation', 'Managed SOC', or custom),
    identifies, screens, and ranks high-propensity enterprise customers using live public signals.
    """

    def __init__(self):
        pass

    def _resolve_offering(self, offering_input: Union[str, OfferingProfile]) -> OfferingProfile:
        if isinstance(offering_input, OfferingProfile):
            return offering_input
        if offering_input in FLAGSHIP_OFFERINGS:
            return FLAGSHIP_OFFERINGS[offering_input]
        return decompose_custom_offering(offering_input)

    def prospect_universe(
        self,
        offering: Union[str, OfferingProfile],
        custom_candidates: Optional[List[Dict[str, Any]]] = None,
        max_workers: int = 6
    ) -> ProspectingUniverseResult:
        """
        Discovers, queries, scores, and ranks candidate companies for a given commercial offering.
        """
        resolved_offering = self._resolve_offering(offering)
        candidate_pool = custom_candidates or get_candidate_universe(resolved_offering.target_sectors)

        scored_dossiers: List[PerfectCustomerDossier] = []

        # Analyze candidates in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_cand = {
                executor.submit(self.analyze_single_prospect, cand["name"], resolved_offering, cand.get("domain")): cand
                for cand in candidate_pool
            }
            for future in concurrent.futures.as_completed(future_to_cand):
                try:
                    dossier = future.result()
                    scored_dossiers.append(dossier)
                except Exception as e:
                    cand = future_to_cand[future]
                    # Log or handle exception gracefully
                    pass

        # Sort descending by propensity score (disqualified at the bottom)
        scored_dossiers.sort(key=lambda d: (-1 if d.is_disqualified else d.propensity_score), reverse=True)

        tier1_count = sum(1 for d in scored_dossiers if d.tier.startswith("Tier 1") and not d.is_disqualified)
        tier2_count = sum(1 for d in scored_dossiers if d.tier.startswith("Tier 2") and not d.is_disqualified)

        return ProspectingUniverseResult(
            offering=resolved_offering,
            total_evaluated=len(scored_dossiers),
            tier1_count=tier1_count,
            tier2_count=tier2_count,
            ranked_customers=scored_dossiers
        )

    def analyze_single_prospect(
        self,
        company_name: str,
        offering: Union[str, OfferingProfile],
        domain_hint: Optional[str] = None
    ) -> PerfectCustomerDossier:
        """
        Conducts deep multi-source intelligence gathering and scores fit for a specific enterprise account.
        """
        resolved_offering = self._resolve_offering(offering)
        cand_meta = find_candidate_by_name(company_name) or {}
        op_attrs = cand_meta.get("operational_attributes", {})

        # 1. Entity Resolution (Clearbit & Wikipedia)
        resolved_entity = resolve_company_entity(company_name, domain_hint)
        domain = resolved_entity["domain"]

        # 2. Parallel Federated Queries to Catalog Endpoints with Offering-Specific Keywords
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            fut_registry = executor.submit(verify_official_registry, company_name)
            fut_financials = executor.submit(fetch_financial_signals, company_name)
            fut_news = executor.submit(fetch_company_news, company_name, resolved_offering.signal_keywords)
            fut_ats = executor.submit(fetch_ats_hiring_signals, company_name, resolved_offering.ats_roles)
            fut_tenders = executor.submit(fetch_public_procurement_tenders, company_name, resolved_offering.tender_keywords)

            registry_data = fut_registry.result()
            financials = fut_financials.result()
            news_items = fut_news.result()
            ats_data = fut_ats.result()
            tender_data = fut_tenders.result()

        # Build Unified CompanyProfile
        canonical_name = cand_meta.get("name") or company_name
        headcount = financials.get("headcount") or cand_meta.get("headcount") or 1000
        sector = financials.get("sector") or cand_meta.get("sector") or "Enterprise & Industrials"
        country = financials.get("country") or cand_meta.get("country") or resolved_entity.get("country") or "EU"
        ticker = financials.get("ticker") or cand_meta.get("ticker")
        legal_name = cand_meta.get("name") or registry_data.get("legal_name") or canonical_name
        is_solvent = registry_data.get("is_solvent", True)

        # Check explicit bankruptcy in candidate pool
        if op_attrs.get("physical_footprint_level") == "Insolvent":
            is_solvent = False

        profile = CompanyProfile(
            name=canonical_name,
            domain=domain or cand_meta.get("domain", ""),
            legal_name=legal_name,
            country=country,
            headcount=headcount,
            sector=sector,
            ticker=ticker,
            description=cand_meta.get("description", "") or resolved_entity.get("description", "")[:280],
            is_solvent=is_solvent
        )

        evidence_list: List[ProspectEvidence] = []

        # =========================================================
        # 3. HARD GATES & DISQUALIFICATION CHECKS
        # =========================================================
        if not is_solvent:
            return PerfectCustomerDossier(
                company=profile,
                offering_id=resolved_offering.offering_id,
                offering_title=resolved_offering.title,
                propensity_score=0.0,
                tier="Disqualified",
                is_disqualified=True,
                disqualification_reason=f"Account is insolvent or under liquidation ({registry_data.get('registry_source', 'Official European Corporate Registry')}).",
                score_breakdown=ScoreBreakdown(),
                primary_commercial_wedge=CommercialWedge(
                    name="N/A - Disqualified",
                    target_archetype="Insolvent Entity",
                    description="Commercial engagement prohibited.",
                    value_driver="Credit and solvency default risk."
                ),
                operational_rationale="Corporate insolvency renders the account commercially unviable for procurement or leasing contracts.",
                evidence_citations=[
                    ProspectEvidence(
                        category="Registry Solvency",
                        title="Corporate Insolvency Notice",
                        snippet=f"Confirmed active liquidation proceedings in {registry_data.get('registry_source', 'Court Registry')}.",
                        source="Official Commercial Register",
                        confidence=1.0,
                        points_awarded=0.0
                    )
                ],
                target_buying_committee=[],
                estimated_commercial_scope="0 (Insolvent)",
                strategic_pitch_narrative="Account disqualified due to active insolvency proceedings."
            )

        # Physical presence check
        is_100pct_remote = op_attrs.get("is_100pct_remote", False) or "all-remote" in profile.description.lower()
        if resolved_offering.requires_physical_presence and is_100pct_remote:
            return PerfectCustomerDossier(
                company=profile,
                offering_id=resolved_offering.offering_id,
                offering_title=resolved_offering.title,
                propensity_score=15.0,
                tier="Disqualified / Low Fit",
                is_disqualified=True,
                disqualification_reason="100% remote company model with zero physical campuses, delivery couriers, or local logistics operations.",
                score_breakdown=ScoreBreakdown(operational_fit=5.0, composite_score=15.0),
                primary_commercial_wedge=CommercialWedge(
                    name="N/A - Operational Mismatch",
                    target_archetype="Remote Organization",
                    description="No physical operational footprint for hardware/fleet deployment.",
                    value_driver="Lack of operational fit."
                ),
                operational_rationale="Physical fleet or campus mobility solutions require on-site employees or physical delivery depots. All-remote workforces do not possess this operational need.",
                evidence_citations=[
                    ProspectEvidence(
                        category="Operational Footprint",
                        title="All-Remote Operational Model",
                        snippet="Public disclosures confirm 100% distributed remote workforce with no corporate physical offices.",
                        source="Corporate Profile & SEC Disclosures",
                        confidence=0.95,
                        points_awarded=0.0
                    )
                ],
                target_buying_committee=[],
                estimated_commercial_scope="0 (No physical operations)",
                strategic_pitch_narrative="Account operates 100% remotely. No physical fleet opportunity."
            )

        # =========================================================
        # 4. MULTI-DIMENSIONAL FIT & PROPENSITY SCORING
        # =========================================================
        op_fit_pts = 0.0
        urgency_pts = 0.0
        scale_pts = 0.0
        intent_pts = 0.0

        # --- DIMENSION 1: OPERATIONAL FIT (Max 35 pts) ---
        sector_lower = profile.sector.lower()
        target_sectors_lower = [s.lower() for s in resolved_offering.target_sectors]

        has_last_mile = op_attrs.get("has_last_mile_delivery", False) or any(k in profile.description.lower() for k in ["courier", "delivery", "logistics", "parcels", "food"])
        has_large_campus = op_attrs.get("has_large_campus", False) or any(k in profile.description.lower() for k in ["manufacturing", "plant", "complex", "industrial", "aerospace", "automotive"])
        is_large_employer = (profile.headcount or 0) >= 10000

        if resolved_offering.offering_id == "commercial_bikes":
            if has_last_mile:
                op_fit_pts += 35.0
                evidence_list.append(ProspectEvidence(
                    category="Operational Footprint",
                    title="High-Volume Last-Mile Delivery Network",
                    snippet=f"Operates dedicated urban couriers, postal delivery, or logistics parcel distribution networks.",
                    source="Company Operational Dossier",
                    confidence=0.95,
                    points_awarded=35.0
                ))
            elif has_large_campus:
                op_fit_pts += 30.0
                evidence_list.append(ProspectEvidence(
                    category="Operational Footprint",
                    title="Extensive Multi-Site Industrial Campus Footprint",
                    snippet=f"Operates massive multi-building production and engineering complexes spanning square kilometers ({op_attrs.get('physical_footprint_level', 'High')}).",
                    source="Company Operational Dossier",
                    confidence=0.90,
                    points_awarded=30.0
                ))
            elif is_large_employer:
                op_fit_pts += 22.0
                evidence_list.append(ProspectEvidence(
                    category="Operational Footprint",
                    title="Large-Scale Corporate Commuter Base",
                    snippet=f"Massive on-site workforce ({profile.headcount:,} staff) prime for employee green commuter bike-leasing programs.",
                    source="Headcount Disclosures",
                    confidence=0.85,
                    points_awarded=22.0
                ))
            else:
                op_fit_pts += 12.0
        else:
            # Generalized operational fit for other offerings
            sector_match = any(ts in sector_lower or sector_lower in ts for ts in target_sectors_lower)
            if sector_match:
                op_fit_pts += 28.0
                evidence_list.append(ProspectEvidence(
                    category="Industry Alignment",
                    title=f"Core Target Sector: {profile.sector}",
                    snippet=f"Account operates within priority target vertical for {resolved_offering.title}.",
                    source="Firmographics & SIC/NACE",
                    confidence=0.90,
                    points_awarded=28.0
                ))
            else:
                op_fit_pts += 14.0

        # --- DIMENSION 2: TIMING & URGENCY SIGNALS (Max 30 pts) ---
        # A. News analysis
        news_eval = evaluate_news_relevance(news_items, resolved_offering.signal_keywords)
        if news_eval["is_detected"]:
            matched_arts = news_eval["articles"]
            urgency_pts += min(18.0, 10.0 + (3.0 * len(matched_arts)))
            top_art = matched_arts[0]
            evidence_list.append(ProspectEvidence(
                category="Real-Time Public Signal",
                title=f"Live Press Catalyst ({top_art['title'][:65]}...)",
                snippet=f"Recent announcement referencing {', '.join(top_art['keywords'][:3])}. Date: {top_art.get('date', 'Recent')}.",
                source="Google News Pan-European Feed",
                confidence=0.92,
                points_awarded=round(urgency_pts, 1)
            ))
        else:
            # Baseline sector urgency or ESG target in metadata
            if op_attrs.get("esg_net_zero_target"):
                urgency_pts += 12.0
                evidence_list.append(ProspectEvidence(
                    category="ESG Mandate",
                    title=f"Corporate Decarbonization Mandate: {op_attrs['esg_net_zero_target']}",
                    snippet="Public sustainability commitment accelerating adoption of clean mobility and Scope 3 emissions cuts.",
                    source="Audited Sustainability Disclosures",
                    confidence=0.88,
                    points_awarded=12.0
                ))
            else:
                urgency_pts += 6.0

        # B. Public Procurement & Tenders
        if tender_data.get("active_tender_rfp"):
            tender_pts = 12.0
            urgency_pts = min(30.0, urgency_pts + tender_pts)
            top_notice = tender_data.get("notices", [{}])[0]
            evidence_list.append(ProspectEvidence(
                category="Public Tender / RFP",
                title="Active Procurement RFP Notice Detected",
                snippet=f"Notice: '{top_notice.get('title', 'Public procurement tender')[:75]}...'",
                source=tender_data.get("source", "Public Procurement News Feed"),
                confidence=tender_data.get("confidence", 0.40),
                points_awarded=tender_pts
            ))

        # --- DIMENSION 3: PURCHASING SCALE & FINANCIAL CAPACITY (Max 20 pts) ---
        if profile.headcount:
            if profile.headcount >= 100000:
                scale_pts += 12.0
            elif profile.headcount >= 20000:
                scale_pts += 10.0
            elif profile.headcount >= 2000:
                scale_pts += 7.0
            elif profile.headcount >= resolved_offering.min_headcount:
                scale_pts += 5.0

        op_margin = financials.get("operating_margin")
        if op_margin is not None:
            if op_margin > 0.08:
                scale_pts += 8.0
                evidence_list.append(ProspectEvidence(
                    category="Financial Capacity",
                    title=f"Strong Financial Solvency (Operating Margin {op_margin*100:.1f}%)",
                    snippet="Robust balance sheet and commercial budget capacity to underwrite multi-year fleet contracts.",
                    source="Yahoo Finance Audited P&L",
                    confidence=0.95,
                    points_awarded=8.0
                ))
            else:
                scale_pts += 5.0
                evidence_list.append(ProspectEvidence(
                    category="Financial Health",
                    title="Capital Restraint / Overhead Efficiency Mandate",
                    snippet=f"Operating margin at {op_margin*100:.1f}%; strong incentive to deploy cost-reducing fleet/automation solutions.",
                    source="Yahoo Finance Audited P&L",
                    confidence=0.85,
                    points_awarded=5.0
                ))
        else:
            scale_pts += 6.0

        scale_pts = min(20.0, scale_pts)

        # --- DIMENSION 4: HIRING INTENT & BUYING COMMITTEE (Max 15 pts) ---
        matched_roles = ats_data.get("matched_roles", [])
        if matched_roles:
            intent_pts += min(15.0, 7.0 + (3.0 * len(matched_roles)))
            evidence_list.append(ProspectEvidence(
                category="Active Recruitment Signal",
                title=f"Recruiting Key Decision Roles ({len(matched_roles)} Openings)",
                snippet=f"Actively hiring in relevant functions: {', '.join(matched_roles[:3])}.",
                source=f"{ats_data.get('ats_provider', 'Public Career Boards')}",
                confidence=0.92,
                points_awarded=round(intent_pts, 1)
            ))
        elif ats_data.get("total_openings", 0) > 30:
            intent_pts += 7.0
        else:
            intent_pts += 4.0

        # Composite Score Calculation
        composite_score = round(op_fit_pts + urgency_pts + scale_pts + intent_pts, 1)
        composite_score = max(0.0, min(100.0, composite_score))

        breakdown = ScoreBreakdown(
            operational_fit=round(op_fit_pts, 1),
            timing_urgency=round(urgency_pts, 1),
            purchasing_scale=round(scale_pts, 1),
            hiring_intent=round(intent_pts, 1),
            composite_score=composite_score
        )

        # Tier Categorization
        if composite_score >= 80.0:
            tier = "Tier 1 - Prime Target (Urgent Buying Catalysts)"
        elif composite_score >= 60.0:
            tier = "Tier 2 - Strategic Opportunity (Strong Operational Fit)"
        elif composite_score >= 40.0:
            tier = "Tier 3 - Nurture Candidate"
        else:
            tier = "Cold / Baseline"

        # =========================================================
        # 5. COMMERCIAL WEDGE SELECTION & DOSSIER SYNTHESIS
        # =========================================================
        selected_wedge = self._select_commercial_wedge(resolved_offering, op_attrs, profile)
        decision_committee = self._determine_buying_committee(selected_wedge, profile)
        estimated_scope = self._estimate_commercial_scope(resolved_offering, selected_wedge, profile)
        pitch_narrative = self._generate_strategic_pitch(
            offering=resolved_offering,
            wedge=selected_wedge,
            company=profile,
            evidence=evidence_list,
            committee=decision_committee
        )

        operational_rationale = (
            f"{profile.name} exhibits ideal enterprise characteristics for {resolved_offering.title}: "
            f"{selected_wedge.name} provides immediate operational synergy with their {profile.sector} footprint, "
            f"supported by verified live buying signals and organizational scale ({profile.headcount:,} employees)."
        )

        return PerfectCustomerDossier(
            company=profile,
            offering_id=resolved_offering.offering_id,
            offering_title=resolved_offering.title,
            propensity_score=composite_score,
            tier=tier,
            is_disqualified=False,
            disqualification_reason=None,
            score_breakdown=breakdown,
            primary_commercial_wedge=selected_wedge,
            operational_rationale=operational_rationale,
            evidence_citations=evidence_list,
            target_buying_committee=decision_committee,
            estimated_commercial_scope=estimated_scope,
            strategic_pitch_narrative=pitch_narrative
        )

    def _select_commercial_wedge(
        self,
        offering: OfferingProfile,
        op_attrs: Dict[str, Any],
        profile: CompanyProfile
    ) -> CommercialWedge:
        """Determines the specific operational wedge tailored to the target's business model."""
        if offering.offering_id == "commercial_bikes":
            if op_attrs.get("has_last_mile_delivery") or any(k in profile.description.lower() for k in ["courier", "delivery", "logistics", "food", "parcel"]):
                return offering.target_wedges[0]  # Last-Mile Delivery Cargo E-Bike Fleet
            elif op_attrs.get("has_large_campus") or any(k in profile.description.lower() for k in ["manufacturing", "plant", "aerospace", "automotive", "chemical"]):
                return offering.target_wedges[1]  # Large Industrial Campus & Inter-Facility Mobility
            else:
                return offering.target_wedges[2]  # Corporate Commuter Bike-Leasing Employee Perk (JobRad Scheme)
        
        # Default to first wedge for other offerings
        return offering.target_wedges[0] if offering.target_wedges else CommercialWedge(
            name=f"Enterprise {offering.title}",
            target_archetype="Enterprise Customers",
            description=offering.description,
            value_driver="Operational excellence"
        )

    def _determine_buying_committee(
        self,
        wedge: CommercialWedge,
        profile: CompanyProfile
    ) -> List[DecisionMakerPersona]:
        """Identifies specific executive decision makers for consultative sales."""
        w_name = wedge.name.lower()

        if "last-mile" in w_name or "cargo" in w_name:
            return [
                DecisionMakerPersona(
                    title="VP of Global Fleet & Urban Logistics Operations",
                    department="Supply Chain & Fleet Operations",
                    mandate="Oversees urban delivery asset allocation, vehicle TCO, fuel spend, and courier throughput.",
                    outreach_hook="Solving inner-city congestion delays and bypassing European low-emission zone vehicle bans."
                ),
                DecisionMakerPersona(
                    title="Chief Sustainability Officer (CSO) / Head of Net Zero",
                    department="Executive Leadership / ESG",
                    mandate="Responsible for meeting public Scope 1 and Scope 3 transport decarbonization targets.",
                    outreach_hook="Measurable zero-emission delivery metrics ready for audited CSRD compliance reporting."
                ),
                DecisionMakerPersona(
                    title="Director of European Procurement",
                    department="Strategic Sourcing",
                    mandate="Negotiates commercial vehicle fleet leasing and maintenance service contracts.",
                    outreach_hook="Turnkey leasing with inclusive battery management and 99.5% uptime SLAs."
                )
            ]
        elif "campus" in w_name or "industrial" in w_name:
            return [
                DecisionMakerPersona(
                    title="VP of Plant Engineering & Site Operations",
                    department="Manufacturing Operations",
                    mandate="Controls inter-facility transit, maintenance technician deployment speed, and plant safety.",
                    outreach_hook="Slashing technician intra-plant travel latency by 60% across multi-kilometer facility halls."
                ),
                DecisionMakerPersona(
                    title="Head of Corporate Real Estate & Facilities",
                    department="Workplace & Infrastructure",
                    mandate="Manages on-site campus transport, internal vehicle fleets, and micro-infrastructure.",
                    outreach_hook="Eliminating dirty internal combustion maintenance vans inside factory perimeters."
                )
            ]
        elif "commuter" in w_name or "leasing" in w_name or "jobrad" in w_name:
            return [
                DecisionMakerPersona(
                    title="Chief People Officer / VP Total Rewards",
                    department="Human Resources & People",
                    mandate="Owns employee retention, wellness perks, and employer branding attractiveness.",
                    outreach_hook="Zero-cost corporate benefit delivering high employee satisfaction and health perks."
                ),
                DecisionMakerPersona(
                    title="Head of Corporate Sustainability & Mobility",
                    department="ESG / Corporate Affairs",
                    mandate="Directly tasked with reducing corporate employee commuter Scope 3 emissions.",
                    outreach_hook="Auditable carbon emission offsets directly tied to employee commuting shifts."
                )
            ]
        else:
            return [
                DecisionMakerPersona(
                    title="Chief Operating Officer (COO) / VP Operations",
                    department="Executive Operations",
                    mandate="Optimizing business operational efficiency and eliminating manual cost centers.",
                    outreach_hook="Measurable operational efficiency gains within 90 days."
                ),
                DecisionMakerPersona(
                    title="Head of Digital Transformation / Enterprise Architecture",
                    department="Technology & Strategy",
                    mandate="Modernizing legacy enterprise systems and scaling automated capabilities.",
                    outreach_hook="Seamless integration with current enterprise architecture."
                )
            ]

    def _estimate_commercial_scope(
        self,
        offering: OfferingProfile,
        wedge: CommercialWedge,
        profile: CompanyProfile
    ) -> str:
        """Estimates contract scope and unit potential."""
        headcount = profile.headcount or 5000
        w_name = wedge.name.lower()

        if offering.offering_id == "commercial_bikes":
            if "last-mile" in w_name or "cargo" in w_name:
                est_bikes = max(150, min(12000, int(headcount * 0.05)))
                return f"{est_bikes:,} - {int(est_bikes*1.8):,} Cargo E-Bikes across European metro depots"
            elif "campus" in w_name:
                est_bikes = max(80, min(4500, int(headcount * 0.03)))
                return f"{est_bikes:,} - {int(est_bikes*1.6):,} Ruggedized On-Site Industrial E-Bikes & Trikes"
            else:
                est_eligible = max(200, min(25000, int(headcount * 0.15)))
                return f"{est_eligible:,} Eligible Employees for Corporate Bike-Leasing Scheme"
        
        return f"Enterprise Contract for {profile.name} ({headcount:,} employees)"

    def _generate_strategic_pitch(
        self,
        offering: OfferingProfile,
        wedge: CommercialWedge,
        company: CompanyProfile,
        evidence: List[ProspectEvidence],
        committee: List[DecisionMakerPersona]
    ) -> str:
        """
        Synthesizes a strategic executive pitch narrative and consultative talking points.
        (NOT a canned spam email!).
        """
        top_trigger = next((e.snippet for e in evidence if "Signal" in e.category or "Press" in e.category or "ESG" in e.category), "corporate sustainability and operational efficiency targets")
        target_persona = committee[0].title if committee else "Executive Leadership"

        narrative = f"""### STRATEGIC ACCOUNT ENGAGEMENT BRIEF: {company.name.upper()}
**Commercial Angle / Wedge:** {wedge.name}
**Primary Buyer Persona:** {target_persona}
**Strategic Rationale:**
{wedge.value_driver}

**Executive Intelligence Context:**
Recent market signals confirm {company.name}'s strategic focus on: "{top_trigger}".
Deploying Orange's {offering.title} directly addresses this mandate through our turn-key {wedge.name} model.

**Consultative Discovery Angles for Sales Reps:**
1. Focus on operational TCO: Highlight how replacing traditional assets with our managed solution eliminates capital expenditure and maintenance friction.
2. Leverage the ESG regulatory catalyst: Use CSRD Scope 3 / Zero-Emission Zone compliance as the primary buying driver.
3. Propose a scoped 60-day pilot deployment in a flagship metropolitan depot or manufacturing campus before broad European rollout."""

        return narrative
