"""
Commercial Offering Catalog and Autonomous Offering Decomposer.
Transforms any product or commercial mandate into structured ICP criteria,
operational wedges, live signal queries, and target buyer personas.
"""
from typing import Dict, List, Any
import re
from backend.models import OfferingProfile, CommercialWedge, DecisionMakerPersona

# Pre-configured flagship offerings
FLAGSHIP_OFFERINGS: Dict[str, OfferingProfile] = {
    "commercial_bikes": OfferingProfile(
        offering_id="commercial_bikes",
        title="Commercial E-Bike Fleets & Last-Mile Cargo Bicycles",
        category="Commercial Micro-Mobility & Clean Fleet Solutions",
        description="Turnkey corporate e-bike fleets, heavy-duty cargo e-bikes for urban delivery, and turnkey employee commuter bike leasing programs.",
        target_sectors=[
            "Logistics & Delivery",
            "Couriers & Express Delivery",
            "Food & Grocery Delivery",
            "Heavy Manufacturing & Industrials",
            "Automotive",
            "Chemical & Pharmaceuticals",
            "E-Commerce & Retail",
            "Enterprise Technology Campuses",
            "Public Transportation & Municipal Infrastructure"
        ],
        target_wedges=[
            CommercialWedge(
                name="Last-Mile Delivery Cargo E-Bike Fleet",
                target_archetype="Logistics, couriers, postal services, food/grocery delivery platforms",
                description="Heavy-payload urban cargo e-bikes designed to bypass traffic, access pedestrian low-emission zones, and replace diesel vans for last-mile routes.",
                value_driver="Cut urban parcel delivery cost by 35%, eliminate fuel spend, and guarantee compliance with European Zero-Emission City Zones."
            ),
            CommercialWedge(
                name="Large Industrial Campus & Inter-Facility Mobility",
                target_archetype="Massive manufacturing facilities, chemical complexes, aerospace plants, automotive factories",
                description="Ruggedized on-site e-bikes and cargo trikes for maintenance technicians, factory supervisors, and internal intra-site logistics across multi-kilometer sites.",
                value_driver="Reduce internal campus transit time by 60%, eliminate small internal combustion vans on-site, and improve site safety."
            ),
            CommercialWedge(
                name="Corporate Commuter Bike-Leasing Employee Perk (JobRad Scheme)",
                target_archetype="Large corporate employers, tech campuses, banks, retail headquarters with high commuter footfall",
                description="Tax-advantaged salary-sacrifice corporate e-bike leasing program for employees, managed end-to-end with insurance and servicing.",
                value_driver="Dramatically reduce corporate Scope 3 commuter carbon emissions for CSRD reporting, boost employee retention, and alleviate office parking congestion."
            )
        ],
        signal_keywords=[
            "cargo bike", "e-bike", "fleet", "last mile", "delivery", "logistics",
            "emissions", "net zero", "decarbonization", "scope 3", "campus",
            "sustainable mobility", "zero emission", "urban delivery", "commute", "esg"
        ],
        ats_roles=[
            "Fleet Manager", "Head of Last Mile", "Sustainability Manager", "ESG Director",
            "Facilities Coordinator", "Campus Operations", "Logistics Supervisor", "Delivery Operations"
        ],
        tender_keywords=[
            "fleet leasing", "bicycles", "cargo bikes", "electric bikes", "mobility services",
            "sustainable transport", "zero emission delivery", "commuter mobility"
        ],
        min_headcount=100,
        requires_physical_presence=True,
        disqualifiers=[
            "100% remote company with zero physical offices, campuses, or logistics hubs",
            "Company under active bankruptcy or insolvency proceedings"
        ]
    ),

    "agentic_automation": OfferingProfile(
        offering_id="agentic_automation",
        title="Agentic Process Automation & AI Workforce",
        category="Intelligent Enterprise Automation",
        description="Autonomous AI agents and process automation squads that integrate with legacy ERP/CRM to eliminate manual back-office overhead.",
        target_sectors=[
            "Financial Services & Banking", "Insurance", "Logistics", "Telecommunications",
            "Manufacturing", "Retail & E-Commerce", "Healthcare"
        ],
        target_wedges=[
            CommercialWedge(
                name="Back-Office Operational Overhead Reduction",
                target_archetype="Enterprises facing margin pressure, hiring freezes, or rising SG&A costs",
                description="Autonomous agents handling invoicing, reconciliation, vendor onboarding, and compliance workflows.",
                value_driver="Absorb 40% of repetitive operational tasks without increasing headcount."
            ),
            CommercialWedge(
                name="Customer Service & Operations Agentic Acceleration",
                target_archetype="High-volume customer interaction and claims processing environments",
                description="Agentic multi-turn triage and resolution for complex inbound claims and requests.",
                value_driver="Reduce average response latency from hours to seconds while decreasing escalations."
            )
        ],
        signal_keywords=[
            "automation", "efficiency", "restructuring", "cost reduction", "rpa", "ai",
            "margin pressure", "streamline", "back office", "process mining"
        ],
        ats_roles=[
            "Automation Engineer", "RPA Developer", "Process Mining Specialist", "Celonis Lead",
            "Business Analyst", "Transformation Director"
        ],
        tender_keywords=[
            "process automation", "software modernization", "RPA", "AI services", "digital workflow"
        ],
        min_headcount=150,
        requires_physical_presence=False,
        disqualifiers=["Company under active insolvency proceedings"]
    ),

    "managed_soc": OfferingProfile(
        offering_id="managed_soc",
        title="Managed SOC & NIS2/DORA Cyber Resilience",
        category="Enterprise Cybersecurity",
        description="24/7 Managed Security Operations Center, threat hunting, and compliance engineering for EU NIS2 and DORA regulations.",
        target_sectors=[
            "Energy & Utilities", "Banking & Finance", "Healthcare", "Transport", "Manufacturing", "Digital Infrastructure"
        ],
        target_wedges=[
            CommercialWedge(
                name="NIS2 / DORA Compliance Fast-Track",
                target_archetype="Critical infrastructure and supply chain vendors subject to EU cyber enforcement",
                description="Rapid audit, continuous monitoring, and incident reporting pipeline compliant with regulatory frameworks.",
                value_driver="Guarantee NIS2 audit readiness and avoid regulatory fines up to €10M or 2% global turnover."
            )
        ],
        signal_keywords=[
            "cybersecurity", "nis2", "dora", "compliance", "data breach", "ransomware", "security audit", "ciso"
        ],
        ats_roles=[
            "CISO", "Security Analyst", "SOC Lead", "Information Security Officer", "DevSecOps"
        ],
        tender_keywords=[
            "cybersecurity", "managed soc", "penetration testing", "security operations", "incident response"
        ],
        min_headcount=50,
        requires_physical_presence=False,
        disqualifiers=["Company under active insolvency proceedings"]
    )
}

