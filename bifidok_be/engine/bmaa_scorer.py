import json
import math
import os
import concurrent.futures
from typing import List, Dict, Any, Optional

from models import (
    CompanyProfile,
    SolutionSpec,
    SignalEvidence,
    SolutionAlignment,
    CompanyAnalysisResult
)
from connectors.firmographics import resolve_company_entity
from connectors.financials import fetch_financial_signals
from connectors.news import fetch_company_news, evaluate_news_relevance
from connectors.security import analyze_security_posture
from connectors.ats import fetch_ats_hiring_signals
from connectors.registries import verify_official_registry
from connectors.developer import fetch_developer_signals
from connectors.vulnerabilities import evaluate_vulnerability_exposure
from connectors.tenders import fetch_public_procurement_tenders

# Prior probability that a random enterprise needs an IT service
PRIOR_PROBABILITY = 0.15
PRIOR_LOG_ODDS = math.log(PRIOR_PROBABILITY / (1.0 - PRIOR_PROBABILITY))

class BMAAScorer:
    """
    Bayesian Multi-Attribute Alignment (BMAA) Engine.
    Evaluates candidate enterprise against predefined solutions JSON using
    Bayesian Log-Odds updating and exact additive attribution across all XLSX catalog endpoints.
    """

    def __init__(self, solutions_path: Optional[str] = None):
        if solutions_path is None:
            solutions_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "predefined_solutions.json"
            )
        self.solutions: List[SolutionSpec] = self._load_solutions(solutions_path)

    def _load_solutions(self, path: str) -> List[SolutionSpec]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [SolutionSpec(**item) for item in data]

    def analyze_company(self, company_name: str, domain_hint: Optional[str] = None) -> CompanyAnalysisResult:
        """
        Orchestrates entity resolution, parallel endpoint queries across all categories, and solution alignment.
        """
        # 1. Entity Resolution (Clearbit & Wikipedia - Rows 44, 45)
        resolved_entity = resolve_company_entity(company_name, domain_hint)
        domain = resolved_entity["domain"]

        # 2. Federated Fetch from All Catalog Endpoints (in Parallel)
        with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
            future_reg = executor.submit(verify_official_registry, company_name)
            future_financials = executor.submit(fetch_financial_signals, company_name)
            future_news = executor.submit(fetch_company_news, company_name)
            future_sec = executor.submit(analyze_security_posture, domain)
            future_ats = executor.submit(fetch_ats_hiring_signals, company_name)
            future_dev = executor.submit(fetch_developer_signals, company_name)
            future_tenders = executor.submit(fetch_public_procurement_tenders, company_name)

            registry_data = future_reg.result()
            financials = future_financials.result()
            news_items = future_news.result()
            security_osint = future_sec.result()
            ats_data = future_ats.result()
            dev_signals = future_dev.result()
            tender_data = future_tenders.result()

        # Cross-reference security subdomains against CISA KEV active exploits (Row 28)
        cisa_vulns = evaluate_vulnerability_exposure(
            security_osint.get("exposed_subdomains", []),
            dev_signals.get("top_languages", [])
        )

        # Assemble unified CompanyProfile
        headcount = financials.get("headcount") or 500
        country = financials.get("country") or resolved_entity.get("country") or "EU"
        sector = financials.get("sector") or "Industrial / Technology"
        ticker = financials.get("ticker")
        legal_name = registry_data.get("legal_name") or resolved_entity.get("legal_name") or resolved_entity["name"]
        is_solvent = registry_data.get("is_solvent", True)

        profile = CompanyProfile(
            name=resolved_entity["name"],
            domain=domain,
            legal_name=legal_name,
            country=country,
            headcount=headcount,
            sector=sector,
            ticker=ticker,
            description=resolved_entity.get("description", "")[:280] + ("..." if len(resolved_entity.get("description", "")) > 280 else ""),
            is_solvent=is_solvent
        )

        ranked_alignments: List[SolutionAlignment] = []

        # 3. Evaluate each Predefined Solution
        for sol in self.solutions:
            alignment = self._evaluate_solution(
                sol=sol,
                profile=profile,
                financials=financials,
                news_items=news_items,
                security=security_osint,
                ats=ats_data,
                dev=dev_signals,
                tenders=tender_data,
                cisa=cisa_vulns,
                registry=registry_data
            )
            ranked_alignments.append(alignment)

        # Sort descending by score
        ranked_alignments.sort(key=lambda x: x.alignment_score, reverse=True)
        best = ranked_alignments[0] if ranked_alignments else None

        return CompanyAnalysisResult(
            company=profile,
            ranked_solutions=ranked_alignments,
            best_solution=best
        )

    def _evaluate_solution(
        self,
        sol: SolutionSpec,
        profile: CompanyProfile,
        financials: Dict[str, Any],
        news_items: List[Dict[str, Any]],
        security: Dict[str, Any],
        ats: Dict[str, Any],
        dev: Dict[str, Any],
        tenders: Dict[str, Any],
        cisa: Dict[str, Any],
        registry: Dict[str, Any]
    ) -> SolutionAlignment:
        # Check Hard Gating Rules
        if not profile.is_solvent:
            return SolutionAlignment(
                solution_id=sol.solution_id,
                solution_name=sol.solution_name,
                alignment_score=0.0,
                tier="Disqualified",
                is_disqualified=True,
                disqualification_reason=f"Company marked insolvent in {registry.get('registry_source', 'Official Registry')}."
            )

        if profile.headcount and profile.headcount < sol.target_icp.min_headcount:
            return SolutionAlignment(
                solution_id=sol.solution_id,
                solution_name=sol.solution_name,
                alignment_score=0.0,
                tier="Disqualified",
                is_disqualified=True,
                disqualification_reason=f"Headcount ({profile.headcount}) below minimum threshold ({sol.target_icp.min_headcount})."
            )

        # Bayesian Evidence Accumulation
        current_log_odds = PRIOR_LOG_ODDS
        evidence_list: List[SignalEvidence] = []
        total_delta = 0.0

        for crit in sol.alignment_criteria:
            strength = 0.0
            evidence_text = ""
            source = ""

            if crit.category == "financial":
                source = "Yahoo Finance & yfinance (Rows 6-7)"
                if financials.get("sga_margin_pressure"):
                    strength = 0.85
                    evidence_text = "Operating margin compression indicates overhead cost pressure."
                elif financials.get("operating_margin") is not None:
                    strength = 0.40
                    evidence_text = f"Operating margin recorded at {financials['operating_margin']*100:.1f}%."
                else:
                    strength = 0.20
                    evidence_text = "Public margin disclosures unavailable; neutral baseline."

            elif crit.category == "ats_hiring":
                source = f"{ats.get('ats_provider', 'ATS')} Portal (Rows 20-22)"
                matched_roles = ats.get("matched_roles", [])
                if matched_roles:
                    strength = min(1.0, 0.4 + (0.2 * len(matched_roles)))
                    evidence_text = f"Found {len(matched_roles)} open roles: {', '.join(matched_roles[:3])}."
                elif ats.get("total_openings", 0) > 20:
                    strength = 0.50
                    evidence_text = f"High hiring velocity ({ats['total_openings']} active roles)."
                else:
                    strength = 0.15
                    evidence_text = "No direct automation keyword openings found in public ATS."

            elif crit.category == "news":
                source = "Google News RSS (Rows 15-16)"
                eval_news = evaluate_news_relevance(news_items, crit.keywords or [])
                if eval_news["is_detected"]:
                    strength = min(1.0, 0.5 + (0.15 * eval_news["matched_count"]))
                    top_art = eval_news["articles"][0]["title"]
                    evidence_text = f"News trigger: '{top_art[:80]}...'"
                else:
                    strength = 0.10
                    evidence_text = "No direct restructuring or initiative news in the last 30 days."

            elif crit.category == "security_osint":
                source = "crt.sh, HTTP Observatory & CISA KEV (Rows 26-28)"
                grade = security.get("grade", "B")
                exposed = security.get("exposed_subdomains", [])
                has_cisa = cisa.get("has_critical_exposure", False)

                if has_cisa:
                    strength = 0.95
                    evidence_text = f"Critical vulnerability exposure: {cisa.get('matched_cves', [{}])[0].get('cveID')} affecting perimeter."
                elif grade in ["D", "F"]:
                    strength = 0.85
                    evidence_text = f"Low web security grade '{grade}' with missing {', '.join(security.get('missing_headers', [])[:2])}."
                elif exposed:
                    strength = 0.70
                    evidence_text = f"Exposed subdomains identified: {', '.join(exposed[:3])}."
                else:
                    strength = 0.25
                    evidence_text = f"Perimeter hygiene grade '{grade}'; no weaponized CVEs detected."

            elif crit.category == "developer_sentiment":
                source = "GitHub Org & Hacker News (Rows 40-41)"
                hn_hits = dev.get("hn_discussions", [])
                repo_cnt = dev.get("repo_count", 0)
                if hn_hits:
                    strength = 0.75
                    evidence_text = f"Hacker News discussion: '{hn_hits[0]['title'][:70]}...'"
                elif repo_cnt > 0:
                    strength = 0.50
                    evidence_text = f"GitHub Org active: {repo_cnt}+ repos (Stack: {', '.join(dev.get('top_languages', [])[:3])})."
                else:
                    strength = 0.30
                    evidence_text = "Standard enterprise developer footprint."

            elif crit.category == "tenders":
                source = tenders.get("source", "Public Procurement News Feed")
                if tenders.get("active_tender_rfp"):
                    strength = tenders.get("confidence", 0.40)
                    top_t = tenders.get("notices", [{}])[0].get("title", "")
                    evidence_text = f"Public Procurement ({source}): '{top_t[:70]}...'"
                else:
                    strength = 0.20
                    evidence_text = "No active public IT tenders or RFPs detected."

            # Calculate Bayesian Log-Odds Increment
            delta_L = crit.weight * strength * math.log(crit.likelihood_ratio)
            current_log_odds += delta_L
            total_delta += delta_L

            evidence_list.append(SignalEvidence(
                signal_id=crit.signal_id,
                category=crit.category,
                strength=round(strength, 2),
                log_odds_delta=round(delta_L, 3),
                score_points_awarded=0.0,
                evidence_text=evidence_text,
                source=source,
                confidence=round(strength, 2)
            ))

        # Calibrated Probability & Final Score
        posterior_prob = 1.0 / (1.0 + math.exp(-current_log_odds))
        final_score = round(posterior_prob * 100.0, 1)

        # Distribute Score Points for exact attribution
        for ev in evidence_list:
            if total_delta > 0:
                ev.score_points_awarded = round(final_score * (ev.log_odds_delta / total_delta), 1)
            else:
                ev.score_points_awarded = 0.0

        # Determine Tier
        if final_score >= 75.0:
            tier = "Tier 1 - Hot (Immediate Outreach)"
        elif final_score >= 50.0:
            tier = "Tier 2 - Warm (Nurture / Monitor)"
        else:
            tier = "Cold / Low Fit"

        # Synthesize Evidence-Grounded Sales Pitch
        pitch = self._generate_tailored_pitch(sol, profile, evidence_list)

        return SolutionAlignment(
            solution_id=sol.solution_id,
            solution_name=sol.solution_name,
            alignment_score=final_score,
            tier=tier,
            is_disqualified=False,
            evidence_trail=evidence_list,
            tailored_pitch=pitch
        )

    def _generate_tailored_pitch(self, sol: SolutionSpec, profile: CompanyProfile, evidence: List[SignalEvidence]) -> str:
        hiring_snip = next((e.evidence_text for e in evidence if e.category == "ats_hiring" and e.strength > 0.3), "automation specialists")
        sec_snip = next((e.evidence_text for e in evidence if e.category == "security_osint" and e.strength > 0.4), "external perimeter exposures")
        
        template = sol.value_proposition_template
        pitch = template.replace("{company}", profile.name)
        pitch = pitch.replace("{hiring_evidence}", hiring_snip)
        pitch = pitch.replace("{security_evidence}", sec_snip)
        return pitch
