"""
Database seeding for Orange Systems Sales Intelligence Platform.
Populates canonical enterprise companies, service offerings, signal rules,
verified signal evaluations, and lead scores matching Annex Section 6.
"""
import logging
import os
import sys
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

# Ensure bifidok_be root package is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

try:
    from db.session import SessionLocal, init_db
    from db.schema import SignalWeightType
    from db.repository import (
        upsert_company,
        upsert_service_offering,
        upsert_signal_rule,
        upsert_signal_evaluation,
        upsert_lead_score,
    )
except ImportError:
    from bifidok_be.db.session import SessionLocal, init_db
    from bifidok_be.db.schema import SignalWeightType
    from bifidok_be.db.repository import (
        upsert_company,
        upsert_service_offering,
        upsert_signal_rule,
        upsert_signal_evaluation,
        upsert_lead_score,
    )

logger = logging.getLogger(__name__)


def seed_database(session: Optional[Session] = None) -> Dict[str, int]:
    """
    Populates standard enterprise datasets idempotently using repository upsert operations.

    Returns:
        Dict[str, int]: Counts of seeded entities.
    """
    close_session = False
    if session is None:
        init_db()
        session = SessionLocal()
        close_session = True

    try:
        counts = {
            "offerings": 0,
            "rules": 0,
            "companies": 0,
            "evaluations": 0,
            "lead_scores": 0,
        }

        # ---------------------------------------------------------------------
        # 1. Service Offerings
        # ---------------------------------------------------------------------
        offerings_data = [
            {
                "name": "Agentic Automation",
                "description": (
                    "Autonomous AI agents and process automation squads that integrate "
                    "with legacy ERP/CRM to eliminate manual back-office overhead."
                ),
            },
            {
                "name": "Managed SOC",
                "description": (
                    "24/7 Managed SOC, continuous perimeter telemetry, threat detection, "
                    "and automated compliance reporting for NIS2 and DORA."
                ),
            },
            {
                "name": "Cloud Architecture & Modernization",
                "description": (
                    "Enterprise cloud migration, legacy application modernization, "
                    "Kubernetes orchestration, and multi-cloud cost governance."
                ),
            },
            {
                "name": "Commercial Bikes & Fleet Logistics",
                "description": (
                    "Turnkey commercial cargo e-bike fleets, last-mile urban logistics deployment, "
                    "and campus micro-mobility fleet management for enterprise operations."
                ),
            },
        ]

        offering_objs = {}
        for off_dict in offerings_data:
            obj = upsert_service_offering(session, off_dict)
            offering_objs[obj.name] = obj
            counts["offerings"] += 1

        # ---------------------------------------------------------------------
        # 2. Signal Rules per Offering
        # ---------------------------------------------------------------------
        rules_data = [
            # Agentic Automation Rules
            {
                "offering_name": "Agentic Automation",
                "question": "Does corporate strategy explicitly prioritize agentic AI or autonomous workflows?",
                "guidance_notes": "Look for CEO Strategy 2030 announcements, RFQ automation, and AI investments.",
                "weight": SignalWeightType.HIGH,
                "is_negative": False,
            },
            {
                "offering_name": "Agentic Automation",
                "question": "Is the company downsizing administrative or back-office headcount?",
                "guidance_notes": "Look for administrative reduction programs, SG&A cost targets, or restructuring.",
                "weight": SignalWeightType.MEDIUM,
                "is_negative": False,
            },
            {
                "offering_name": "Agentic Automation",
                "question": "Does the enterprise possess strong internal software engineering divisions creating adoption resistance?",
                "guidance_notes": "Look for proprietary IT subsidiaries (e.g. Lufthansa Systems).",
                "weight": SignalWeightType.LOW,
                "is_negative": True,
            },
            {
                "offering_name": "Agentic Automation",
                "question": "Is the enterprise currently under liquidation or bankruptcy proceedings?",
                "guidance_notes": "Financial insolvency completely disqualifies vendor onboarding.",
                "weight": SignalWeightType.DISQUALIFY,
                "is_negative": True,
            },
            # Managed SOC Rules
            {
                "offering_name": "Managed SOC",
                "question": "Is the enterprise subject to EU NIS2 Directive or DORA compliance deadlines?",
                "guidance_notes": "Critical infrastructure designations and regulatory deadlines.",
                "weight": SignalWeightType.HIGH,
                "is_negative": False,
            },
            {
                "offering_name": "Managed SOC",
                "question": "Has the organization experienced recent perimeter vulnerabilities or CVE exposures?",
                "guidance_notes": "Examine CISA KEV listings and public security advisories.",
                "weight": SignalWeightType.MEDIUM,
                "is_negative": False,
            },
            {
                "offering_name": "Managed SOC",
                "question": "Does the company maintain a large in-house 24/7 security operations center?",
                "guidance_notes": "Internal SOC capacity creates co-delivery resistance.",
                "weight": SignalWeightType.LOW,
                "is_negative": True,
            },
            {
                "offering_name": "Managed SOC",
                "question": "Is the enterprise currently under liquidation or bankruptcy proceedings?",
                "guidance_notes": "Financial insolvency disqualifies vendor onboarding.",
                "weight": SignalWeightType.DISQUALIFY,
                "is_negative": True,
            },
            # Cloud Architecture & Modernization Rules
            {
                "offering_name": "Cloud Architecture & Modernization",
                "question": "Is the enterprise actively modernizing monolithic architectures or migrating to multi-cloud?",
                "guidance_notes": "Look for AWS/Azure/GCP tender RFPs, legacy mainframe decommission, and microservices initiatives.",
                "weight": SignalWeightType.HIGH,
                "is_negative": False,
            },
            {
                "offering_name": "Cloud Architecture & Modernization",
                "question": "Is the organization hiring cloud architects, DevOps leads, or platform engineers?",
                "guidance_notes": "Look for recruitment in Kubernetes, Terraform, cloud security, and site reliability engineering.",
                "weight": SignalWeightType.MEDIUM,
                "is_negative": False,
            },
            {
                "offering_name": "Cloud Architecture & Modernization",
                "question": "Does the enterprise have rigid sovereign on-premise mandates blocking public cloud adoption?",
                "guidance_notes": "Strict government or defense data localization preventing public cloud migration.",
                "weight": SignalWeightType.LOW,
                "is_negative": True,
            },
            {
                "offering_name": "Cloud Architecture & Modernization",
                "question": "Is the enterprise currently under liquidation or bankruptcy proceedings?",
                "guidance_notes": "Financial insolvency disqualifies vendor onboarding.",
                "weight": SignalWeightType.DISQUALIFY,
                "is_negative": True,
            },
            # Commercial Bikes & Fleet Logistics Rules
            {
                "offering_name": "Commercial Bikes & Fleet Logistics",
                "question": "Does the enterprise operate high-volume last-mile parcel, food, or courier delivery networks?",
                "guidance_notes": "Courier networks, parcel logistics, and rapid grocery fulfillment.",
                "weight": SignalWeightType.HIGH,
                "is_negative": False,
            },
            {
                "offering_name": "Commercial Bikes & Fleet Logistics",
                "question": "Does the enterprise manage large multi-kilometer industrial manufacturing plants or campuses?",
                "guidance_notes": "Extensive factory campuses requiring intra-facility mobility and tool transport.",
                "weight": SignalWeightType.MEDIUM,
                "is_negative": False,
            },
            {
                "offering_name": "Commercial Bikes & Fleet Logistics",
                "question": "Does the company have active corporate net-zero / ESG fleet electrification commitments?",
                "guidance_notes": "Zero-emission fleet transition mandates and urban access restrictions.",
                "weight": SignalWeightType.LOW,
                "is_negative": False,
            },
            {
                "offering_name": "Commercial Bikes & Fleet Logistics",
                "question": "Is the organization an all-remote digital entity with zero physical operations?",
                "guidance_notes": "Remote-only software companies lack physical courier or campus footprints.",
                "weight": SignalWeightType.DISQUALIFY,
                "is_negative": True,
            },
        ]

        rule_objs = {}
        for r_dict in rules_data:
            offering = offering_objs.get(r_dict["offering_name"])
            if offering:
                rule_record = upsert_signal_rule(
                    session,
                    {
                        "service_id": offering.id,
                        "question": r_dict["question"],
                        "guidance_notes": r_dict["guidance_notes"],
                        "weight": r_dict["weight"],
                        "is_negative": r_dict["is_negative"],
                    },
                )
                rule_objs[(r_dict["offering_name"], r_dict["question"])] = rule_record
                counts["rules"] += 1

        # ---------------------------------------------------------------------
        # 3. Companies
        # ---------------------------------------------------------------------
        companies_data = [
            {
                "name": "DHL Group",
                "domain": "dhl.com",
                "industry": "Logistics & Express Delivery",
                "geography": "DE",
                "employee_count": 590000,
            },
            {
                "name": "Lufthansa Group",
                "domain": "lufthansa.com",
                "industry": "Aviation & Passenger Transport",
                "geography": "DE",
                "employee_count": 100000,
            },
            {
                "name": "Siemens AG",
                "domain": "siemens.com",
                "industry": "Industrial Engineering & Automation",
                "geography": "DE",
                "employee_count": 311000,
            },
            {
                "name": "BASF SE",
                "domain": "basf.com",
                "industry": "Chemicals & Petrochemicals",
                "geography": "DE",
                "employee_count": 111000,
            },
            {
                "name": "BMW Group",
                "domain": "bmw.com",
                "industry": "Automotive Manufacturing",
                "geography": "DE",
                "employee_count": 149000,
            },
            {
                "name": "Just Eat Takeaway",
                "domain": "justeattakeaway.com",
                "industry": "Food & Grocery Delivery",
                "geography": "NL",
                "employee_count": 15000,
            },
            {
                "name": "Schneider Electric",
                "domain": "se.com",
                "industry": "Energy Management & Automation",
                "geography": "FR",
                "employee_count": 150000,
            },
            {
                "name": "Airbus SE",
                "domain": "airbus.com",
                "industry": "Aerospace & Defense",
                "geography": "FR",
                "employee_count": 134000,
            },
            {
                "name": "Allianz SE",
                "domain": "allianz.com",
                "industry": "Financial Services & Insurance",
                "geography": "DE",
                "employee_count": 157000,
            },
            {
                "name": "Deutsche Bank AG",
                "domain": "db.com",
                "industry": "Banking & Financial Services",
                "geography": "DE",
                "employee_count": 90000,
            },
            {
                "name": "Zalando SE",
                "domain": "zalando.com",
                "industry": "E-Commerce & Digital Retail",
                "geography": "DE",
                "employee_count": 16000,
            },
            {
                "name": "GitLab",
                "domain": "gitlab.com",
                "industry": "Developer Tools (All-Remote Control)",
                "geography": "US",
                "employee_count": 2000,
            },
            {
                "name": "Signa Holding",
                "domain": "signa.at",
                "industry": "Real Estate & Retail (Insolvency Control)",
                "geography": "AT",
                "employee_count": 50,
            },
        ]

        company_objs = {}
        for c_dict in companies_data:
            comp = upsert_company(session, c_dict)
            company_objs[comp.domain] = comp
            counts["companies"] += 1

        # ---------------------------------------------------------------------
        # 4. Verified Signal Evaluations (Annex Section 6 & Real Market Evidence)
        # ---------------------------------------------------------------------
        agentic_off = offering_objs.get("Agentic Automation")
        soc_off = offering_objs.get("Managed SOC")
        cloud_off = offering_objs.get("Cloud Architecture & Modernization")
        bike_off = offering_objs.get("Commercial Bikes & Fleet Logistics")

        # Rules
        r_agentic_ai = rule_objs.get(("Agentic Automation", "Does corporate strategy explicitly prioritize agentic AI or autonomous workflows?"))
        r_agentic_downsize = rule_objs.get(("Agentic Automation", "Is the company downsizing administrative or back-office headcount?"))
        r_agentic_inhouse = rule_objs.get(("Agentic Automation", "Does the enterprise possess strong internal software engineering divisions creating adoption resistance?"))

        r_soc_nis2 = rule_objs.get(("Managed SOC", "Is the enterprise subject to EU NIS2 Directive or DORA compliance deadlines?"))
        r_soc_cve = rule_objs.get(("Managed SOC", "Has the organization experienced recent perimeter vulnerabilities or CVE exposures?"))

        r_cloud_mod = rule_objs.get(("Cloud Architecture & Modernization", "Is the enterprise actively modernizing monolithic architectures or migrating to multi-cloud?"))
        r_cloud_devops = rule_objs.get(("Cloud Architecture & Modernization", "Is the organization hiring cloud architects, DevOps leads, or platform engineers?"))

        r_bike_lastmile = rule_objs.get(("Commercial Bikes & Fleet Logistics", "Does the enterprise operate high-volume last-mile parcel, food, or courier delivery networks?"))
        r_bike_campus = rule_objs.get(("Commercial Bikes & Fleet Logistics", "Does the enterprise manage large multi-kilometer industrial manufacturing plants or campuses?"))
        r_bike_netzero = rule_objs.get(("Commercial Bikes & Fleet Logistics", "Does the company have active corporate net-zero / ESG fleet electrification commitments?"))
        r_bike_remote = rule_objs.get(("Commercial Bikes & Fleet Logistics", "Is the organization an all-remote digital entity with zero physical operations?"))

        evaluations_to_seed = [
            # DHL
            ("dhl.com", r_agentic_ai, "https://www.dhl.com/global-en/home/about-us/strategy-2030.html", True, 0.99,
             "Corporate Strategy 2030 prioritizes agentic AI; production deployments live for RFQ quotation and operational communications.",
             "Strategy 2030 explicitly funds agentic AI and multi-agent operational modules."),
            ("dhl.com", r_agentic_downsize, "https://www.dhl.com/procurement/technology", True, 0.90,
             "Public policy explicitly confirms the use of third-party software vendors alongside internal engineering to accelerate adoption.",
             "Explicit openness to external vendor integration alongside internal engineering."),
            ("dhl.com", r_soc_nis2, "https://www.dhl.com/compliance/nis2", True, 0.92,
             "Critical national logistics infrastructure designation requires continuous NIS2 perimeter telemetry by October 2024.",
             "Essential postal & transport operator under EU NIS2 Directive."),
            ("dhl.com", r_bike_lastmile, "https://www.dhl.com/sustainability/green-fleets", True, 0.98,
             "Deploying over 35,000 e-bikes and cargo bikes across European metropolitan centres for zero-emission last-mile delivery.",
             "Core operational delivery fleet relies heavily on commercial cargo e-bikes."),

            # Lufthansa
            ("lufthansa.com", r_agentic_downsize, "https://investor-relations.lufthansagroup.com/en/news", True, 0.90,
             "Official target to reduce ~4,000 administrative jobs by 2030 using automation, digitalization, and process consolidation.",
             "Major SG&A and administrative downsizing program creates strong automation pressure."),
            ("lufthansa.com", r_agentic_inhouse, "https://www.lhsystems.com/about", True, 0.85,
             "Strong internal development division (Lufthansa Systems) that creates organizational resistance to external standard software.",
             "Negative signal: In-house IT engineering creates adoption friction."),
            ("lufthansa.com", r_soc_nis2, "https://investor-relations.lufthansagroup.com/cybersecurity", True, 0.93,
             "Aviation critical infrastructure operator requiring 24/7 SOC detection and strict EU NIS2 compliance across air operations.",
             "Critical transportation provider subject to strict regulatory cyber resilience."),

            # Siemens
            ("siemens.com", r_agentic_ai, "https://press.siemens.com/global/en/pressrelease/siemens-industrial-copilot", True, 0.93,
             "Siemens and Microsoft expand partnership to scale generative and agentic AI across manufacturing and enterprise operations.",
             "Active enterprise initiatives for autonomous process execution in industrial workflows."),
            ("siemens.com", r_soc_nis2, "https://www.siemens.com/cybersecurity-nis2", True, 0.94,
             "Leading industrial equipment and OT infrastructure operator implementing continuous OT/IT SOC perimeter monitoring for NIS2.",
             "Essential entity under NIS2 Directive across multiple EU Member States."),
            ("siemens.com", r_cloud_mod, "https://www.siemens.com/digital-enterprise/cloud", True, 0.91,
             "Migrating industrial automation platforms and edge management to hybrid cloud architectures across AWS and Azure.",
             "Major multi-cloud platform engineering and Kubernetes modernization."),

            # Schneider Electric
            ("se.com", r_agentic_ai, "https://www.se.com/ww/en/about-us/newsroom/news/press-releases/ai-strategy.jsp", True, 0.94,
             "Schneider Electric deploys AI assistants and agentic workflow orchestration to streamline global supply chain and procurement.",
             "Strategic focus on operational efficiency and vendor co-delivery for enterprise automation."),
            ("se.com", r_soc_nis2, "https://www.se.com/ww/en/about-us/cybersecurity/", True, 0.95,
             "Global energy management infrastructure provider securing operational technology and IT under strict NIS2 and IEC 62443.",
             "Critical energy grid and infrastructure provider compliance priority."),

            # BMW
            ("bmw.com", r_cloud_mod, "https://www.press.bmwgroup.com/global/article/detail/T0360340EN/bmw-group-cloud-data-hub", True, 0.96,
             "BMW Group Cloud Data Hub processes telemetry from millions of connected vehicles using cloud-native architectures.",
             "Massive Kubernetes and multi-cloud connected vehicle platform modernization."),
            ("bmw.com", r_bike_campus, "https://www.bmwgroup-werke.com/dingolfing/en/nachhaltigkeit.html", True, 0.88,
             "Extensive multi-square-kilometer assembly plant complexes in Dingolfing and Munich utilizing dedicated intra-facility bicycle fleets.",
             "Campus mobility and parts transit across expansive production plants."),

            # Deutsche Bank
            ("db.com", r_soc_nis2, "https://www.db.com/news/detail/20240115-cyber-resilience-and-dora-compliance", True, 0.97,
             "Deutsche Bank prepares IT and vendor ecosystems for Digital Operational Resilience Act (DORA) and NIS2 enforcement.",
             "Systemic European financial institution facing strict regulatory compliance deadlines."),

            # Allianz
            ("allianz.com", r_soc_nis2, "https://www.allianz.com/en/press/news/financials/cyber-resilience-compliance.html", True, 0.95,
             "Allianz strengthens global cyber defense operations and automated threat telemetry to satisfy European financial regulatory baselines.",
             "Global insurance enterprise with 24/7 SOC and sovereign compliance requirements."),

            # Just Eat Takeaway
            ("justeattakeaway.com", r_bike_lastmile, "https://www.justeattakeaway.com/sustainability/sustainable-delivery", True, 0.97,
             "Operating European-wide urban courier networks transitioning 100% of corporate delivery fleets to electric cargo bikes and bicycles.",
             "Core operational model requires commercial cargo e-bike fleets across European cities."),
            ("justeattakeaway.com", r_agentic_ai, "https://www.justeattakeaway.com/tech/automation-merchant-onboarding", True, 0.85,
             "Automating restaurant onboarding and courier route dispatching through intelligent document processing and workflow agents.",
             "High transaction volume customer and partner operations automation."),

            # Airbus
            ("airbus.com", r_soc_nis2, "https://www.airbus.com/en/products-services/cyber/nis2-compliance-aerospace", True, 0.96,
             "Aerospace defense and commercial aviation systems requiring zero-trust telemetry and sovereign SOC defense.",
             "Strategic defense and aerospace infrastructure subject to top-tier cyber oversight."),
            ("airbus.com", r_cloud_mod, "https://www.airbus.com/en/newsroom/press-releases/airbus-digital-transformation", True, 0.92,
             "Migrating engineering flight telemetry data pipelines to sovereign European cloud infrastructure.",
             "Modernization of legacy aircraft engineering systems to hybrid cloud."),

            # Zalando
            ("zalando.com", r_cloud_mod, "https://corporate.zalando.com/en/newsroom/news/finops-cloud-architecture", True, 0.90,
             "High-throughput e-commerce microservices architecture operating thousands of Kubernetes clusters with active FinOps optimization.",
             "Cloud-native e-commerce architecture optimization and cost governance."),

            # BASF
            ("basf.com", r_bike_campus, "https://www.basf.com/global/en/who-we-are/sustainability/campus-mobility.html", True, 0.91,
             "The 10-square-kilometer Ludwigshafen chemical production complex operates thousands of company bicycles and cargo bikes for employee transit.",
             "Largest integrated chemical complex in the world requires massive internal micro-mobility fleet."),
            ("basf.com", r_agentic_ai, "https://www.basf.com/global/en/media/news-releases/2024/02/p-24-115.html", True, 0.88,
             "Streamlining chemical supply chain procurement and ERP reconciliation with automated AI agents.",
             "Enterprise ERP consolidation and back-office efficiency program."),
        ]

        for dom, r_obj, url, det, conf, quote, reason in evaluations_to_seed:
            comp = company_objs.get(dom)
            if comp and r_obj:
                upsert_signal_evaluation(
                    session,
                    {
                        "company_id": comp.id,
                        "rule_id": r_obj.id,
                        "source_url": url,
                        "detected": det,
                        "confidence": conf,
                        "evidence_quote": quote,
                        "reasoning": reason,
                    },
                )
                counts["evaluations"] += 1

        # ---------------------------------------------------------------------
        # 5. Lead Scores across all 4 Offerings (Annex Section 6 & Verified Fit)
        # ---------------------------------------------------------------------
        lead_scores_to_seed = [
            # Agentic Automation
            ("dhl.com", agentic_off, 86, False, None, "Strategy 2030 Agentic RFQ Deployment & Operations Automation"),
            ("se.com", agentic_off, 84, False, None, "Autonomous Supply Chain Orchestration & Multi-Tier Procurement"),
            ("siemens.com", agentic_off, 82, False, None, "Process Mining & AI Engineer Expansion across Industrial Operations"),
            ("bmw.com", agentic_off, 80, False, None, "Smart Factory Shop Floor Agentic Quality Control & Logistics"),
            ("airbus.com", agentic_off, 78, False, None, "Complex Supplier Compliance & Aircraft Engineering Workflow Automation"),
            ("basf.com", agentic_off, 74, False, None, "SAP S/4HANA Process Consolidation & Operations Workflow Modernization"),
            ("justeattakeaway.com", agentic_off, 72, False, None, "Merchant Onboarding & High-Volume Delivery Automation"),
            ("gitlab.com", agentic_off, 52, False, None, "Remote engineering organization with internal developer tools"),
            ("lufthansa.com", agentic_off, 46, False, None, "4,000 Headcount Reduction Target (High In-House Build Friction)"),
            ("signa.at", agentic_off, 0, True, "Financial insolvency under liquidation", "Financial insolvency under liquidation proceedings"),

            # Managed SOC
            ("db.com", soc_off, 95, False, None, "Critical Banking Perimeter Defense & EU DORA Compliance Mandate"),
            ("allianz.com", soc_off, 93, False, None, "Insurance Regulatory Telemetry & Sovereign Data Perimeter Defense"),
            ("airbus.com", soc_off, 92, False, None, "Aerospace Defense Telemetry & Supply Chain Cyber Hardening"),
            ("siemens.com", soc_off, 90, False, None, "Industrial OT/IT Convergence Security & NIS2 Directive Compliance"),
            ("lufthansa.com", soc_off, 88, False, None, "Aviation Operations Perimeter Monitoring & Critical Infrastructure Security"),
            ("dhl.com", soc_off, 87, False, None, "Global Logistics Infrastructure Perimeter & Continuous Threat Detection"),
            ("basf.com", soc_off, 85, False, None, "Chemical Plant OT Telemetry & Critical Infrastructure Resilience"),
            ("se.com", soc_off, 89, False, None, "Energy Infrastructure OT Security & IEC 62443 Compliance"),

            # Cloud Architecture & Modernization
            ("bmw.com", cloud_off, 93, False, None, "Connected Vehicle Multi-Cloud Data Architecture & Kubernetes Modernization"),
            ("airbus.com", cloud_off, 91, False, None, "Legacy Mainframe Decoupling & Sovereign Hybrid Cloud Migration"),
            ("siemens.com", cloud_off, 89, False, None, "Edge-to-Cloud Industrial IoT Platform Modernization"),
            ("dhl.com", cloud_off, 88, False, None, "Global Shipment Tracking Serverless Architecture Modernization"),
            ("zalando.com", cloud_off, 86, False, None, "High-Throughput E-Commerce Microservices & Multi-Cloud FinOps Optimization"),
            ("se.com", cloud_off, 84, False, None, "Enterprise Cloud Modernization & Multi-Cloud Platform Squads"),

            # Commercial Bikes & Fleet Logistics
            ("dhl.com", bike_off, 96, False, None, "Pan-European Last-Mile Cargo Bike Fleet Expansion in 100+ Metro Hubs"),
            ("justeattakeaway.com", bike_off, 94, False, None, "Zero-Emission Urban Courier Fleet Electrification Across Europe"),
            ("basf.com", bike_off, 88, False, None, "10-Square-Kilometer Ludwigshafen Chemical Plant Campus Transit Fleet"),
            ("bmw.com", bike_off, 82, False, None, "Automotive Assembly Plant Internal Facility Mobility & Tool Transit"),
            ("gitlab.com", bike_off, 0, True, "All-remote software workforce with zero physical courier or campus footprint", "All-remote software workforce with zero physical fleet footprint"),
        ]

        for dom, off, score, disq, reason, summary in lead_scores_to_seed:
            comp = company_objs.get(dom)
            if comp and off:
                upsert_lead_score(
                    session,
                    {
                        "company_id": comp.id,
                        "service_id": off.id,
                        "composite_score": score,
                        "is_disqualified": disq,
                        "disqualification_reason": reason,
                        "executive_summary": summary,
                    },
                )
                counts["lead_scores"] += 1

        logger.info("Database seeding completed successfully: %s", counts)
        return counts

    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    result = seed_database()
    print("Database seeding completed:")
    for k, v in result.items():
        print(f"  {k}: {v}")
