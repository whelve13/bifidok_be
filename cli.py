import argparse
import sys
import os
import json

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

from backend.engine.bmaa_scorer import BMAAScorer
from backend.connectors.firmographics import resolve_company_entity
from backend.connectors.financials import fetch_financial_signals
from backend.connectors.news import fetch_company_news, evaluate_news_relevance
from backend.connectors.security import analyze_security_posture
from backend.connectors.ats import fetch_ats_hiring_signals
from backend.connectors.registries import verify_official_registry
from backend.connectors.developer import fetch_developer_signals
from backend.connectors.vulnerabilities import evaluate_vulnerability_exposure
from backend.connectors.tenders import fetch_public_procurement_tenders

console = Console(force_terminal=True, highlight=False)
last_analysis_result = None

def display_solutions():
    scorer = BMAAScorer()
    console.print(Panel.fit("[bold cyan]Orange Systems - Predefined Solutions Catalog[/bold cyan]", border_style="cyan"))
    table = Table(box=box.ASCII, show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Solution ID", style="dim", ratio=2)
    table.add_column("Solution Name", style="bold white", ratio=3)
    table.add_column("Target ICP Sectors", style="green", ratio=2)
    table.add_column("Key Signal Triggers", style="yellow", ratio=3)

    for sol in scorer.solutions:
        sectors = ", ".join(sol.target_icp.sectors[:3]) + "..."
        triggers = ", ".join([c.signal_id for c in sol.alignment_criteria])
        table.add_row(sol.solution_id, sol.solution_name, sectors, triggers)

    console.print(table)

def analyze_and_render(company_name: str, domain_hint: str = None):
    global last_analysis_result
    console.print(f"\n[bold cyan]>>> Fetching data from catalog endpoints for '{company_name}'...[/bold cyan]")
    scorer = BMAAScorer()
    result = scorer.analyze_company(company_name, domain_hint)
    last_analysis_result = result

    # 1. Company Profile Card
    comp = result.company
    profile_text = Text()
    profile_text.append(f"Entity: {comp.name} ({comp.legal_name or comp.name})\n", style="bold white")
    profile_text.append(f"Domain: {comp.domain}  |  Country: {comp.country}  |  Ticker: {comp.ticker or 'N/A'}\n", style="cyan")
    profile_text.append(f"Headcount: {comp.headcount:,}  |  Sector: {comp.sector}\n", style="yellow")
    if comp.description:
        profile_text.append(f"Summary: {comp.description}\n", style="italic dim")

    console.print(Panel(profile_text, title=f"[bold]Account Dossier: {comp.name}[/bold]", border_style="blue"))

    # 2. Ranked Solutions Alignment Table
    sol_table = Table(title="Multi-Solution Alignment Ranking (BMAA Engine)", box=box.ASCII, expand=True)
    sol_table.add_column("Rank", justify="center", style="bold", ratio=1)
    sol_table.add_column("Solution Offering", style="bold white", ratio=5)
    sol_table.add_column("Score", justify="right", ratio=2)
    sol_table.add_column("Tier & Readiness", ratio=4)

    for i, sol in enumerate(result.ranked_solutions, 1):
        score_val = f"{sol.alignment_score:.1f}%"
        if sol.alignment_score >= 75:
            score_style = "[bold green]" + score_val + "[/bold green]"
            tier_style = "[bold green]" + sol.tier + "[/bold green]"
        elif sol.alignment_score >= 50:
            score_style = "[bold yellow]" + score_val + "[/bold yellow]"
            tier_style = "[bold yellow]" + sol.tier + "[/bold yellow]"
        else:
            score_style = "[bold red]" + score_val + "[/bold red]"
            tier_style = "[dim]" + sol.tier + "[/dim]"

        sol_table.add_row(str(i), sol.solution_name, score_style, tier_style)

    console.print(sol_table)

    # 3. Top Recommendation Spotlight & Additive Explainability Waterfall
    top = result.best_solution
    if top:
        console.print(Panel(
            f"[bold green]RECOMMENDED OFFERING:[/bold green] [bold white]{top.solution_name}[/bold white]\n"
            f"[bold]Score:[/bold] {top.alignment_score:.1f}/100  |  [bold]Status:[/bold] {top.tier}",
            border_style="green"
        ))

        # Attribution Table
        attr_table = Table(title="Explainability Trail: Additive Signal Attribution", box=box.ASCII, expand=True)
        attr_table.add_column("Criteria / Signal", style="bold white", ratio=3)
        attr_table.add_column("Endpoint Source", style="dim", ratio=3)
        attr_table.add_column("Verifiable Evidence Discovered", style="italic", ratio=5)
        attr_table.add_column("Pts Awarded", justify="right", style="bold green", ratio=2)

        for ev in top.evidence_trail:
            pts_str = f"+{ev.score_points_awarded:.1f} pts" if ev.score_points_awarded > 0 else "0.0 pts"
            attr_table.add_row(ev.signal_id, ev.source, ev.evidence_text or "No active trigger", pts_str)

        console.print(attr_table)

        # 4. Tailored Sales Outreach Draft
        pitch_panel = Panel(
            f"[italic white]{top.tailored_pitch}[/italic white]",
            title="[bold magenta]Generated Value Proposition (Ready for HubSpot / InMail)[/bold magenta]",
            border_style="magenta"
        )
        console.print(pitch_panel)

    return result

def export_last_result():
    global last_analysis_result
    if not last_analysis_result:
        console.print("[bold red]No analysis result in memory to export. Run an analysis first![/bold red]")
        return
    
    output_filename = "analysis_output.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(last_analysis_result.model_dump(), f, indent=2)
    console.print(f"[bold green]Successfully exported analysis to {output_filename}[/bold green]")

def test_individual_connectors():
    console.print("\n[bold cyan]Select an Endpoint Connector to Test Individually:[/bold cyan]")
    console.print("  [1] Yahoo Finance & yfinance (Ticker, Margins, Headcount)")
    console.print("  [2] Google News RSS (DACH & Pan-EU Business Feeds)")
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

    company = Prompt.ask("Enter company name to test", default="Siemens")

    domain_default = company if "." in company else f"{company.lower().replace(' ', '')}.com"

    if choice == "1":
        console.print(f"[yellow]Querying Yahoo Finance for '{company}'...[/yellow]")
        fin = fetch_financial_signals(company)
        console.print_json(data=fin)
    elif choice == "2":
        console.print(f"[yellow]Querying Google News RSS for '{company}'...[/yellow]")
        news = fetch_company_news(company)
        console.print_json(data=news[:3] if news else [])
    elif choice == "3":
        console.print(f"[yellow]Scanning Public ATS Boards for '{company}'...[/yellow]")
        ats = fetch_ats_hiring_signals(company)
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
        console.print(f"[yellow]Scanning European Public IT Tenders for '{company}'...[/yellow]")
        tenders = fetch_public_procurement_tenders(company)
        console.print_json(data=tenders)

def interactive_menu():
    while True:
        console.print("\n" + "=" * 70)
        console.print(Panel.fit(
            "[bold white]Orange Systems - AI B2B Sales Intelligence Platform[/bold white]\n"
            "[dim]Bayesian Multi-Attribute Alignment Engine (BMAA)[/dim]",
            border_style="cyan"
        ))
        console.print("[bold yellow]MAIN MENU:[/bold yellow]")
        console.print("  [bold green][1][/bold green] Analyze Enterprise Account (Custom Input)")
        console.print("  [bold green][2][/bold green] Quick Account Presets (Siemens, Knorr-Bremse, N26, Zalando)")
        console.print("  [bold green][3][/bold green] View Predefined Solutions Catalog & Criteria")
        console.print("  [bold green][4][/bold green] Test Individual Catalog Connectors (Live APIs)")
        console.print("  [bold green][5][/bold green] Export Last Analysis Result to JSON (HubSpot Hook)")
        console.print("  [bold green][6][/bold green] Run Multi-Account Comparative Demo")
        console.print("  [bold red][0][/bold red] Exit")

        choice = Prompt.ask("\n[bold cyan]Select an option[/bold cyan]", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")

        if choice == "0":
            console.print("[bold cyan]Exiting Orange Systems Intelligence CLI. Goodbye![/bold cyan]")
            break
        elif choice == "1":
            comp_name = Prompt.ask("Enter target company name (e.g. Siemens, SAP, Airbus)")
            dom_hint = Prompt.ask("Enter domain hint (optional, press Enter to auto-resolve)", default="")
            analyze_and_render(comp_name, dom_hint if dom_hint.strip() else None)
        elif choice == "2":
            console.print("\n[bold yellow]Select a preset enterprise account:[/bold yellow]")
            console.print("  [1] Siemens AG (DAX 40 Industrials)")
            console.print("  [2] Knorr-Bremse AG (Manufacturing / Automation)")
            console.print("  [3] N26 Bank (Fintech / European Banking)")
            console.print("  [4] Zalando SE (DAX E-Commerce & Retail)")
            p_choice = Prompt.ask("Choose preset", choices=["1", "2", "3", "4"], default="1")
            presets = {
                "1": ("Siemens", "siemens.com"),
                "2": ("Knorr-Bremse", "knorr-bremse.com"),
                "3": ("N26 Bank", "n26.com"),
                "4": ("Zalando", "zalando.de")
            }
            comp_name, dom_hint = presets[p_choice]
            analyze_and_render(comp_name, dom_hint)
        elif choice == "3":
            display_solutions()
        elif choice == "4":
            test_individual_connectors()
        elif choice == "5":
            export_last_result()
        elif choice == "6":
            console.print(Panel.fit("[bold green]Running Multi-Account Demo (DACH & Pan-EU Accounts)[/bold green]"))
            demo_companies = [("Siemens", "siemens.com"), ("N26 Bank", "n26.com")]
            for c_name, c_dom in demo_companies:
                console.rule(f"[bold cyan]Analyzing {c_name}[/bold cyan]")
                analyze_and_render(c_name, c_dom)
                console.print("\n")

def main():
    parser = argparse.ArgumentParser(description="Orange Systems AI B2B Sales Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: menu
    subparsers.add_parser("menu", help="Launch interactive navigation menu")

    # Command: solutions
    subparsers.add_parser("solutions", help="List predefined solutions from JSON")

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a company and match solutions")
    analyze_parser.add_argument("--company", required=True, help="Company name (e.g. Siemens, Knorr-Bremse, N26)")
    analyze_parser.add_argument("--domain", required=False, default=None, help="Optional company domain hint")

    # Command: demo
    subparsers.add_parser("demo", help="Run end-to-end demo on European enterprise accounts")

    args = parser.parse_args()

    # If no subcommand passed, launch interactive menu by default
    if args.command is None or args.command == "menu":
        interactive_menu()
    elif args.command == "solutions":
        display_solutions()
    elif args.command == "analyze":
        analyze_and_render(args.company, args.domain)
    elif args.command == "demo":
        interactive_menu()

if __name__ == "__main__":
    main()