def decompose_custom_offering(query: str) -> OfferingProfile:
    """
    Intelligent NLP/heuristic parser that takes ANY arbitrary user query
    (e.g., 'Bikes', 'We want to sell bikes', 'Industrial solar microgrids', 'Warehouse automation')
    and creates a fully-featured OfferingProfile.
    """
    clean_q = query.strip()
    lowered = clean_q.lower()

    # Match built-in offering if query references it
    if any(k in lowered for k in ["bike", "bicycle", "e-bike", "ebike", "cargo bike", "fleet bike", "mobility"]):
        return FLAGSHIP_OFFERINGS["commercial_bikes"]
    elif any(k in lowered for k in ["automation", "rpa", "agentic", "process mining", "cost reduction"]):
        return FLAGSHIP_OFFERINGS["agentic_automation"]
    elif any(k in lowered for k in ["cyber", "soc", "nis2", "dora", "infosec"]):
        return FLAGSHIP_OFFERINGS["managed_soc"]

    # Extract keywords from the query
    words = re.findall(r'[a-zA-Z]{3,}', lowered)
    stopwords = {"want", "sell", "find", "companies", "customer", "customers", "perfect", "good", "best", "that", "this", "with", "from", "into"}
    meaningful = [w for w in words if w not in stopwords]

    title = clean_q.title() if len(clean_q.split()) <= 6 else f"Commercial Offering: {clean_q[:40]}..."
    slug = re.sub(r'[^a-z0-9]+', '_', lowered)[:30].strip('_')

    # Detect if physical presence is needed
    physical_terms = ["bike", "solar", "hardware", "robot", "warehouse", "drone", "fleet", "vehicle", "clean", "equipment", "sensor"]
    is_physical = any(term in lowered for term in physical_terms)

    # Dynamic target sectors based on keywords
    sectors = ["Manufacturing & Industrials", "Logistics & Supply Chain", "Enterprise Technology", "Retail & Commerce"]
    if any(term in lowered for term in ["energy", "solar", "green", "carbon", "eco", "power"]):
        sectors = ["Energy & Utilities", "Chemical & Heavy Industry", "Commercial Real Estate", "Logistics Hubs"]
    elif any(term in lowered for term in ["health", "med", "pharma", "biotech"]):
        sectors = ["Healthcare & Hospitals", "Pharmaceuticals", "Medical Technology"]
    elif any(term in lowered for term in ["finance", "bank", "insur", "fintech"]):
        sectors = ["Banking & Capital Markets", "Insurance", "Fintech"]

    # Formulate dynamic wedges
    primary_wedge = CommercialWedge(
        name=f"Enterprise Deployment of {title}",
        target_archetype="Large enterprises with strategic requirements in this domain",
        description=f"Direct B2B implementation of {title} integrated with current corporate operations.",
        value_driver=f"Drive measurable ROI, cost savings, and operational enhancement through {title}."
    )

    ats_roles = [f"{w.title()} Lead" for w in meaningful[:3]] + ["Procurement Manager", "Director of Operations"]

    return OfferingProfile(
        offering_id=f"custom_{slug}",
        title=title,
        category="Dynamic Commercial Offering",
        description=f"Tailored B2B offering: {clean_q}",
        target_sectors=sectors,
        target_wedges=[primary_wedge],
        signal_keywords=meaningful + ["modernization", "procurement", "transformation", "esg", "cost reduction"],
        ats_roles=ats_roles,
        tender_keywords=meaningful + ["procurement", "supply contract", "equipment"],
        min_headcount=100 if is_physical else 50,
        requires_physical_presence=is_physical,
        disqualifiers=[
            "100% remote company with zero physical operations" if is_physical else "Irrelevant domain footprint",
            "Company under active bankruptcy or insolvency proceedings"
        ]
    )
