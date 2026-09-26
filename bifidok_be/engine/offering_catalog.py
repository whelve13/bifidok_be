"""
Commercial Offering Catalog and Autonomous Offering Decomposer.
Compiles user commercial mandates into structured ICP criteria,
operational signal rules, connector queries, and target buyer personas.
Supports Gemini AI compilation with rule-based heuristic fallback.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

from models import CommercialWedge, OfferingProfile

logger = logging.getLogger(__name__)

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
            "Public Transportation & Municipal Infrastructure",
        ],
        target_wedges=[
            CommercialWedge(
                name="Last-Mile Delivery Cargo E-Bike Fleet",
                target_archetype="Logistics, couriers, postal services, food/grocery delivery platforms",
                description="Heavy-payload urban cargo e-bikes designed to bypass traffic, access pedestrian low-emission zones, and replace diesel vans for last-mile routes.",
                value_driver="Cut urban parcel delivery cost by 35%, eliminate fuel spend, and guarantee compliance with European Zero-Emission City Zones.",
            ),
            CommercialWedge(
                name="Large Industrial Campus & Inter-Facility Mobility",
                target_archetype="Massive manufacturing facilities, chemical complexes, aerospace plants, automotive factories",
                description="Ruggedized on-site e-bikes and cargo trikes for maintenance technicians, factory supervisors, and internal intra-site logistics across multi-kilometer sites.",
                value_driver="Reduce internal campus transit time by 60%, eliminate small internal combustion vans on-site, and improve site safety.",
            ),
            CommercialWedge(
                name="Corporate Commuter Bike-Leasing Employee Perk (JobRad Scheme)",
                target_archetype="Large corporate employers, tech campuses, banks, retail headquarters with high commuter footfall",
                description="Tax-advantaged salary-sacrifice corporate e-bike leasing program for employees, managed end-to-end with insurance and servicing.",
                value_driver="Dramatically reduce corporate Scope 3 commuter carbon emissions for CSRD reporting, boost employee retention, and alleviate office parking congestion.",
            ),
        ],
        signal_keywords=[
            "cargo bike", "e-bike", "fleet", "last mile", "delivery", "logistics",
            "emissions", "net zero", "decarbonization", "scope 3", "campus",
            "sustainable mobility", "zero emission", "urban delivery", "commute", "esg",
        ],
        ats_roles=[
            "Fleet Manager", "Head of Last Mile", "Sustainability Manager", "ESG Director",
            "Facilities Coordinator", "Campus Operations", "Logistics Supervisor", "Delivery Operations",
        ],
        tender_keywords=[
            "fleet leasing", "bicycles", "cargo bikes", "electric bikes", "mobility services",
            "sustainable transport", "zero emission delivery", "commuter mobility",
        ],
        min_headcount=100,
        requires_physical_presence=True,
        disqualifiers=[
            "100% remote company with zero physical offices, campuses, or logistics hubs",
            "Company under active bankruptcy or insolvency proceedings",
        ],
    ),

    "agentic_automation": OfferingProfile(
        offering_id="agentic_automation",
        title="Agentic Process Automation & AI Workforce",
        category="Intelligent Enterprise Automation",
        description="Autonomous AI agents and process automation squads that integrate with legacy ERP/CRM to eliminate manual back-office overhead.",
        target_sectors=[
            "Financial Services & Banking", "Insurance", "Logistics", "Telecommunications",
            "Manufacturing", "Retail & E-Commerce", "Healthcare",
        ],
        target_wedges=[
            CommercialWedge(
                name="Back-Office Operational Overhead Reduction",
                target_archetype="Enterprises facing margin pressure, hiring freezes, or rising SG&A costs",
                description="Autonomous agents handling invoicing, reconciliation, vendor onboarding, and compliance workflows.",
                value_driver="Absorb 40% of repetitive operational tasks without increasing headcount.",
            ),
            CommercialWedge(
                name="Customer Service & Operations Agentic Acceleration",
                target_archetype="High-volume customer interaction and claims processing environments",
                description="Agentic multi-turn triage and resolution for complex inbound claims and requests.",
                value_driver="Reduce average response latency from hours to seconds while decreasing escalations.",
            ),
        ],
        signal_keywords=[
            "automation", "efficiency", "restructuring", "cost reduction", "rpa", "ai",
            "margin pressure", "streamline", "back office", "process mining",
        ],
        ats_roles=[
            "Automation Engineer", "RPA Developer", "Process Mining Specialist", "Celonis Lead",
            "Business Analyst", "Transformation Director",
        ],
        tender_keywords=[
            "process automation", "software modernization", "RPA", "AI services", "digital workflow",
        ],
        min_headcount=150,
        requires_physical_presence=False,
        disqualifiers=["Company under active insolvency proceedings"],
    ),

    "managed_soc": OfferingProfile(
        offering_id="managed_soc",
        title="Managed SOC & NIS2/DORA Cyber Resilience",
        category="Enterprise Cybersecurity",
        description="24/7 Managed Security Operations Center, threat hunting, and compliance engineering for EU NIS2 and DORA regulations.",
        target_sectors=[
            "Energy & Utilities", "Banking & Finance", "Healthcare", "Transport", "Manufacturing", "Digital Infrastructure",
        ],
        target_wedges=[
            CommercialWedge(
                name="NIS2 / DORA Compliance Fast-Track",
                target_archetype="Critical infrastructure and supply chain vendors subject to EU cyber enforcement",
                description="Rapid audit, continuous monitoring, and incident reporting pipeline compliant with regulatory frameworks.",
                value_driver="Guarantee NIS2 audit readiness and avoid regulatory fines up to €10M or 2% global turnover.",
            ),
        ],
        signal_keywords=[
            "cybersecurity", "nis2", "dora", "compliance", "data breach", "ransomware", "security audit", "ciso",
        ],
        ats_roles=[
            "CISO", "Security Analyst", "SOC Lead", "Information Security Officer", "DevSecOps",
        ],
        tender_keywords=[
            "cybersecurity", "managed soc", "penetration testing", "security operations", "incident response",
        ],
        min_headcount=50,
        requires_physical_presence=False,
        disqualifiers=["Company under active insolvency proceedings"],
    ),
}


def _compile_with_gemini(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to compile user commercial input using the Google Gemini SDK.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""You are an expert B2B sales intelligence compiler for Orange Systems.
Decompose the following commercial offering into a structured JSON draft configuration.

Product / Offering: "{user_input}"

Format your output strictly as a JSON object adhering to this schema:
{{
  "offering_name": "string title",
  "description": "2-3 sentence commercial description",
  "signal_rules": [
    {{
      "question": "Does the enterprise have active initiatives or investments in ...?",
      "guidance_notes": "Look for ... in corporate news, annual disclosures, and press releases.",
      "weight": "HIGH",
      "is_negative": false
    }},
    {{
      "question": "Is the company actively recruiting roles for ...?",
      "guidance_notes": "Look for ATS job postings.",
      "weight": "MEDIUM",
      "is_negative": false
    }},
    {{
      "question": "Has the company issued public tenders or RFPs for ...?",
      "guidance_notes": "Look for public procurement notices.",
      "weight": "MEDIUM",
      "is_negative": false
    }},
    {{
      "question": "Does the company possess an existing internal team building proprietary alternatives?",
      "guidance_notes": "Internal technical capacity creates adoption resistance.",
      "weight": "LOW",
      "is_negative": true
    }},
    {{
      "question": "Is the enterprise undergoing active insolvency, restructuring, or bankruptcy?",
      "guidance_notes": "Insolvency eliminates purchasing capacity.",
      "weight": "DISQUALIFY",
      "is_negative": true
    }}
  ],
  "connector_queries": {{
    "news": ["keyword1", "keyword2", "keyword3"],
    "tenders": ["keyword1", "keyword2"],
    "ats": ["Role 1", "Role 2"],
    "developer": ["keyword1", "keyword2"],
    "security": ["keyword1", "keyword2"]
  }},
  "disqualifiers": [
    "Company under active bankruptcy or insolvency proceedings"
  ]
}}
Do NOT wrap your output in markdown formatting. Return raw JSON only.
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)

        required_keys = {"offering_name", "description", "signal_rules", "connector_queries", "disqualifiers"}
        if required_keys.issubset(data.keys()):
            return data
    except Exception as exc:
        logger.warning("Gemini offering compilation failed (%s). Falling back to heuristics.", exc)

    return None


def _compile_with_heuristics(user_input: str) -> Dict[str, Any]:
    """
    Rule-based heuristic compiler that translates arbitrary commercial mandates
    into structured signal rules, connector keywords, and disqualifiers.
    """
    clean_q = user_input.strip()
    lowered = clean_q.lower()

    # Match built-in archetypes if referenced
    if any(k in lowered for k in ["bike", "bicycle", "e-bike", "ebike", "cargo bike", "fleet bike", "mobility"]):
        return {
            "offering_name": "Commercial E-Bike Fleets & Last-Mile Cargo Bicycles",
            "description": "Turnkey corporate e-bike fleets, heavy-duty cargo e-bikes for urban delivery, and employee commuter bike leasing programs.",
            "signal_rules": [
                {
                    "question": "Does the company operate urban courier, parcel, or last-mile delivery fleets?",
                    "guidance_notes": "Look for courier dispatch, delivery vans, urban logistics hubs.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Does the enterprise operate massive multi-building campuses or industrial manufacturing complexes?",
                    "guidance_notes": "Look for chemical plants, automotive factories, aerospace campuses spanning square kilometers.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Does the company report Scope 3 commuter decarbonization or CSRD sustainability targets?",
                    "guidance_notes": "Look for ESG reports, net-zero commitments, and green commuter programs.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Is the company actively hiring fleet managers, campus mobility, or last-mile logistics leads?",
                    "guidance_notes": "Look for ATS postings for fleet operations, courier supervisors.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Does the company operate 100% remotely with no physical offices, warehouses, or campus facilities?",
                    "guidance_notes": "All-remote workforce cannot utilize physical bikes or depot mobility.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
                {
                    "question": "Is the company currently under insolvency, restructuring, or bankruptcy proceedings?",
                    "guidance_notes": "Credit insolvency disqualifies hardware leasing commitments.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["cargo bike", "e-bike", "fleet decarbonization", "last-mile delivery", "scope 3"],
                "tenders": ["fleet leasing", "cargo bikes", "electric bikes", "sustainable mobility"],
                "ats": ["Fleet Manager", "Head of Last Mile", "Sustainability Manager", "Campus Operations"],
                "developer": ["telematics", "fleet tracking", "iot sensors"],
                "security": ["fleet portal", "iot security"],
            },
            "disqualifiers": [
                "100% remote company with zero physical offices, campuses, or logistics hubs",
                "Company under active bankruptcy or insolvency proceedings",
            ],
        }

    if any(k in lowered for k in ["automation", "rpa", "agentic", "process mining", "cost reduction"]):
        return {
            "offering_name": "Agentic Process Automation & AI Workforce",
            "description": "Autonomous AI agents and process automation squads that integrate with legacy ERP/CRM to eliminate manual back-office overhead.",
            "signal_rules": [
                {
                    "question": "Does the company mention process optimization, cost reduction, operational efficiency, or automation initiatives?",
                    "guidance_notes": "Look for restructuring, margin improvement, and automation roadmaps.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Is the company hiring RPA developers, automation engineers, AI specialists, or process excellence roles?",
                    "guidance_notes": "Look for UiPath, Celonis, Power Automate, or LangChain talent searches.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Has the organization issued RFPs or public procurement for process modernization or workflow automation?",
                    "guidance_notes": "Examine procurement notices and tender publications.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Does the enterprise maintain an internal software development unit that resists external vendors?",
                    "guidance_notes": "Internal IT units create friction against external standard automation squads.",
                    "weight": "LOW",
                    "is_negative": True,
                },
                {
                    "question": "Is the company under active bankruptcy or insolvency proceedings?",
                    "guidance_notes": "Insolvency halts software procurement.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["automation", "efficiency", "restructuring", "cost reduction", "rpa", "ai"],
                "tenders": ["process automation", "software modernization", "RPA", "AI services"],
                "ats": ["Automation Engineer", "RPA Developer", "Process Mining Specialist", "Celonis Lead"],
                "developer": ["UiPath", "Celonis", "Power Automate", "GitLab CI/CD"],
                "security": ["access management", "bot credentials"],
            },
            "disqualifiers": ["Company under active insolvency proceedings"],
        }

    if any(k in lowered for k in ["cyber", "soc", "nis2", "dora", "infosec", "penetration"]):
        return {
            "offering_name": "Managed SOC & NIS2/DORA Cyber Resilience",
            "description": "24/7 Managed Security Operations Center, threat hunting, and compliance engineering for EU NIS2 and DORA regulations.",
            "signal_rules": [
                {
                    "question": "Is the enterprise subject to EU NIS2 Directive or DORA compliance deadlines?",
                    "guidance_notes": "Look for critical infrastructure designations and regulatory deadlines.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Has the organization experienced recent perimeter vulnerabilities, breach announcements, or security audit mandates?",
                    "guidance_notes": "Examine CISA KEV listings and news mentions.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Is the company recruiting CISOs, SOC analysts, or DevSecOps engineers?",
                    "guidance_notes": "Active cyber hiring signals internal bandwidth gaps.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Has the organization published tenders for penetration testing or managed security services?",
                    "guidance_notes": "Search public procurement portals for SOC RFPs.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Is the enterprise currently under liquidation or bankruptcy proceedings?",
                    "guidance_notes": "Insolvent accounts cannot fund SOC contracts.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["cybersecurity", "nis2", "dora", "compliance", "data breach", "ciso"],
                "tenders": ["cybersecurity", "managed soc", "penetration testing", "incident response"],
                "ats": ["CISO", "Security Analyst", "SOC Lead", "Information Security Officer"],
                "developer": ["Fortinet VPN", "Kubernetes", "Azure Cloud", "AWS Cloud"],
                "security": ["exposed subdomains", "missing security headers", "CISA KEV"],
            },
            "disqualifiers": ["Company under active insolvency proceedings"],
        }

    # Generic arbitrary offering compilation
    words = re.findall(r"[a-zA-Z]{3,}", lowered)
    stopwords = {"want", "sell", "find", "companies", "customer", "customers", "perfect", "good", "best", "that", "this", "with", "from", "into", "for"}
    meaningful = [w for w in words if w not in stopwords]
    meaningful_str = " ".join(meaningful[:3]) if meaningful else clean_q

    title = clean_q.title() if len(clean_q.split()) <= 6 else f"Commercial Offering: {clean_q[:35]}..."
    physical_terms = ["bike", "solar", "hardware", "robot", "warehouse", "drone", "fleet", "vehicle", "clean", "equipment", "sensor"]
    is_physical = any(term in lowered for term in physical_terms)

    return {
        "offering_name": title,
        "description": f"Tailored B2B solution for {clean_q}. Drives operational efficiency, measurable cost savings, and enterprise transformation.",
        "signal_rules": [
            {
                "question": f"Does the company report active modernization, capital investments, or strategic initiatives in {meaningful_str}?",
                "guidance_notes": f"Search corporate disclosures and press releases for investments and programs related to {meaningful_str}.",
                "weight": "HIGH",
                "is_negative": False,
            },
            {
                "question": f"Is the organization actively hiring roles related to {meaningful_str} or operational transformation?",
                "guidance_notes": "Look for specialized engineering, operational, or procurement positions.",
                "weight": "MEDIUM",
                "is_negative": False,
            },
            {
                "question": f"Has the enterprise issued public tenders, RFPs, or supplier quotes for {meaningful_str}?",
                "guidance_notes": "Examine procurement notices and vendor solicitations.",
                "weight": "MEDIUM",
                "is_negative": False,
            },
            {
                "question": f"Does the company possess an existing internal division building proprietary alternatives to {meaningful_str}?",
                "guidance_notes": "In-house engineering teams often create resistance to external commercial vendors.",
                "weight": "LOW",
                "is_negative": True,
            },
            {
                "question": "Is the enterprise currently under active insolvency, restructuring, or bankruptcy proceedings?",
                "guidance_notes": "Insolvent organizations cannot approve new commercial contracts.",
                "weight": "DISQUALIFY",
                "is_negative": True,
            },
        ],
        "connector_queries": {
            "news": meaningful + ["modernization", "procurement", "transformation", "investment"],
            "tenders": meaningful + ["procurement", "RFP", "supply contract"],
            "ats": [f"{w.title()} Lead" for w in meaningful[:3]] + ["Procurement Manager", "Director of Operations"],
            "developer": meaningful + ["architecture", "integration", "infrastructure"],
            "security": ["compliance", "security audit"],
        },
        "disqualifiers": [
            "100% remote company with zero physical facilities" if is_physical else "Lack of domain operational footprint",
            "Company under active bankruptcy or insolvency proceedings",
        ],
    }


def decompose_custom_offering(user_input: str) -> Dict[str, Any]:
    """
    Decomposes an arbitrary user commercial mandate into structured offering specs,
    signal rules, connector search queries, and disqualifiers.

    Args:
        user_input: Text query describing what the user wants to sell.

    Returns:
        Dict[str, Any] containing:
          - offering_name (str)
          - description (str)
          - signal_rules (List[Dict])
          - connector_queries (Dict)
          - disqualifiers (List[str])
    """
    clean_input = user_input.strip() if user_input else "Enterprise Digital Modernization"

    # Attempt Gemini LLM compilation
    gemini_compiled = _compile_with_gemini(clean_input)
    if gemini_compiled:
        return gemini_compiled

    # Rule-based heuristic fallback
    return _compile_with_heuristics(clean_input)


def offering_dict_to_profile(compiled: Dict[str, Any]) -> OfferingProfile:
    """
    Converts a compiled offering dictionary into a full OfferingProfile object
    ready for execution by the CustomerProspectingEngine.
    """
    name = compiled.get("offering_name", "Custom Commercial Offering")
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower())[:30].strip("_")
    description = compiled.get("description", "")

    connector_queries = compiled.get("connector_queries", {})
    news_kw = connector_queries.get("news", [])
    tenders_kw = connector_queries.get("tenders", [])
    ats_roles = connector_queries.get("ats", [])
    dev_kw = connector_queries.get("developer", [])

    signal_keywords = list(dict.fromkeys(news_kw + dev_kw + [name]))
    if not ats_roles:
        ats_roles = ["Operations Director", "Procurement Manager", "Head of Technology"]
    if not tenders_kw:
        tenders_kw = list(dict.fromkeys(news_kw[:3] + ["procurement", "modernization"]))

    wedges = []
    for rule in compiled.get("signal_rules", []):
        if not rule.get("is_negative") and rule.get("weight") in ("HIGH", "MEDIUM"):
            wedges.append(CommercialWedge(
                name=rule.get("question")[:50],
                target_archetype="Enterprises matching this strategic requirement",
                description=rule.get("guidance_notes") or rule.get("question"),
                value_driver=f"Direct delivery and integration of {name}.",
            ))

    if not wedges:
        wedges.append(CommercialWedge(
            name=f"Enterprise Deployment of {name}",
            target_archetype="Enterprises matching this strategic requirement",
            description=description or f"Direct B2B implementation of {name}.",
            value_driver=f"Drive measurable ROI and efficiency through {name}.",
        ))

    physical_terms = ["bike", "solar", "hardware", "robot", "warehouse", "drone", "fleet", "vehicle", "clean", "equipment", "sensor"]
    is_physical = any(t in name.lower() or t in description.lower() for t in physical_terms)

    sectors = ["Manufacturing & Industrials", "Logistics & Supply Chain", "Enterprise Technology", "Retail & Commerce"]
    if any(term in name.lower() for term in ["energy", "solar", "green", "carbon", "eco", "power"]):
        sectors = ["Energy & Utilities", "Chemical & Heavy Industry", "Commercial Real Estate", "Logistics Hubs"]
    elif any(term in name.lower() for term in ["health", "med", "pharma", "biotech"]):
        sectors = ["Healthcare & Hospitals", "Pharmaceuticals", "Medical Technology"]
    elif any(term in name.lower() for term in ["finance", "bank", "insur", "fintech"]):
        sectors = ["Banking & Capital Markets", "Insurance", "Fintech"]

    return OfferingProfile(
        offering_id=f"custom_{slug}",
        title=name,
        category="Custom Commercial Offering",
        description=description,
        target_sectors=sectors,
        target_wedges=wedges,
        signal_keywords=signal_keywords or ["modernization", "transformation", "procurement"],
        ats_roles=ats_roles,
        tender_keywords=tenders_kw,
        min_headcount=100 if is_physical else 50,
        requires_physical_presence=is_physical,
        disqualifiers=compiled.get("disqualifiers", ["Company under active insolvency proceedings"]),
    )
