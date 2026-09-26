import argparse
import sys
import os
import json
from typing import Any, Dict, List, Optional

# Add current directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

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
from models import PerfectCustomerDossier, ProspectingUniverseResult

from connectors.financials import fetch_financial_signals
from connectors.news import fetch_company_news
from connectors.ats import fetch_ats_hiring_signals
from connectors.security import analyze_security_posture
from connectors.registries import verify_official_registry
from connectors.developer import fetch_developer_signals
from connectors.vulnerabilities import evaluate_vulnerability_exposure
from connectors.tenders import fetch_public_procurement_tenders

console = Console()
engine = CustomerProspectingEngine()
LAST_RESULTS: Optional[ProspectingUniverseResult] = None

def display_offerings_catalog():
    table = Table(title="[bold cyan]Orange Systems Commercial Offerings Catalog[/bold cyan]", box=box.ROUNDED)
    table.add_column("Key", style="bold green")
    table.add_column("Title", style="bold white")
    table.add_column("Category", style="cyan")
    table.add_column("Primary Commercial Wedges", style="yellow")
    table.add_column("Target Sectors", style="magenta")

    for key, off in FLAGSHIP_OFFERINGS.items():
        wedges = "\n".join([f"• {w.name}" for w in off.target_wedges[:3]])
        sectors = ", ".join(off.target_sectors[:3])
        table.add_row(key, off.title, off.category, wedges, sectors)

    console.print(table)

def render_dossier(dossier: PerfectCustomerDossier, rank: int = 1):
    score = dossier.propensity_score
    if score >= 75:
        score_color = "bold green"
    elif score >= 50:
        score_color = "bold yellow"
    else:
        score_color = "bold red"

    # Header Panel
    header_text = Text()
    header_text.append(f"#{rank}  {dossier.company.name} ({dossier.company.domain})\n", style="bold white")
    header_text.append(f"Sector: {dossier.company.sector}  |  Headcount: {dossier.company.headcount or 'Unknown'}  |  Country: {dossier.company.country}\n", style="dim")
    header_text.append(f"Propensity Score: ", style="bold")
    header_text.append(f"{dossier.propensity_score:.1f}/100", style=score_color)
    header_text.append(f"  [{dossier.tier}]\n", style="bold cyan")
    header_text.append(f"Commercial Wedge: ", style="bold")
    header_text.append(f"{dossier.primary_commercial_wedge.name}\n", style="bold yellow")
    header_text.append(f"Wedge Value Driver: {dossier.primary_commercial_wedge.value_driver}", style="italic")

    border_color = "green" if score >= 70 else ("yellow" if score >= 50 else "red")
    console.print(Panel(header_text, title=f"[bold]Account Dossier - {dossier.company.name}[/bold]", border_style=border_color))

    # Operational Rationale
    console.print(f"[bold cyan]Operational Rationale:[/bold cyan] {dossier.operational_rationale}")
    console.print(f"[bold cyan]Estimated Scope:[/bold cyan] {dossier.estimated_commercial_scope}\n")

    # Score Breakdown Table
    bd = dossier.score_breakdown
    sb_table = Table(title="Intent & Readiness Score Matrix", box=box.SIMPLE, show_header=True)
    sb_table.add_column("Dimension", style="bold")
    sb_table.add_column("Weight Max", justify="right")
    sb_table.add_column("Points Awarded", justify="right", style="green")

    sb_table.add_row("Operational Fit", "35.0", f"{bd.operational_fit:.1f}")
    sb_table.add_row("Timing & Trigger Urgency", "30.0", f"{bd.timing_urgency:.1f}")
    sb_table.add_row("Purchasing Scale & Solvency", "20.0", f"{bd.purchasing_scale:.1f}")
    sb_table.add_row("Hiring Intent & Tech Capacity", "15.0", f"{bd.hiring_intent:.1f}")
    sb_table.add_row("[bold]Composite Propensity Score[/bold]", "[bold]100.0[/bold]", f"[bold]{bd.composite_score:.1f}[/bold]")
    console.print(sb_table)

    # Harvested Evidence Citations
    if dossier.evidence_citations:
        ev_table = Table(title="Harvested Multi-Source Evidence", box=box.HORIZONTALS)
        ev_table.add_column("Category", style="cyan", width=16)
        ev_table.add_column("Finding / Evidence Snippet", style="white")
        ev_table.add_column("Confidence", justify="right", width=12)

        for ev in dossier.evidence_citations:
            conf_str = f"{ev.confidence * 100:.0f}%"
            ev_table.add_row(ev.category.upper(), ev.snippet[:120] + ("..." if len(ev.snippet) > 120 else ""), conf_str)
        console.print(ev_table)

    # Buying Committee Personas
    if dossier.target_buying_committee:
        bc_table = Table(title="Target Buying Committee & Tailored Hooks", box=box.ROUNDED)
        bc_table.add_column("Title & Persona", style="bold yellow", width=30)
        bc_table.add_column("Mandate", style="dim", width=25)
        bc_table.add_column("Personalized Outreach Hook", style="white")

        for persona in dossier.target_buying_committee:
            bc_table.add_row(f"{persona.title}\n[dim]{persona.department}[/dim]", persona.mandate, persona.outreach_hook)
        console.print(bc_table)

    # Executive Strategic Pitch Narrative
    console.print(Panel(dossier.strategic_pitch_narrative, title="[bold green]Executive Strategic Pitch Narrative[/bold green]", border_style="green"))
    console.print("\n" + "-" * 75 + "\n")

