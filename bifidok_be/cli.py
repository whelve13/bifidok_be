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
    OfferingProfile,
    decompose_custom_offering,
    offering_dict_to_profile,
)
from models import PerfectCustomerDossier, ProspectingUniverseResult
from db.seed import seed_database
from services.diagnostics import run_preflight_checks
from services.leads_service import query_prioritized_leads, query_signal_evidence
from db.session import SessionLocal
from db.schema import Company, ServiceOffering, LeadScore, SignalEvaluation

from connectors.financials import fetch_financial_signals
from connectors.news import fetch_company_news
from connectors.ats import fetch_ats_hiring_signals
from connectors.security import analyze_security_posture
from connectors.registries import verify_official_registry
from connectors.developer import fetch_developer_signals
from connectors.vulnerabilities import evaluate_vulnerability_exposure
from connectors.tenders import fetch_public_procurement_tenders
from connectors.firmographics import resolve_company_entity

from data.historical_harvester import (
    build_and_save_historical_market_dataset,
    load_historical_market_dataset,
    HISTORICAL_DATASET_PATH,
)
from engine.local_ml.trainer import (
    train_and_save_models,
    WEIGHTS_DIR,
)
from engine.local_ml.feature_extractor import FEATURE_NAMES

console = Console()
engine = CustomerProspectingEngine()
LAST_RESULTS: Any = None

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
        table.add_row(key, off.title, off.category or "-", wedges, sectors)

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

def prospect_and_render(offering_input: Any):
    if isinstance(offering_input, str):
        offering_key = offering_input.strip()
    elif hasattr(offering_input, "title"):
        offering_key = offering_input.title
    else:
        offering_key = str(offering_input)

    console.print(f"\n[bold green]>>> Prospecting customer universe for offering: '{offering_key}'...[/bold green]")
    global LAST_RESULTS
    with console.status("[bold cyan]Scanning enterprise candidates, harvesting live connectors, computing multidimensional ML fit...", spinner="dots"):
        result = engine.prospect_universe(offering_key)
        LAST_RESULTS = result

    cat_suffix = f" ({result.offering.category})" if result.offering.category else ""
    console.print(f"\n[bold white]Offering:[/bold white] [bold cyan]{result.offering.title}[/bold cyan]{cat_suffix}")
    console.print(f"Total Candidates Evaluated: {result.total_evaluated}  |  Tier 1 Prime Targets: {result.tier1_count}  |  Tier 2 Strategic: {result.tier2_count}\n")

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

    inspect_choice = Prompt.ask("\nEnter Rank # to view full dossier (or press Enter to return to menu)", default="")
    if inspect_choice.isdigit():
        idx = int(inspect_choice) - 1
        if 0 <= idx < len(result.ranked_customers):
            render_dossier(result.ranked_customers[idx], rank=idx+1)


def evaluate_single_account(company_name: str, offering_key: str = "commercial_bikes", domain_hint: Optional[str] = None):
    console.print(f"\n[bold green]>>> Deep-diving account '{company_name}' fit for '{offering_key}'...[/bold green]")
    with console.status(f"[bold cyan]Harvesting live signals and executing ML inference for {company_name}...", spinner="dots"):
        dossier = engine.evaluate_single_company(company_name, offering_key, domain_hint)
    render_dossier(dossier, rank=1)


def export_last_result():
    if not LAST_RESULTS:
        console.print("[red]No prospecting run available to export. Run option 1 first![/red]")
        return
    filename = "prospecting_leads_export.json"
    with open(filename, "w", encoding="utf-8") as f:
        if hasattr(LAST_RESULTS, "model_dump_json"):
            f.write(LAST_RESULTS.model_dump_json(indent=2))
        else:
            json.dump(LAST_RESULTS, f, indent=2)
    console.print(f"[bold green]Successfully exported results to '{filename}'[/bold green]")


