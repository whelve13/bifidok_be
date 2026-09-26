import argparse
import sys
import os
import json
from typing import Any, Dict, List, Optional

# Add current directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Ensure UTF-8 stdout on Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from engine.prospecting_engine import CustomerProspectingEngine
from engine.offering_catalog import (
    FLAGSHIP_OFFERINGS,
    decompose_custom_offering,
    offering_dict_to_profile,
)
from engine.gemini_extractor import extract_signal_evidence, verify_verbatim_quote
from engine.scoring_service import (
    calculate_deterministic_score,
    compute_composite_3layer_score,
    record_lead_feedback,
    get_lead_feedback,
)
from models import PerfectCustomerDossier, ProspectingUniverseResult

from connectors.financials import fetch_financial_signals
from connectors.news import fetch_company_news
from connectors.security import analyze_security_posture
from connectors.ats import fetch_ats_hiring_signals
from connectors.registries import verify_official_registry
from connectors.developer import fetch_developer_signals
from connectors.vulnerabilities import evaluate_vulnerability_exposure
from connectors.tenders import fetch_public_procurement_tenders

console = Console(force_terminal=True, highlight=False)
last_prospecting_result: ProspectingUniverseResult = None
last_single_dossier: PerfectCustomerDossier = None

def display_offerings_catalog():
    console.print(Panel.fit(
        "[bold cyan]Orange Systems - Commercial Offerings & Buyer Persona Catalog[/bold cyan]\n"
        "[dim]Dynamic decomposition of products/services into operational wedges, buying signals, and ICP[/dim]",
        border_style="cyan"
    ))
    table = Table(box=box.ASCII, show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Offering ID", style="dim", ratio=2)
    table.add_column("Commercial Offering Title", style="bold white", ratio=3)
    table.add_column("Category & Physical Footprint", style="cyan", ratio=3)
    table.add_column("Operational Commercial Wedges", style="green", ratio=5)

    for off_id, off in FLAGSHIP_OFFERINGS.items():
        wedges_str = " • " + "\n • ".join([w.name for w in off.target_wedges])
        footprint_str = f"{off.category}\n[yellow]Physical Footprint Required: {'Yes' if off.requires_physical_presence else 'No'}[/yellow]"
        table.add_row(off.offering_id, off.title, footprint_str, wedges_str)

    console.print(table)

def render_customer_dossier(dossier: PerfectCustomerDossier):
    global last_single_dossier
    last_single_dossier = dossier

    comp = dossier.company
    wedge = dossier.primary_commercial_wedge
    breakdown = dossier.score_breakdown

    # 1. Company Profile Card
    profile_text = Text()
    profile_text.append(f"Entity: {comp.name} ({comp.legal_name or comp.name})\n", style="bold white")
    profile_text.append(f"Domain: {comp.domain}  |  Country: {comp.country}  |  Ticker: {comp.ticker or 'Private / Non-listed'}\n", style="cyan")
    profile_text.append(f"Headcount: {comp.headcount:,}  |  Sector: {comp.sector}  |  Solvency: {'Solvent & In Good Standing' if comp.is_solvent else 'INSOLVENT'}\n", style="yellow")
    if comp.description:
        profile_text.append(f"Overview: {comp.description}\n", style="italic dim")

    # Score Banner
    score_color = "bold green" if dossier.propensity_score >= 80 else ("bold yellow" if dossier.propensity_score >= 60 else "bold red")
    profile_text.append(f"\nBuying Propensity Score: ", style="bold white")
    profile_text.append(f"{dossier.propensity_score:.1f}%", style=score_color)
    profile_text.append(f"  |  Status: {dossier.tier}\n", style="bold cyan")

    console.print(Panel(profile_text, title=f"[bold]Account Dossier: {comp.name}[/bold]", border_style="blue"))

    # If disqualified, show reason and stop
    if dossier.is_disqualified:
        console.print(Panel(
            f"[bold red]DISQUALIFICATION NOTICE:[/bold red]\n{dossier.disqualification_reason}\n\n"
            f"[italic]{dossier.operational_rationale}[/italic]",
            border_style="red"
        ))
        return

    # 2. Multi-Dimensional Score Breakdown Waterfall
    score_table = Table(title="Multi-Dimensional Propensity & Fit Attribution", box=box.ASCII, expand=True)
    score_table.add_column("Evaluation Dimension", style="bold white", ratio=4)
    score_table.add_column("Maximum Points", justify="center", style="dim", ratio=2)
    score_table.add_column("Points Awarded", justify="right", style="bold green", ratio=2)
    score_table.add_column("Dimension Core Assessment", style="italic", ratio=5)

    score_table.add_row("Operational & Campus Fit", "35.0", f"{breakdown.operational_fit:.1f}", "Operational alignment with logistics, campus, or workforce archetype")
    score_table.add_row("Timing & Live Public Triggers", "30.0", f"{breakdown.timing_urgency:.1f}", "Real-time Google News RSS, ESG decarbonization mandates & tenders")
    score_table.add_row("Purchasing Power & Scale", "20.0", f"{breakdown.purchasing_scale:.1f}", "Enterprise headcount tier and financial operating margin")
    score_table.add_row("Hiring Intent & Receptivity", "15.0", f"{breakdown.hiring_intent:.1f}", "Active recruitment in fleet, logistics, sustainability, or operations")
    score_table.add_row("[bold]Composite Propensity Score[/bold]", "[bold]100.0[/bold]", f"[{score_color}]{breakdown.composite_score:.1f}%[/{score_color}]", f"[bold]{dossier.tier}[/bold]")
    console.print(score_table)

    # 3. Commercial Wedge Spotlight
    wedge_panel = Text()
    wedge_panel.append(f"Recommended Wedge: {wedge.name}\n", style="bold magenta")
    wedge_panel.append(f"Target Archetype: {wedge.target_archetype}\n", style="dim")
    wedge_panel.append(f"Commercial Value Driver: {wedge.value_driver}\n", style="bold green")
    wedge_panel.append(f"Estimated Commercial Potential: {dossier.estimated_commercial_scope}\n", style="bold yellow")
    wedge_panel.append(f"\nOperational Rationale: {dossier.operational_rationale}\n", style="italic white")
    console.print(Panel(wedge_panel, title="[bold]Strategic Commercial Wedge & Sizing[/bold]", border_style="magenta"))

    # 4. Verified Live Signal Citations
    if dossier.evidence_citations:
        ev_table = Table(title="Live Verified Evidence & Signal Provenance", box=box.ASCII, expand=True)
        ev_table.add_column("Signal Category", style="bold cyan", ratio=2)
        ev_table.add_column("Headline / Context", style="bold white", ratio=4)
        ev_table.add_column("Verbatim Citation & Snippet", style="italic", ratio=6)
        ev_table.add_column("Source", style="dim", ratio=2)
        ev_table.add_column("Impact", justify="right", style="green", ratio=1)

        for ev in dossier.evidence_citations:
            pts_str = f"+{ev.points_awarded:.1f} pts" if ev.points_awarded > 0 else "0.0 pts"
            ev_table.add_row(ev.category, ev.title, ev.snippet, ev.source, pts_str)

        console.print(ev_table)

    # 5. Target Buying Committee / Decision Maker Personas
    if dossier.target_buying_committee:
        dm_table = Table(title="Target Buying Committee & Executive Personas", box=box.ASCII, expand=True)
        dm_table.add_column("Executive Role / Title", style="bold yellow", ratio=3)
        dm_table.add_column("Department", style="cyan", ratio=2)
        dm_table.add_column("Core Mandate & Responsibilities", style="white", ratio=4)
        dm_table.add_column("Specific Outreach Hook", style="italic green", ratio=4)

        for dm in dossier.target_buying_committee:
            dm_table.add_row(dm.title, dm.department, dm.mandate, dm.outreach_hook)

        console.print(dm_table)

    # 6. Consultative Strategic Pitch Brief (NOT a spam email!)
    console.print(Panel(
        f"[white]{dossier.strategic_pitch_narrative}[/white]",
        title="[bold green]Executive Sales Intelligence Brief (For Account Executives)[/bold green]",
        border_style="green"
    ))

def prospect_and_render(offering_key_or_text: str):
    global last_prospecting_result
    engine = CustomerProspectingEngine()
    resolved_offering = engine._resolve_offering(offering_key_or_text)

    # Banner
    banner = Text()
    banner.append(f"TARGET COMMERCIAL OFFERING: {resolved_offering.title}\n", style="bold green")
    banner.append(f"Category: {resolved_offering.category}  |  Min Headcount: {resolved_offering.min_headcount:,}\n", style="cyan")
    banner.append(f"Description: {resolved_offering.description}\n", style="italic white")
    banner.append(f"Target Sectors: {', '.join(resolved_offering.target_sectors[:4])}...\n", style="yellow")
    console.print(Panel(banner, title="[bold]Autonomous Prospecting Search Launched[/bold]", border_style="cyan"))

    console.print(f"[bold cyan]>>> Scanning candidate universe and harvesting live multi-source signals...[/bold cyan]")
    universe_result = engine.prospect_universe(resolved_offering)
    last_prospecting_result = universe_result

    # Leaderboard Table
    lb_table = Table(
        title=f"Perfect Customer Leaderboard for '{resolved_offering.title}' ({universe_result.total_evaluated} Evaluated | {universe_result.tier1_count} Prime Targets)",
        box=box.ASCII,
        expand=True
    )
    lb_table.add_column("Rank", justify="center", style="bold", ratio=1)
    lb_table.add_column("Target Enterprise", style="bold white", ratio=3)
    lb_table.add_column("Propensity Score", justify="right", ratio=2)
    lb_table.add_column("Buying Intent Tier", ratio=3)
    lb_table.add_column("Recommended Commercial Wedge", style="cyan", ratio=4)
    lb_table.add_column("Headcount", justify="right", style="yellow", ratio=2)
    lb_table.add_column("Industry Sector", style="dim", ratio=3)

    for i, d in enumerate(universe_result.ranked_customers, 1):
        if d.is_disqualified:
            score_str = "[bold red]0.0%[/bold red]" if d.propensity_score == 0 else f"[bold red]{d.propensity_score:.1f}%[/bold red]"
            tier_str = f"[bold red]{d.tier}[/bold red]"
            wedge_str = f"[dim]{d.primary_commercial_wedge.name}[/dim]"
        elif d.propensity_score >= 80.0:
            score_str = f"[bold green]{d.propensity_score:.1f}%[/bold green]"
            tier_str = f"[bold green]{d.tier}[/bold green]"
            wedge_str = f"[bold green]{d.primary_commercial_wedge.name}[/bold green]"
        elif d.propensity_score >= 60.0:
            score_str = f"[bold yellow]{d.propensity_score:.1f}%[/bold yellow]"
            tier_str = f"[bold yellow]{d.tier}[/bold yellow]"
            wedge_str = f"[bold yellow]{d.primary_commercial_wedge.name}[/bold yellow]"
        else:
            score_str = f"[white]{d.propensity_score:.1f}%[/white]"
            tier_str = f"[dim]{d.tier}[/dim]"
            wedge_str = f"[dim]{d.primary_commercial_wedge.name}[/dim]"

        hc_str = f"{d.company.headcount:,}" if d.company.headcount else "N/A"
        lb_table.add_row(str(i), d.company.name, score_str, tier_str, wedge_str, hc_str, d.company.sector)

    console.print(lb_table)

    # Sub-menu to inspect dossiers
    while True:
        choice = Prompt.ask(
            "\nEnter Rank # (1-N) to open full Actionable Sales Dossier (or '0' to return to Main Menu)",
            default="1"
        )
        if choice == "0":
            break
        try:
            rank_idx = int(choice) - 1
            if 0 <= rank_idx < len(universe_result.ranked_customers):
                selected_dossier = universe_result.ranked_customers[rank_idx]
                console.rule(f"[bold green]Opening Dossier: {selected_dossier.company.name}[/bold green]")
                render_customer_dossier(selected_dossier)
            else:
                console.print("[red]Invalid rank number.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")

def evaluate_single_account(company_name: str, offering_input: str, domain_hint: str = None):
    console.print(f"\n[bold cyan]>>> Analyzing fit of '{company_name}' for '{offering_input}'...[/bold cyan]")
    engine = CustomerProspectingEngine()
    dossier = engine.analyze_single_prospect(company_name, offering_input, domain_hint)
    render_customer_dossier(dossier)
    return dossier

def export_last_result():
    global last_prospecting_result, last_single_dossier
    output_filename = "analysis_output.json"

    if last_prospecting_result:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(last_prospecting_result.model_dump(), f, indent=2)
        console.print(f"[bold green]Successfully exported {last_prospecting_result.total_evaluated} candidate dossiers to {output_filename}[/bold green]")
    elif last_single_dossier:
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(last_single_dossier.model_dump(), f, indent=2)
        console.print(f"[bold green]Successfully exported {last_single_dossier.company.name} dossier to {output_filename}[/bold green]")
    else:
        console.print("[bold red]No prospecting result in memory to export. Run a prospecting search first![/bold red]")

def test_individual_connectors():
    console.print("\n[bold cyan]Select an Endpoint Connector to Test Individually:[/bold cyan]")
    console.print("  [1] Yahoo Finance & yfinance (Ticker, Margins, Headcount)")
    console.print("  [2] Google News RSS (Dynamic Keywords & Signals)")
    console.print("  [3] Applicant Tracking Systems (Greenhouse, Lever, Personio)")
    console.print("  [4] Security OSINT & Perimeter Resilience (Headers & Subdomains)")
    console.print("  [5] Official EU Corporate Registries (French SIRENE & Norwegian Brreg)")
    console.print("  [6] Developer Velocity & Sentiment (GitHub Org & Hacker News)")
    console.print("  [7] CISA Known Exploited Vulnerabilities (1,720+ Weaponized CVEs)")
    console.print("  [8] European Public Procurement & Tenders (TED & OpenTender)")
    console.print("  [0] Back to Main Menu")

    choice = Prompt.ask("\nChoose connector", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")
    if choice == "0":
        return

    company = Prompt.ask("Enter company name to test", default="DHL Group")
    domain_default = company if "." in company else f"{company.lower().replace(' ', '')}.com"

    if choice == "1":
        console.print(f"[yellow]Querying Yahoo Finance for '{company}'...[/yellow]")
        fin = fetch_financial_signals(company)
        console.print_json(data=fin)
    elif choice == "2":
        kws = Prompt.ask("Enter search keywords (comma-separated)", default="fleet, cargo bike, net zero, logistics")
        kw_list = [k.strip() for k in kws.split(",")]
        console.print(f"[yellow]Querying Google News RSS for '{company}' with keywords {kw_list}...[/yellow]")
        news = fetch_company_news(company, kw_list)
        console.print_json(data=news[:3] if news else [])
    elif choice == "3":
        roles = Prompt.ask("Enter target roles (comma-separated)", default="Fleet Manager, Sustainability, Logistics")
        role_list = [r.strip() for r in roles.split(",")]
        console.print(f"[yellow]Scanning Public ATS Boards for '{company}'...[/yellow]")
        ats = fetch_ats_hiring_signals(company, role_list)
        console.print_json(data=ats)
    elif choice == "4":
        domain = Prompt.ask("Enter domain to audit", default=domain_default)
        console.print(f"[yellow]Auditing Security Headers & Subdomains for '{domain}'...[/yellow]")
        sec = analyze_security_posture(domain)
        console.print_json(data=sec)
    elif choice == "5":
        console.print(f"[yellow]Querying Official EU Registries for '{company}'...[/yellow]")
        reg = verify_official_registry(company)
        console.print_json(data=reg)
    elif choice == "6":
        console.print(f"[yellow]Fetching GitHub & Hacker News Sentiment for '{company}'...[/yellow]")
        dev = fetch_developer_signals(company)
        console.print_json(data=dev)
    elif choice == "7":
        domain = Prompt.ask("Enter domain to cross-reference with CISA KEV", default=domain_default)
        sec = analyze_security_posture(domain)
        console.print(f"[yellow]Cross-referencing subdomains with CISA KEV weaponized zero-days...[/yellow]")
        vulns = evaluate_vulnerability_exposure(sec.get("exposed_subdomains", []))
        console.print_json(data=vulns)
    elif choice == "8":
        tender_kws = Prompt.ask("Enter tender keywords", default="fleet, mobility, leasing, transport")
        tk_list = [k.strip() for k in tender_kws.split(",")]
        console.print(f"[yellow]Scanning European Public Tenders for '{company}'...[/yellow]")
        tenders = fetch_public_procurement_tenders(company, tk_list)
        console.print_json(data=tenders)

def render_gnn_prediction(company_name: str):
    from gnn.inference import HTGNNInferenceEngine
    console.print(f"\n[bold magenta]>>> Executing HT-GNN Neural Message-Passing for '{company_name}'...[/bold magenta]")
    engine = HTGNNInferenceEngine()
    pred = engine.predict_account(company_name)

    score_style = "bold green" if pred["overall_readiness_score"] >= 70 else ("bold yellow" if pred["overall_readiness_score"] >= 45 else "bold red")
    summary = Text()
    summary.append(f"Target Account: {pred['company_name']}\n", style="bold white")
    summary.append(f"HT-GNN Buying Readiness Score: ", style="bold white")
    summary.append(f"{pred['overall_readiness_score']}/100", style=score_style)
    summary.append(f"  |  Tier: {pred['tier']}\n", style="cyan")
    summary.append(f"Recommended Solution: {pred['best_solution']}\n", style="bold yellow")
    console.print(Panel(summary, title="[bold]HT-GNN Graph Intent Prediction[/bold]", border_style="magenta"))

    table = Table(title="Multi-Relational Ecosystem Influences", box=box.ASCII, expand=True)
    table.add_column("Relation Type", style="bold cyan", ratio=2)
    table.add_column("Connected Entities & Signals", style="white", ratio=6)

    comp_list = ", ".join([f"{c['name']} ({'Active Buyer' if c['buyer_label'] else 'Peer'})" for c in pred["ecosystem_attribution"]["competitors"][:3]])
    tech_list = ", ".join(pred["ecosystem_attribution"]["technologies"][:4])
    reg_list = ", ".join(pred["ecosystem_attribution"]["regulations"][:3])

    table.add_row("Competitor Contagion", comp_list or "No direct sector rivals in immediate graph neighborhood")
    table.add_row("Technology Stack", tech_list or "Standard enterprise infrastructure")
    table.add_row("Regulatory Mandates", reg_list or "Baseline corporate standards")
    console.print(table)
    console.print(Panel(pred["grounded_pitch"], title="[bold green]Graph-Grounded Value Proposition[/bold green]", border_style="green"))


def render_3layer_hybrid_scoring(target_company: Optional[str] = None):
    console.print("\n" + "=" * 75)
    console.print(Panel.fit(
        "[bold cyan]3-Layer Hybrid Brain Pipeline[/bold cyan]\n"
        "[dim]Layer 1: Gemini AI Signal Extraction • Layer 2: Annex 4.2 Deterministic Formula • Layer 3: PyG HT-GNN Graph[/dim]",
        border_style="cyan"
    ))

    if not target_company:
        target_company = Prompt.ask("Enter company name to analyze", default="DHL Group")

    console.print("\n[bold yellow]Select Intelligence Scenario to evaluate:[/bold yellow]")
    console.print("  [bold green][1][/bold green] Agentic Automation & RPA Squads [dim](Strategy 2030, back-office overhead)[/dim]")
    console.print("  [bold green][2][/bold green] Managed SOC & NIS2 Cyber Resilience [dim](Perimeter vulnerabilities, compliance)[/dim]")
    console.print("  [bold green][3][/bold green] Cloud Legacy Modernization & AI Engineering [dim](AWS/Kubernetes architecture)[/dim]")
    console.print("  [bold green][4][/bold green] Disqualification Stress-Test [dim](Tests insolvency / liquidation exclusion rules)[/dim]")
    console.print("  [bold green][5][/bold green] Live News Ingestion [dim](Fetches live Google News RSS and extracts verbatim signals)[/dim]")
    console.print("  [bold green][6][/bold green] Custom Document Text & Signal Question [dim](Paste custom text)[/dim]")

    sc_choice = Prompt.ask("Choose scenario", choices=["1", "2", "3", "4", "5", "6"], default="1")

    # Build scenario data
    if sc_choice == "1":
        passage = (
            f"{target_company} announced the expansion of its Strategy 2030 digital roadmap, "
            f"deploying agentic AI squads and RPA workflows to streamline logistics hub operations "
            f"and reduce back-office administrative bottlenecks."
        )
        question = "Is the company deploying agentic process automation or RPA workflows?"
        guidance = "Look for Strategy 2030, RPA, workflow automation, agentic AI, digital roadmap."
        rules = [
            {"id": "r1", "question": question, "weight": "HIGH", "is_negative": False},
            {"id": "r2", "question": "Are they hiring software engineers?", "weight": "MEDIUM", "is_negative": False}
        ]
    elif sc_choice == "2":
        passage = (
            f"Facing imminent enforcement deadlines under the EU NIS2 Directive, {target_company} "
            f"has initiated an urgent review of perimeter cybersecurity controls and critical infrastructure vulnerabilities."
        )
        question = "Is the company subject to NIS2 compliance deadlines or seeking Managed SOC capabilities?"
        guidance = "Look for NIS2, DORA, cybersecurity audit, Managed SOC, perimeter vulnerability."
        rules = [
            {"id": "r1", "question": question, "weight": "HIGH", "is_negative": False},
            {"id": "r2", "question": "Active critical vulnerabilities detected?", "weight": "MEDIUM", "is_negative": False}
        ]
    elif sc_choice == "3":
        passage = (
            f"In its latest technology disclosure, {target_company} detailed plans to migrate core legacy systems "
            f"to AWS Cloud and Kubernetes clusters to accelerate software delivery cycles."
        )
        question = "Is the company actively migrating legacy platforms to modern cloud infrastructure?"
        guidance = "Look for AWS, Azure, cloud migration, legacy modernization, Kubernetes."
        rules = [
            {"id": "r1", "question": question, "weight": "HIGH", "is_negative": False}
        ]
    elif sc_choice == "4":
        passage = (
            f"According to commercial court registry filings, {target_company} has entered preliminary insolvency proceedings "
            f"and appointed an administrator to oversee debt restructuring."
        )
        question = "Is the company undergoing insolvency, bankruptcy, or debt liquidation?"
        guidance = "Check for bankruptcy, insolvency administrator, liquidation proceedings."
        rules = [
            {"id": "r_disq", "question": question, "weight": "DISQUALIFY", "is_negative": True}
        ]
    elif sc_choice == "5":
        console.print(f"[yellow]Fetching real-time public news for {target_company}...[/yellow]")
        news_items = fetch_company_news(target_company, ["digital", "automation", "strategy", "expansion", "cloud"])
        if news_items:
            passage = f"{news_items[0]['title']}. {news_items[0]['snippet']}"
            console.print(f"[dim]Harvested Article: {news_items[0]['title']}[/dim]")
        else:
            passage = f"{target_company} announced strategic operational investments in digital modernization and fleet efficiency."
        question = f"Does the text indicate active transformation, expansion, or technology procurement at {target_company}?"
        guidance = "Identify corporate investment, expansion, digital projects, or new contracts."
        rules = [
            {"id": "r_news", "question": question, "weight": "HIGH", "is_negative": False}
        ]
    else:
        passage = Prompt.ask("Enter raw text passage")
        question = Prompt.ask("Enter signal question to verify")
        guidance = Prompt.ask("Enter guidance notes", default="Extract direct verbatim evidence.")
        rules = [
            {"id": "r_custom", "question": question, "weight": "HIGH", "is_negative": False}
        ]

    # -------------------------------------------------------------
    # LAYER 1: GOOGLE AI STUDIO GEMINI SIGNAL EXTRACTION
    # -------------------------------------------------------------
    console.print(f"\n[bold cyan]>>> [Layer 1] Running Gemini Structured Extraction & Verbatim Assertion...[/bold cyan]")
    with console.status("[bold green]Querying Gemini & verifying verbatim anti-hallucination guardrail...[/bold green]"):
        l1_result = extract_signal_evidence(raw_passage=passage, question=question, guidance=guidance)

    l1_panel = Text()
    l1_panel.append(f"Question: {question}\n", style="bold white")
    l1_panel.append("Signal Detected: ", style="bold white")
    l1_panel.append(f"{'CONFIRMED' if l1_result['detected'] else 'NOT DETECTED'}\n", style="bold green" if l1_result['detected'] else "bold red")
    l1_panel.append(f"Confidence: {l1_result['confidence']:.2f}\n", style="cyan")
    if l1_result['evidence_quote']:
        l1_panel.append(f'Verbatim Quote: "{l1_result["evidence_quote"]}"\n', style="italic yellow")
        l1_panel.append("Anti-Hallucination Guardrail: [PASS] Verbatim match confirmed in source text\n", style="bold green")
    else:
        l1_panel.append("Evidence Quote: (None / Empty)\n", style="dim")
    l1_panel.append(f"Reasoning: {l1_result['reasoning']}\n", style="dim white")
    console.print(Panel(l1_panel, title="[bold]Layer 1: Grounded Evidence Extraction[/bold]", border_style="cyan"))

    # -------------------------------------------------------------
    # LAYER 2 & 3: COMPOSITE 3-LAYER SYNTHESIS (ANNEX 4.2 + HT-GNN)
    # -------------------------------------------------------------
    console.print(f"[bold magenta]>>> [Layer 2 & 3] Computing Annex 4.2 Deterministic Score & PyG HT-GNN Inference...[/bold magenta]")
    
    evaluations = [
        {
            "rule_id": rules[0]["id"],
            "detected": l1_result["detected"],
            "confidence": l1_result["confidence"],
            "evidence_quote": l1_result["evidence_quote"],
            "reasoning": l1_result["reasoning"],
            "weight": rules[0]["weight"],
            "is_negative": rules[0]["is_negative"],
        }
    ]

    with console.status("[bold magenta]Running Graph Neural Message-Passing on multi-relational ecosystem...[/bold magenta]"):
        composite = compute_composite_3layer_score(
            company_name=target_company,
            domain=f"{target_company.lower().replace(' ', '')}.com",
            evaluations=evaluations,
            rules=rules
        )

    # Layer 2 Breakdown
    l2_table = Table(title="Layer 2: Annex 4.2 Deterministic Score Formula", box=box.ASCII, expand=True)
    l2_table.add_column("Formula Component", style="bold white", ratio=3)
    l2_table.add_column("Value / Status", style="bold cyan", ratio=3)
    l2_table.add_column("Calculation Rule", style="italic dim", ratio=5)

    l2_table.add_row("Signal Weight", str(rules[0]["weight"]), "HIGH=35 | MEDIUM=20 | LOW=10")
    l2_table.add_row("Detection Confidence", f"{l1_result['confidence']:.2f}", "0.0 - 1.0 extraction confidence")
    l2_table.add_row("Disqualification Status", "[bold red]DISQUALIFIED[/bold red]" if composite["is_disqualified"] else "[bold green]ELIGIBLE[/bold green]", "Triggered if weight=='DISQUALIFY' and C >= 0.80")
    if composite["is_disqualified"]:
        l2_table.add_row("Disqualification Reason", str(composite["disqualification_reason"]), "Outreach generation locked")
    l2_table.add_row("Layer 2 Score (S_det)", f"{composite['deterministic_score']}/100", "Bounded in [0, 100]")
    console.print(l2_table)

    # Layer 3 Breakdown
    l3_table = Table(title="Layer 3: PyG Heterogeneous Temporal Graph (HT-GNN)", box=box.ASCII, expand=True)
    l3_table.add_column("Graph Relation", style="bold magenta", ratio=3)
    l3_table.add_column("Ecosystem Ripple Attribution", style="white", ratio=8)

    expl = composite.get("ecosystem_attribution", {})
    comp_str = ", ".join([c["name"] for c in expl.get("competitors", [])[:3]]) or "Industry peer baseline"
    tech_str = ", ".join(expl.get("technologies", [])[:4]) or "Standard enterprise infrastructure"
    reg_str = ", ".join(expl.get("regulations", [])[:3]) or "Standard EU regulations"

    l3_table.add_row("Competitor Contagion", comp_str)
    l3_table.add_row("Enterprise Tech Stack", tech_str)
    l3_table.add_row("Regulatory Pressures", reg_str)
    l3_table.add_row("HT-GNN Score (S_graph)", f"{composite['graph_readiness_score']:.1f}/100")
    console.print(l3_table)

    # Final Composite Banner
    final_score = composite["composite_score"]
    score_style = "bold green" if final_score >= 70 else ("bold yellow" if final_score >= 45 else "bold red")
    
    synth_text = Text()
    synth_text.append(f"Target Account: {composite['company_name']} ({composite['domain']})\n", style="bold white")
    synth_text.append(f"Deterministic Score (70%): {composite['deterministic_score']}  |  Graph Score (30%): {composite['graph_readiness_score']:.1f}\n", style="dim")
    synth_text.append("Final 3-Layer Composite Score: ", style="bold white")
    synth_text.append(f"{final_score}/100\n", style=score_style)
    if composite["is_disqualified"]:
        synth_text.append(f"Status: DISQUALIFIED - {composite['disqualification_reason']}\n", style="bold red")
    else:
        synth_text.append(f"Status: {composite.get('tier') or 'Qualified Lead'}\n", style="bold cyan")
        synth_text.append(f"Best Solution Fit: {composite.get('best_solution') or 'Enterprise Transformation'}\n", style="bold yellow")
    
    console.print(Panel(synth_text, title="[bold]Composite 3-Layer Hybrid Score Breakdown[/bold]", border_style="green" if not composite["is_disqualified"] else "red"))

    if composite.get("grounded_pitch"):
        console.print(Panel(composite["grounded_pitch"], title="[bold green]Executive Sales Pitch (Grounded in Layer 1-3)[/bold green]", border_style="green"))

    # Human-in-the-loop Calibration
    feedback_choice = Prompt.ask("\n[bold yellow]Record validation feedback for scoring calibration? (y/n)[/bold yellow]", choices=["y", "n"], default="y")
    if feedback_choice == "y":
        is_acc = Prompt.ask("Was this score assessment accurate?", choices=["y", "n"], default="y") == "y"
        notes = Prompt.ask("Calibration notes (optional)", default="")
        rec = record_lead_feedback(
            lead_id=f"lead_{target_company.lower().replace(' ', '_')}",
            is_accurate=is_acc,
            notes=notes
        )
        console.print(f"[bold green][OK] Feedback successfully logged with ID: {rec['feedback_id']} (stored in data/lead_feedback.jsonl)[/bold green]")


def render_compiled_rules_table(compiled: Dict[str, Any]):
    console.print(Panel.fit(
        f"[bold cyan]Compiled Commercial Offering Draft: {compiled.get('offering_name', 'Custom Offering')}[/bold cyan]\n"
        f"[dim]{compiled.get('description', '')}[/dim]",
        border_style="cyan"
    ))

    table = Table(title="Configured Signal Rules & Weights", box=box.ASCII, expand=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Signal Question / Business Criterion", style="bold white", ratio=5)
    table.add_column("Guidance Notes", style="dim", ratio=3)
    table.add_column("Weight", style="bold yellow", ratio=2)
    table.add_column("Polarity", style="cyan", ratio=2)

    for idx, rule in enumerate(compiled.get("signal_rules", []), start=1):
        weight = rule.get("weight", "MEDIUM")
        weight_style = "bold red" if weight == "DISQUALIFY" else ("bold green" if weight == "HIGH" else "yellow")
        polarity = "[red]Negative[/red]" if rule.get("is_negative") else "[green]Positive[/green]"
        table.add_row(
            str(idx),
            rule.get("question", ""),
            rule.get("guidance_notes", ""),
            f"[{weight_style}]{weight}[/{weight_style}]",
            polarity
        )
    console.print(table)


def run_custom_offering_workflow(initial_prompt: Optional[str] = None):
    """
    Prompts user for commercial mandate, displays compiled draft rules and weights,
    presents interactive edit step, and runs autonomous prospecting scan.
    """
    if initial_prompt and initial_prompt.strip():
        user_input = initial_prompt.strip()
    else:
        user_input = Prompt.ask(
            "\n[bold yellow]What product, service, or commercial mandate do you want to sell?[/bold yellow]\n"
            "[dim](e.g. 'Warehouse Robotics', 'Commercial Solar Panels', 'Electric Delivery Vans')[/dim]\n"
            "Enter product/service"
        )

    if not user_input.strip():
        console.print("[red]No product or service entered. Returning to menu.[/red]")
        return

    console.print(f"\n[bold cyan]>>> Compiling custom offering specification for '{user_input}'...[/bold cyan]")
    compiled = decompose_custom_offering(user_input)

    while True:
        console.print()
        render_compiled_rules_table(compiled)

        console.print("\n[bold yellow]Interactive Custom Offering Configurator:[/bold yellow]")
        console.print("  [bold green][1][/bold green] Confirm & Run")
        console.print("  [bold green][2][/bold green] Edit Weights")
        console.print("  [bold green][3][/bold green] Add/Edit Signal Questions")
        console.print("  [bold red][0][/bold red] Cancel")

        step = Prompt.ask("Select action", choices=["0", "1", "2", "3"], default="1")

        if step == "0":
            console.print("[yellow]Custom offering compilation cancelled.[/yellow]")
            return
        elif step == "1":
            console.print("\n[bold green]Configuration confirmed! Launching autonomous customer prospecting...[/bold green]")
            profile = offering_dict_to_profile(compiled)
            prospect_and_render(profile)
            break
        elif step == "2":
            num_rules = len(compiled.get("signal_rules", []))
            if num_rules == 0:
                console.print("[red]No signal rules to edit.[/red]")
                continue
            rule_num = Prompt.ask(
                f"Enter rule # to update weight (1-{num_rules})",
                choices=[str(i) for i in range(1, num_rules + 1)]
            )
            idx = int(rule_num) - 1
            curr_weight = compiled["signal_rules"][idx].get("weight", "MEDIUM")
            new_weight = Prompt.ask(
                f"Select new weight for Rule #{rule_num} (current: {curr_weight})",
                choices=["HIGH", "MEDIUM", "LOW", "DISQUALIFY"],
                default=curr_weight
            )
            compiled["signal_rules"][idx]["weight"] = new_weight
            console.print(f"[bold green]Rule #{rule_num} weight updated to {new_weight}.[/bold green]")
        elif step == "3":
            num_rules = len(compiled.get("signal_rules", []))
            edit_action = Prompt.ask(
                "Choose question operation: [1] Edit existing question | [2] Add new question",
                choices=["1", "2"],
                default="1"
            ) if num_rules > 0 else "2"

            if edit_action == "1" and num_rules > 0:
                rule_choice = Prompt.ask(
                    f"Enter rule # to edit (1-{num_rules})",
                    choices=[str(i) for i in range(1, num_rules + 1)]
                )
                idx = int(rule_choice) - 1
                curr_q = compiled["signal_rules"][idx].get("question", "")
                curr_notes = compiled["signal_rules"][idx].get("guidance_notes", "")
                new_q = Prompt.ask("Enter updated signal question", default=curr_q)
                new_notes = Prompt.ask("Enter updated guidance notes", default=curr_notes)
                compiled["signal_rules"][idx]["question"] = new_q
                compiled["signal_rules"][idx]["guidance_notes"] = new_notes
                console.print(f"[bold green]Rule #{rule_choice} updated.[/bold green]")
            else:
                new_q = Prompt.ask("Enter new signal question")
                new_notes = Prompt.ask("Enter guidance notes for evidence extraction", default="")
                new_weight = Prompt.ask("Select rule weight", choices=["HIGH", "MEDIUM", "LOW", "DISQUALIFY"], default="HIGH")
                is_neg_str = Prompt.ask("Is this a negative signal (penalizes score)?", choices=["y", "n"], default="n")
                compiled["signal_rules"].append({
                    "question": new_q,
                    "guidance_notes": new_notes,
                    "weight": new_weight,
                    "is_negative": (is_neg_str.lower() == "y"),
                })
                console.print("[bold green]New signal question added successfully.[/bold green]")


def interactive_menu():
    while True:
        console.print("\n" + "=" * 75)
        console.print(Panel.fit(
            "[bold white]Orange Systems - Autonomous Customer Prospecting & Buying Intent Engine[/bold white]\n"
            "[dim]Dynamic Offering Decomposer • Multi-Source Evidence Harvesting • Actionable Sales Dossiers[/dim]",
            border_style="cyan"
        ))
        console.print("[bold yellow]MAIN MENU:[/bold yellow]")
        console.print("  [bold green][1][/bold green] Find Perfect Customers for an Offering (e.g. Bikes, Automation, Cyber, Custom)")
        console.print("  [bold green][2][/bold green] Deep-Dive Single Enterprise Fit for an Offering (e.g. Test DHL, Siemens, Zalando for Bikes)")
        console.print("  [bold green][3][/bold green] Explore Commercial Offerings & Intelligent Operational Wedges")
        console.print("  [bold green][4][/bold green] Custom Commercial Offering (Interactive Rule Configurator & Prospecting)")
        console.print("  [bold green][5][/bold green] Test Individual Live Data Connectors (With Product Keywords)")
        console.print("  [bold green][6][/bold green] Export Prospect Dossiers to JSON (HubSpot / CRM Ready)")
        console.print("  [bold green][7][/bold green] Run HT-GNN Graph Intelligence & Ecosystem Ripple Analysis")
        console.print("  [bold green][8][/bold green] 3-Layer Hybrid Brain (Gemini LLM + Annex Formula + PyG HT-GNN)")
        console.print("  [bold red][0][/bold red] Exit")

        choice = Prompt.ask("\n[bold cyan]Select an option[/bold cyan]", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"], default="1")

        if choice == "0":
            console.print("[bold cyan]Exiting Orange Systems Intelligence CLI. Goodbye![/bold cyan]")
            break
        elif choice == "1":
            console.print("\n[bold yellow]Select a Commercial Offering to find customers for:[/bold yellow]")
            console.print("  [bold green][1][/bold green] Commercial E-Bike Fleets & Cargo Bicycles [dim](Orange's New Offering: Urban delivery, campus transit, JobRad)[/dim]")
            console.print("  [bold green][2][/bold green] Agentic Process Automation & AI Workforce [dim](Back-office overhead & process mining)[/dim]")
            console.print("  [bold green][3][/bold green] Managed SOC & NIS2/DORA Cyber Resilience [dim](Perimeter compliance & 24/7 SOC)[/dim]")
            console.print("  [bold green][4][/bold green] Custom Commercial Offering [dim](Type ANY product or service you want to sell)[/dim]")

            off_choice = Prompt.ask("Choose offering", choices=["1", "2", "3", "4"], default="1")
            if off_choice == "1":
                prospect_and_render("commercial_bikes")
            elif off_choice == "2":
                prospect_and_render("agentic_automation")
            elif off_choice == "3":
                prospect_and_render("managed_soc")
            elif off_choice == "4":
                run_custom_offering_workflow()

        elif choice == "2":
            comp_name = Prompt.ask("Enter company name to evaluate (e.g. DHL Group, BASF, Siemens, Zalando)")
            dom_hint = Prompt.ask("Enter domain hint (optional, press Enter to auto-resolve)", default="")

            console.print("\n[bold yellow]Select the Commercial Offering to evaluate against:[/bold yellow]")
            console.print("  [1] Commercial E-Bike Fleets & Cargo Bicycles")
            console.print("  [2] Agentic Process Automation & AI Workforce")
            console.print("  [3] Managed SOC & NIS2 Cyber Resilience")
            console.print("  [4] Custom Offering Text")
            o_choice = Prompt.ask("Choose offering", choices=["1", "2", "3", "4"], default="1")

            off_map = {
                "1": "commercial_bikes",
                "2": "agentic_automation",
                "3": "managed_soc"
            }
            if o_choice == "4":
                offering_str = Prompt.ask("Enter offering text")
            else:
                offering_str = off_map[o_choice]

            evaluate_single_account(comp_name, offering_str, dom_hint if dom_hint.strip() else None)

        elif choice == "3":
            display_offerings_catalog()
        elif choice == "4":
            run_custom_offering_workflow()
        elif choice == "5":
            test_individual_connectors()
        elif choice == "6":
            export_last_result()
        elif choice == "7":
            comp_name = Prompt.ask("Enter company name for HT-GNN Graph Analysis", default="Knorr-Bremse")
            render_gnn_prediction(comp_name)
        elif choice == "8":
            comp_name = Prompt.ask("Enter company name for 3-Layer Hybrid Brain Analysis", default="DHL Group")
            render_3layer_hybrid_scoring(comp_name)

def main():
    parser = argparse.ArgumentParser(description="Orange Systems Autonomous Customer Prospecting CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: menu
    subparsers.add_parser("menu", help="Launch interactive navigation menu")

    # Command: offerings
    subparsers.add_parser("offerings", help="List commercial offerings and buyer archetypes")

    # Command: prospect
    prospect_parser = subparsers.add_parser("prospect", help="Prospect and rank perfect customers for an offering")
    prospect_parser.add_argument("--offering", required=False, default="commercial_bikes", help="Offering key or description (e.g. 'commercial_bikes', 'Bikes', 'Automation')")

    # Command: evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Deep-dive account fit for an offering")
    eval_parser.add_argument("--company", required=True, help="Target company name (e.g. DHL Group, Siemens, Zalando)")
    eval_parser.add_argument("--offering", required=False, default="commercial_bikes", help="Offering name (default: commercial_bikes)")
    eval_parser.add_argument("--domain", required=False, default=None, help="Optional domain hint")

    # Command: gnn
    gnn_parser = subparsers.add_parser("gnn", help="Run HT-GNN graph neural prediction on an account")
    gnn_parser.add_argument("--company", required=True, help="Company name (e.g. Knorr-Bremse, Siemens, Lufthansa Group)")

    # Command: 3layer
    layer3_parser = subparsers.add_parser("3layer", help="Run 3-Layer Hybrid Brain (Gemini + Annex 4.2 + PyG HT-GNN)")
    layer3_parser.add_argument("--company", required=False, default="DHL Group", help="Company name (e.g. DHL Group, BASF, Siemens)")

    # Command: custom
    custom_parser = subparsers.add_parser("custom", help="Compile and edit a custom commercial offering interactively")
    custom_parser.add_argument("--offering", required=False, default=None, help="Initial product or service description")

    args = parser.parse_args()

    if args.command is None or args.command == "menu":
        interactive_menu()
    elif args.command == "offerings":
        display_offerings_catalog()
    elif args.command == "prospect":
        prospect_and_render(args.offering)
    elif args.command == "evaluate":
        evaluate_single_account(args.company, args.offering, args.domain)
    elif args.command == "gnn":
        render_gnn_prediction(args.company)
    elif args.command == "3layer":
        render_3layer_hybrid_scoring(args.company)
    elif args.command == "custom":
        run_custom_offering_workflow(args.offering)

if __name__ == "__main__":
    main()

