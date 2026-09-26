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
        # 4. Verified Signal Evaluations (Annex Section 6)
        # ---------------------------------------------------------------------
        agentic_off = offering_objs.get("Agentic Automation")

        # DHL Evaluations
        dhl = company_objs.get("dhl.com")
        rule_dhl_ai = rule_objs.get(("Agentic Automation", "Does corporate strategy explicitly prioritize agentic AI or autonomous workflows?"))
        rule_dhl_downsize = rule_objs.get(("Agentic Automation", "Is the company downsizing administrative or back-office headcount?"))

        if dhl and rule_dhl_ai:
            upsert_signal_evaluation(
                session,
                {
                    "company_id": dhl.id,
                    "rule_id": rule_dhl_ai.id,
                    "source_url": "https://www.dhl.com/global-en/home/about-us/strategy-2030.html",
                    "detected": True,
                    "confidence": 0.95,
                    "evidence_quote": "Corporate Strategy 2030 prioritizes agentic AI; production deployments live for RFQ quotation and operational communications.",
                    "reasoning": "Strategy 2030 explicitly funds agentic AI and multi-agent operational modules.",
                },
            )
            counts["evaluations"] += 1

        if dhl and rule_dhl_downsize:
            upsert_signal_evaluation(
                session,
                {
                    "company_id": dhl.id,
                    "rule_id": rule_dhl_downsize.id,
                    "source_url": "https://www.dhl.com/procurement/technology",
                    "detected": True,
                    "confidence": 0.90,
                    "evidence_quote": "Public policy explicitly confirms the use of third-party software vendors alongside internal engineering to accelerate adoption.",
                    "reasoning": "Explicit openness to external vendor integration alongside internal engineering.",
                },
            )
            counts["evaluations"] += 1

        # Lufthansa Evaluations
        lh = company_objs.get("lufthansa.com")
        rule_lh_downsize = rule_objs.get(("Agentic Automation", "Is the company downsizing administrative or back-office headcount?"))
        rule_lh_inhouse = rule_objs.get(("Agentic Automation", "Does the enterprise possess strong internal software engineering divisions creating adoption resistance?"))

        if lh and rule_lh_downsize:
            upsert_signal_evaluation(
                session,
                {
                    "company_id": lh.id,
                    "rule_id": rule_lh_downsize.id,
                    "source_url": "https://investor-relations.lufthansagroup.com/en/news",
                    "detected": True,
                    "confidence": 0.90,
                    "evidence_quote": "Official target to reduce ~4,000 administrative jobs by 2030 using automation, digitalization, and process consolidation.",
                    "reasoning": "Major SG&A and administrative downsizing program creates strong automation pressure.",
                },
            )
            counts["evaluations"] += 1

        if lh and rule_lh_inhouse:
            upsert_signal_evaluation(
                session,
                {
                    "company_id": lh.id,
                    "rule_id": rule_lh_inhouse.id,
                    "source_url": "https://www.lhsystems.com/about",
                    "detected": True,
                    "confidence": 0.85,
                    "evidence_quote": "Strong internal development division (Lufthansa Systems) that creates organizational resistance to external standard software.",
                    "reasoning": "Negative signal: In-house IT engineering creates adoption friction.",
                },
            )
            counts["evaluations"] += 1

        # ---------------------------------------------------------------------
        # 5. Lead Scores (Annex Section 6)
        # ---------------------------------------------------------------------
        if dhl and agentic_off:
            upsert_lead_score(
                session,
                {
                    "company_id": dhl.id,
                    "service_id": agentic_off.id,
                    "composite_score": 86,
                    "is_disqualified": False,
                    "executive_summary": "Strategy 2030 Agentic RFQ Deployment",
                },
            )
            counts["lead_scores"] += 1

        if lh and agentic_off:
            upsert_lead_score(
                session,
                {
                    "company_id": lh.id,
                    "service_id": agentic_off.id,
                    "composite_score": 46,
                    "is_disqualified": False,
                    "executive_summary": "4,000 Headcount Reduction Target",
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