def run_doctor():
    console.print("\n[bold cyan]>>> Running preflight health diagnostics...[/bold cyan]")
    diag = run_preflight_checks()
    status_color = "green" if diag["status"] == "HEALTHY" else ("yellow" if diag["status"] == "DEGRADED" else "red")
    console.print(Panel(
        f"[bold {status_color}]System Status: {diag['status']}[/bold {status_color}]\nTimestamp: {diag.get('timestamp', '')}",
        title="Preflight Diagnostics",
        border_style=status_color,
    ))

    table = Table(title="Component Health Probes", box=box.ROUNDED)
    table.add_column("Component", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for comp, details in diag.get("components", {}).items():
        c_status = details.get("status", "UNKNOWN")
        c_color = "green" if c_status in ("UP", "CONFIGURED") else ("yellow" if c_status == "NOT_CONFIGURED" else "red")
        extra = []
        if "company_count" in details:
            extra.append(f"companies: {details['company_count']}")
        if "dialect" in details:
            extra.append(f"dialect: {details['dialect']}")
        if "error" in details and details["error"]:
            extra.append(f"error: {details['error']}")
        if "key_configured" in details:
            extra.append(f"configured: {details['key_configured']}")
        if "connected" in details:
            extra.append(f"connected: {details['connected']}")
        info = "; ".join(extra) if extra else "-"
        table.add_row(comp.capitalize(), f"[{c_color}]{c_status}[/{c_color}]", info)

    console.print(table)


def run_seed():
    console.print("\n[bold cyan]>>> Seeding database with canonical enterprise data...[/bold cyan]")
    counts = seed_database()
    console.print("[bold green]Database successfully seeded:[/bold green]")
    for k, v in counts.items():
        console.print(f"  • {k}: {v}")

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
        kws = Prompt.ask("Enter search keywords (comma-separated)", default="automation, digital transformation, cloud, cybersecurity")
        kw_list = [k.strip() for k in kws.split(",")]
        console.print(f"[yellow]Querying Google News RSS for '{company}' with keywords {kw_list}...[/yellow]")
        news = fetch_company_news(company, kw_list)
        console.print_json(data=news[:3] if news else [])
    elif choice == "3":
        roles = Prompt.ask("Enter target roles (comma-separated)", default="AI Engineer, Automation Lead, Cloud Architect, SOC Analyst")
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
        tender_kws = Prompt.ask("Enter tender keywords", default="tender, procurement, RFP, software, cloud")
        tk_list = [k.strip() for k in tender_kws.split(",")]
        console.print(f"[yellow]Scanning European Public Tenders for '{company}'...[/yellow]")
        tenders = fetch_public_procurement_tenders(company, tk_list)
        console.print_json(data=tenders)


def run_train_models(target_samples: int = 450, show_details: bool = True):
    console.print("\n[bold cyan]>>> Training Local Machine Learning Models on Real Market Data...[/bold cyan]")
    with console.status("[bold green]Loading empirical market dataset and fitting LightGBM / Calibrated Classifiers...", spinner="dots"):
        result = train_and_save_models()

    meta = result.get("metadata", {})
    metrics = meta.get("metrics", {})
    importances = meta.get("feature_importances", {})

    table = Table(title="Trained Model Performance & Serialization Status", box=box.ROUNDED)
    table.add_column("Model Name", style="bold white")
    table.add_column("Architecture", style="cyan")
    table.add_column("Primary Validation Metric", style="bold green")
    table.add_column("Serialized Artifact", style="yellow")

    table.add_row(
        "Hard-Gate Disqualification",
        "StandardScaler + LogisticRegression (Balanced)",
        f"Accuracy: {metrics.get('disqualification_accuracy', 1.0) * 100:.1f}%",
        "weights/disqualification_classifier.joblib"
    )
    table.add_row(
        "Propensity Scoring Regressor",
        "LightGBM Regressor (Monotonic Constraints)",
        f"MAE: {metrics.get('propensity_regressor_mae', 0):.2f} | R²: {metrics.get('propensity_regressor_r2', 0):.4f}",
        "weights/propensity_regressor.joblib"
    )
    table.add_row(
        "Commercial Wedge Selector",
        "RandomForestClassifier (Balanced)",
        f"Macro F1: {metrics.get('wedge_classifier_macro_f1', 1.0):.2f}",
        "weights/wedge_classifier.joblib"
    )
    console.print(table)

    if show_details and importances:
        imp_table = Table(title="Learned Feature Importances (Dynamic Weights)", box=box.SIMPLE)
        imp_table.add_column("Feature Name", style="bold white")
        imp_table.add_column("Relative Weight", justify="right", style="bold yellow")
        imp_table.add_column("Impact Description", style="dim")

        descriptions = {
            "headcount_log": "Procurement scale & organizational capacity",
            "operating_margin": "Financial health & margin compression urgency",
            "is_solvent": "Hard solvency / liquidation gate",
            "ats_role_count": "Active hiring velocity in IT / engineering",
            "has_active_tender": "Active RFP / public procurement demand",
            "has_official_ted_award": "Official European contract award history",
            "has_news_signals": "Press coverage on transformation / restructuring",
            "security_resilience_grade": "Perimeter security posture (A to F)",
            "missing_headers_count": "Security vulnerability gap",
            "cisa_kev_active_count": "Active weaponized CISA vulnerabilities",
            "github_repo_count": "Internal software engineering capability",
            "semantic_relevance": "Core service / domain capability alignment",
            "requires_physical_mismatch": "Physical footprint alignment",
            "sector_alignment": "Industry vertical fit",
        }

        for feat, weight in sorted(importances.items(), key=lambda x: x[1], reverse=True):
            imp_table.add_row(feat, f"{weight * 100:.1f}%", descriptions.get(feat, "-"))
        console.print(imp_table)

    console.print(f"[bold green]Models successfully serialized to '{WEIGHTS_DIR}'[/bold green]\n")


def run_harvest_data(rebuild: bool = True, show_stats: bool = True):
    console.print("\n[bold cyan]>>> Fetching and compiling historical market data...[/bold cyan]")
    with console.status("[bold green]Compiling empirical corporate records and historical buying signals...", spinner="dots"):
        if rebuild:
            records = build_and_save_historical_market_dataset()
        else:
            records = load_historical_market_dataset()

    console.print(f"[bold green]Successfully compiled {len(records)} verified enterprise records.[/bold green]")

    if show_stats and records:
        total = len(records)
        insolvent = sum(1 for r in records if r.get("ground_truth_disqualified") == 1)
        solvent = total - insolvent

        wedge_counts = {0: 0, 1: 0, 2: 0}
        for r in records:
            w = r.get("primary_wedge", 0)
            wedge_counts[w] = wedge_counts.get(w, 0) + 1

        stats_table = Table(title="Historical Market Dataset Summary", box=box.ROUNDED)
        stats_table.add_column("Metric / Dimension", style="bold white")
        stats_table.add_column("Count / Distribution", style="cyan")

        stats_table.add_row("Total Enterprise Records", str(total))
        stats_table.add_row("Active / Solvent Enterprises", f"[green]{solvent}[/green] ({solvent/total*100:.1f}%)")
        stats_table.add_row("Insolvent / Disqualified Cases", f"[red]{insolvent}[/red] ({insolvent/total*100:.1f}%)")
        stats_table.add_row("Wedge 0: Agentic Automation", f"{wedge_counts.get(0, 0)} accounts")
        stats_table.add_row("Wedge 1: Managed SOC", f"{wedge_counts.get(1, 0)} accounts")
        stats_table.add_row("Wedge 2: Cloud Modernization", f"{wedge_counts.get(2, 0)} accounts")
        stats_table.add_row("Dataset File Path", HISTORICAL_DATASET_PATH)

        console.print(stats_table)


def run_fetch_live_data(company_name: str, domain_hint: Optional[str] = None):
    console.print(f"\n[bold cyan]>>> Fetching live multi-source intelligence for '{company_name}'...[/bold cyan]")
    with console.status(f"[bold green]Harvesting across all 8 live connectors for {company_name}...", spinner="dots"):
        entity = resolve_company_entity(company_name, domain_hint)
        domain = entity.get("domain", "")

        fin = fetch_financial_signals(company_name)
        news = fetch_company_news(company_name, ["automation", "modernization", "security", "cloud"])
        tenders = fetch_public_procurement_tenders(company_name, ["tender", "procurement", "RFP"])
        ats = fetch_ats_hiring_signals(company_name, ["AI", "Automation", "Cloud", "Security"])
        sec = analyze_security_posture(domain) if domain else {}
        reg = verify_official_registry(company_name)
        dev = fetch_developer_signals(company_name)
        vuln = evaluate_vulnerability_exposure(domain) if domain else {}

    console.print(Panel.fit(
        f"[bold white]{entity.get('name', company_name)}[/bold white] ([dim]{domain}[/dim])\n"
        f"Legal Name: {entity.get('legal_name', company_name)} | Country: {entity.get('country', 'EU')}\n"
        f"{entity.get('description', '')[:200]}...",
        title="Resolved Canonical Entity",
        border_style="green"
    ))

    t = Table(title=f"Live Multi-Source Connector Findings - {company_name}", box=box.ROUNDED)
    t.add_column("Connector Source", style="bold white")
    t.add_column("Signal Detected", justify="center")
    t.add_column("Key Extracted Data / Evidence", style="dim")

    # Financials
    fin_detected = "[green]YES[/green]" if fin.get("headcount") or fin.get("operating_margin") is not None else "[yellow]PARTIAL[/yellow]"
    fin_detail = f"Headcount: {fin.get('headcount', 'N/A')} | Margin: {fin.get('operating_margin', 'N/A')} | Ticker: {fin.get('ticker', 'N/A')}"
    t.add_row("Yahoo Finance", fin_detected, fin_detail)

    # News
    news_detected = f"[green]{len(news)} items[/green]" if news else "[dim]0 items[/dim]"
    news_detail = f"Top headline: {news[0].get('title', '')[:70]}..." if news else "No breaking catalysts detected."
    t.add_row("Google News RSS", news_detected, news_detail)

    # Tenders
    ten_detected = "[green]YES[/green]" if tenders.get("active_tender_rfp") else "[dim]NONE[/dim]"
    ten_detail = f"Award: {tenders.get('has_official_award')} | Source: {tenders.get('source')} | Confidence: {tenders.get('confidence')}"
    t.add_row("EU TED & Procurement", ten_detected, ten_detail)

    # ATS
    ats_detected = f"[green]{len(ats.get('matched_roles', []))} roles[/green]" if ats.get("matched_roles") else "[dim]0 roles[/dim]"
    ats_detail = f"Provider: {ats.get('ats_provider', 'Custom')} | Roles: {', '.join(ats.get('matched_roles', [])[:3])}"
    t.add_row("Public ATS (Greenhouse/Lever)", ats_detected, ats_detail)

    # Security
    sec_detected = f"[cyan]Grade {sec.get('grade', 'B')}[/cyan]"
    sec_detail = f"Missing headers: {', '.join(sec.get('missing_headers', [])[:3]) or 'None'}"
    t.add_row("Mozilla Observatory", sec_detected, sec_detail)

    # Corporate Registry
    reg_detected = "[green]SOLVENT[/green]" if reg.get("is_solvent", True) else "[red]INSOLVENT[/red]"
    reg_detail = f"Status: {reg.get('status', 'Active')} | Registry: {reg.get('registry', 'EU')}"
    t.add_row("Corporate Registry", reg_detected, reg_detail)

    # Developer & GitHub
    dev_detected = f"[cyan]{dev.get('github_repo_count', 0)} repos[/cyan]"
    dev_detail = f"Tech velocity: {dev.get('primary_language', 'Various')} | HN Stories: {len(dev.get('hacker_news_stories', []))}"
    t.add_row("GitHub & Developer OSINT", dev_detected, dev_detail)

    # Vulnerabilities
    vuln_detected = "[red]EXPOSED[/red]" if vuln.get("cisa_kev_matches") else "[green]CLEAN[/green]"
    vuln_detail = f"CISA KEV count: {vuln.get('cisa_kev_count', 0)}"
    t.add_row("CISA KEV Vulnerabilities", vuln_detected, vuln_detail)

    console.print(t)


def run_show_model_metadata():
    meta_path = os.path.join(WEIGHTS_DIR, "model_metadata.json")
    if not os.path.exists(meta_path):
        console.print("[yellow]No model metadata found. Run training first via 'python -m cli train'![/yellow]")
        return

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    console.print(Panel.fit(
        f"[bold white]Local ML Models - Deployment & Metadata[/bold white]\n"
        f"Trained At: {meta.get('trained_at', 'Unknown')}\n"
        f"Dataset Source: {meta.get('training_data_source', 'N/A')} ({meta.get('dataset_episodes_count', 0)} episodes)\n"
        f"Weights Directory: {WEIGHTS_DIR}",
        border_style="cyan"
    ))

    metrics = meta.get("metrics", {})
    t = Table(title="Validation Metrics", box=box.ROUNDED)
    t.add_column("Metric", style="bold white")
    t.add_column("Value", style="bold green")
    t.add_row("Disqualification Accuracy", f"{metrics.get('disqualification_accuracy', 0) * 100:.2f}%")
    t.add_row("Propensity Regressor MAE", f"{metrics.get('propensity_regressor_mae', 0):.4f}")
    t.add_row("Propensity Regressor R²", f"{metrics.get('propensity_regressor_r2', 0):.4f}")
    t.add_row("Commercial Wedge Macro F1", f"{metrics.get('wedge_classifier_macro_f1', 0):.4f}")
    console.print(t)

    importances = meta.get("feature_importances", {})
    if importances:
        imp_t = Table(title="Feature Importance Ranking", box=box.SIMPLE)
        imp_t.add_column("Rank", justify="right", style="bold")
        imp_t.add_column("Feature", style="bold white")
        imp_t.add_column("Weight", justify="right", style="yellow")
        for i, (k, v) in enumerate(sorted(importances.items(), key=lambda x: x[1], reverse=True), 1):
            imp_t.add_row(str(i), k, f"{v * 100:.2f}%")
        console.print(imp_t)


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
        console.print("  [bold green][1][/bold green] Find Perfect Customers for an Offering (Autonomous Prospecting Scan)")
        console.print("  [bold green][2][/bold green] Deep-Dive Single Enterprise Fit for an Offering (e.g. DHL, Siemens, Zalando)")
        console.print("  [bold green][3][/bold green] Explore Commercial Offerings & Intelligent Operational Wedges")
        console.print("  [bold green][4][/bold green] Custom Commercial Offering (Interactive Rule Configurator & Prospecting)")
        console.print("  [bold green][5][/bold green] Test Individual Live Data Connectors (With Custom Search Keywords)")
        console.print("  [bold green][6][/bold green] Export Prospect Dossiers to JSON (HubSpot / CRM Ready)")
        console.print("  [bold green][7][/bold green] Run Preflight Diagnostics (Doctor)")
        console.print("  [bold green][8][/bold green] Seed Database with Canonical Data")
        console.print("  [bold green][9][/bold green] Train Local ML Models on Real Historical Market Data")
        console.print("  [bold green][10][/bold green] Harvest & Compile Historical Market Dataset")
        console.print("  [bold green][11][/bold green] Fetch Live Multi-Source Signals for a Company")
        console.print("  [bold green][12][/bold green] View Model Weights & Validation Metadata")
        console.print("  [bold red][0][/bold red] Exit")

        choice = Prompt.ask("\n[bold cyan]Select an option[/bold cyan]", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"], default="1")

        if choice == "0":
            console.print("[bold cyan]Exiting Orange Systems Intelligence CLI. Goodbye![/bold cyan]")
            break
        elif choice == "1":
            console.print("\n[bold yellow]Select a Commercial Offering to find customers for:[/bold yellow]")
            console.print("  [bold green][1][/bold green] Agentic Process Automation & AI Workforce [dim](Back-office overhead, ERP/CRM integration, autonomous agents)[/dim]")
            console.print("  [bold green][2][/bold green] Managed SOC & NIS2/DORA Cyber Resilience [dim](Perimeter compliance, 24/7 SOC, vulnerability monitoring)[/dim]")
            console.print("  [bold green][3][/bold green] Cloud Architecture & Modernization [dim](Multi-cloud migration, Kubernetes, FinOps cost governance)[/dim]")
            console.print("  [bold green][4][/bold green] Custom Commercial Offering [dim](Type ANY product or service you want to sell)[/dim]")

            off_choice = Prompt.ask("Choose offering", choices=["1", "2", "3", "4"], default="1")
            if off_choice == "1":
                prospect_and_render("agentic_automation")
            elif off_choice == "2":
                prospect_and_render("managed_soc")
            elif off_choice == "3":
                prospect_and_render("cloud_modernization")
            elif off_choice == "4":
                run_custom_offering_workflow()

        elif choice == "2":
            comp_name = Prompt.ask("Enter company name to evaluate (e.g. DHL Group, BASF, Siemens, Zalando)")
            dom_hint = Prompt.ask("Enter domain hint (optional, press Enter to auto-resolve)", default="")

            console.print("\n[bold yellow]Select the Commercial Offering to evaluate against:[/bold yellow]")
            console.print("  [1] Agentic Process Automation & AI Workforce")
            console.print("  [2] Managed SOC & NIS2 Cyber Resilience")
            console.print("  [3] Cloud Architecture & Modernization")
            console.print("  [4] Custom Offering Text")
            o_choice = Prompt.ask("Choose offering", choices=["1", "2", "3", "4"], default="1")

            off_map = {
                "1": "agentic_automation",
                "2": "managed_soc",
                "3": "cloud_modernization"
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
            run_doctor()
        elif choice == "8":
            run_seed()
        elif choice == "9":
            samples_str = Prompt.ask("Enter target training episodes count", default="450")
            samples = int(samples_str) if samples_str.isdigit() else 450
            run_train_models(target_samples=samples, show_details=True)
        elif choice == "10":
            rebuild_choice = Prompt.ask("Force rebuild dataset from scratch? [y/N]", choices=["y", "n", "Y", "N", ""], default="n")
            run_harvest_data(rebuild=(rebuild_choice.lower() == "y"), show_stats=True)
        elif choice == "11":
            comp = Prompt.ask("Enter company name to harvest live intelligence for", default="DHL Group")
            dom = Prompt.ask("Enter domain hint (optional, press Enter to auto-resolve)", default="")
            run_fetch_live_data(comp, dom if dom.strip() else None)
        elif choice == "12":
            run_show_model_metadata()

def main():
    parser = argparse.ArgumentParser(description="Orange Systems Autonomous Customer Prospecting CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: menu
    subparsers.add_parser("menu", help="Launch interactive navigation menu")

    # Command: doctor
    subparsers.add_parser("doctor", help="Run preflight system health diagnostics")

    # Command: seed
    subparsers.add_parser("seed", help="Seed database with canonical offerings, rules, companies, and evaluations")

    # Command: offerings
    subparsers.add_parser("offerings", help="List commercial offerings and buyer archetypes")

    # Command: prospect
    prospect_parser = subparsers.add_parser("prospect", help="Prospect and rank perfect customers for an offering")
    prospect_parser.add_argument("--offering", required=False, default="agentic_automation", help="Offering key or description (e.g. 'agentic_automation', 'managed_soc', 'cloud_modernization')")

    # Command: evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Deep-dive account fit for an offering")
    eval_parser.add_argument("--company", required=True, help="Target company name (e.g. DHL Group, Siemens, Zalando)")
    eval_parser.add_argument("--offering", required=False, default="agentic_automation", help="Offering name (default: agentic_automation)")
    eval_parser.add_argument("--domain", required=False, default=None, help="Optional domain hint")

    # Command: custom
    custom_parser = subparsers.add_parser("custom", help="Compile and edit a custom commercial offering interactively")
    custom_parser.add_argument("--offering", required=False, default=None, help="Initial product or service description")

    # Command: train
    train_parser = subparsers.add_parser("train", help="Train local ML models on historical market dataset")
    train_parser.add_argument("--samples", type=int, default=450, help="Target training episodes count (default: 450)")
    train_parser.add_argument("--no-details", action="store_true", help="Omit feature importance ranking table")

    # Command: fetch-data
    harvest_parser = subparsers.add_parser("fetch-data", help="Fetch and compile historical enterprise market dataset")
    harvest_parser.add_argument("--rebuild", action="store_true", help="Force rebuild historical dataset file from scratch")

    # Command: fetch-live
    live_parser = subparsers.add_parser("fetch-live", help="Fetch multi-source live connector signals for a company")
    live_parser.add_argument("--company", required=True, help="Target company name (e.g. DHL Group, Siemens, Zalando)")
    live_parser.add_argument("--domain", required=False, default=None, help="Optional domain hint")

    # Command: models-info
    subparsers.add_parser("models-info", help="Display local ML model weights and training validation metadata")

    args = parser.parse_args()

    if args.command is None or args.command == "menu":
        interactive_menu()
    elif args.command == "doctor":
        run_doctor()
    elif args.command == "seed":
        run_seed()
    elif args.command == "offerings":
        display_offerings_catalog()
    elif args.command == "prospect":
        prospect_and_render(args.offering)
    elif args.command == "evaluate":
        evaluate_single_account(args.company, args.offering, args.domain)
    elif args.command == "custom":
        run_custom_offering_workflow(args.offering)
    elif args.command == "train":
        run_train_models(target_samples=args.samples, show_details=not args.no_details)
    elif args.command == "fetch-data":
        run_harvest_data(rebuild=args.rebuild, show_stats=True)
    elif args.command == "fetch-live":
        run_fetch_live_data(args.company, args.domain)
    elif args.command == "models-info":
        run_show_model_metadata()

if __name__ == "__main__":
    main()
