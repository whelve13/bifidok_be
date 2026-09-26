import argparse
import sys
import os
import json
from typing import Optional, List, Dict, Any

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
from engine.offering_catalog import FLAGSHIP_OFFERINGS, decompose_custom_offering
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
        console.print("  [bold green][4][/bold green] Test Individual Live Data Connectors (With Product Keywords)")
        console.print("  [bold green][5][/bold green] Export Prospect Dossiers to JSON (HubSpot / CRM Ready)")
        console.print("  [bold red][0][/bold red] Exit")

        choice = Prompt.ask("\n[bold cyan]Select an option[/bold cyan]", choices=["0", "1", "2", "3", "4", "5"], default="1")

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
                custom_off = Prompt.ask("Enter what you want to sell (e.g. 'Warehouse Robotics', 'Commercial Solar Panels', 'Electric Delivery Vans')")
                prospect_and_render(custom_off)

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
            test_individual_connectors()
        elif choice == "5":
            export_last_result()

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

    args = parser.parse_args()

    if args.command is None or args.command == "menu":
        interactive_menu()
    elif args.command == "offerings":
        display_offerings_catalog()
    elif args.command == "prospect":
        prospect_and_render(args.offering)
    elif args.command == "evaluate":
        evaluate_single_account(args.company, args.offering, args.domain)

if __name__ == "__main__":
    main()