def prospect_and_render(offering_key: str):
    console.print(f"\n[bold green]>>> Prospecting customer universe for offering: '{offering_key}'...[/bold green]")
    global LAST_RESULTS
    with console.status("[bold cyan]Scanning enterprise candidates, harvesting live connectors, computing multidimensional fit...", spinner="dots"):
        result = engine.prospect_universe(offering_key)
        LAST_RESULTS = result

    console.print(f"\n[bold white]Offering:[/bold white] [bold cyan]{result.offering.title}[/bold cyan] ({result.offering.category})")
    console.print(f"Total Candidates Evaluated: {result.total_evaluated}  |  Tier 1 Prime Targets: {result.tier1_count}  |  Tier 2 Strategic: {result.tier2_count}\n")

    # Render summary table of ranked candidates
    summary_table = Table(title=f"Ranked Customer Universe - {result.offering.title}", box=box.HEAVY_EDGE)
    summary_table.add_column("Rank", justify="right", style="bold")
    summary_table.add_column("Company", style="bold white")
    summary_table.add_column("Domain", style="dim")
    summary_table.add_column("Score", justify="right")
    summary_table.add_column("Tier", style="cyan")
    summary_table.add_column("Primary Commercial Wedge", style="yellow")
    summary_table.add_column("Solvent", justify="center")

    for i, c in enumerate(result.ranked_customers, 1):
        score_color = "bold green" if c.propensity_score >= 70 else ("bold yellow" if c.propensity_score >= 50 else "bold red")
        solvent_badge = "[green]Yes[/green]" if c.company.is_solvent else "[red]Insolvent[/red]"
        summary_table.add_row(
            str(i),
            c.company.name,
            c.company.domain,
            f"[{score_color}]{c.propensity_score:.1f}[/{score_color}]",
            c.tier,
            c.primary_commercial_wedge.name,
            solvent_badge
        )
    console.print(summary_table)

    # Ask user if they want to inspect a detailed dossier
    inspect_choice = Prompt.ask("\nEnter Rank # to view full dossier (or press Enter to return to menu)", default="")
    if inspect_choice.isdigit():
        idx = int(inspect_choice) - 1
        if 0 <= idx < len(result.ranked_customers):
            render_dossier(result.ranked_customers[idx], rank=idx+1)

def evaluate_single_account(company_name: str, offering_key: str = "commercial_bikes", domain_hint: Optional[str] = None):
    console.print(f"\n[bold green]>>> Deep-diving account '{company_name}' fit for '{offering_key}'...[/bold green]")
    with console.status(f"[bold cyan]Harvesting signals and building operational dossier for {company_name}...", spinner="dots"):
        dossier = engine.evaluate_single_company(company_name, offering_key, domain_hint)
    render_dossier(dossier, rank=1)

def export_last_result():
    if not LAST_RESULTS:
        console.print("[red]No prospecting run available to export. Run option 1 first![/red]")
        return
    filename = f"prospecting_dossiers_{LAST_RESULTS.offering.offering_id}.json"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(LAST_RESULTS.model_dump_json(indent=2))
    console.print(f"[bold green]Successfully exported {len(LAST_RESULTS.ranked_customers)} dossiers to '{filename}'[/bold green]")

def test_individual_connectors():
    company = Prompt.ask("Enter company name to test", default="DHL Group")
    domain_default = "dhl.com" if "dhl" in company.lower() else "siemens.com"

    console.print(f"\n[bold cyan]Testing connectors for '{company}':[/bold cyan]")
    console.print("  [1] Financials (Yahoo Finance)")
    console.print("  [2] News & Intent (Google News RSS)")
    console.print("  [3] Public ATS Hiring (Greenhouse / Lever)")
    console.print("  [4] Security & Infrastructure (DNS / TLS / Subdomains)")
    console.print("  [5] Corporate Registries (EU / North Data / Bundesanzeiger)")
    console.print("  [6] Developer Sentiment (GitHub / Hacker News)")
    console.print("  [7] CISA Known Exploited Vulnerabilities (KEV)")
    console.print("  [8] European Public Procurement Tenders (TED / EU Feeds)")

    choice = Prompt.ask("Select connector to probe", choices=["1", "2", "3", "4", "5", "6", "7", "8"], default="1")

    if choice == "1":
        console.print(f"[yellow]Querying financials for '{company}'...[/yellow]")
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
        console.print("  [bold red][0][/bold red] Exit")

        choice = Prompt.ask("\n[bold cyan]Select an option[/bold cyan]", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")

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
    elif args.command == "custom":
        run_custom_offering_workflow(args.offering)

if __name__ == "__main__":
    main()
