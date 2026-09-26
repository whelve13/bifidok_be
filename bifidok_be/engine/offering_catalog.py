"""
Offering Catalog & Dynamic Commercial Mandate Decomposition Module.
Supports built-in flagship offerings and zero-shot NLP/LLM custom offering decomposition.
"""
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from models import CommercialWedge, OfferingProfile


# ---------------------------------------------------------------------
# BUILT-IN FLAGSHIP OFFERINGS CATALOG
# ---------------------------------------------------------------------
FLAGSHIP_OFFERINGS: Dict[str, OfferingProfile] = {
    "commercial_bikes": OfferingProfile(
        offering_id="commercial_bikes",
        title="Commercial E-Bike Fleets & Last-Mile Cargo Bicycles",
        category="Commercial Micro-Mobility & Clean Fleet Solutions",
        description="Turnkey corporate e-bike fleets, heavy-duty cargo e-bikes for urban delivery, and employee commuter bike leasing programs.",
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
            "sustainable mobility", "zero emission", "urban delivery", "commute", "esg"
        ],
        ats_roles=[
            "Fleet Manager", "Head of Last Mile", "Sustainability Manager",
            "ESG Director", "Facilities Coordinator", "Campus Operations",
            "Logistics Supervisor", "Delivery Operations"
        ],
        tender_keywords=[
            "fleet leasing", "bicycles", "cargo bikes", "electric bikes",
            "mobility services", "sustainable transport", "zero emission delivery", "commuter mobility"
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
        title="Enterprise Agentic AI & Autonomous Process Automation",
        category="Enterprise AI & Intelligent Process Automation",
        description="High-throughput autonomous agent swarms, dynamic document intelligence, and enterprise-grade process orchestration.",
        target_sectors=[
            "Banking & Financial Services", "Insurance", "Logistics & Supply Chain",
            "Telecommunications", "Healthcare & Life Sciences", "Manufacturing"
        ],
        target_wedges=[
            CommercialWedge(
                name="Agentic Document & Back-Office Automation",
                target_archetype="Operations-heavy enterprise divisions, claims processing, invoicing, RFQ quoting",
                description="Autonomous multi-agent workflows executing end-to-end unstructured document processing and ERP syncing.",
                value_driver="Reduce operational cycle time from days to minutes while eliminating manual SG&A processing overhead.",
            ),
            CommercialWedge(
                name="Customer Care & Support Agent Co-Pilot",
                target_archetype="Large customer support teams, shared service centers",
                description="Generative reasoning agents resolving tier-1 and tier-2 customer requests with grounded audit trails.",
                value_driver="Deflect 60%+ of routine inquiries without degrading CSAT scores.",
            ),
        ],
        signal_keywords=[
            "automation", "agentic", "ai", "rpa", "process mining", "efficiency",
            "digital transformation", "cost reduction", "back-office", "generative ai"
        ],
        ats_roles=[
            "RPA Developer", "Automation Engineer", "AI Engineer", "Process Excellence Lead",
            "Head of Operational Transformation", "Business Analyst"
        ],
        tender_keywords=["process automation", "ai platform", "software modernization", "robotic process automation"],
        min_headcount=200,
        requires_physical_presence=False,
        disqualifiers=[
            "Company under active bankruptcy or restructuring proceedings",
        ],
    ),
    "cybersecurity_soc": OfferingProfile(
        offering_id="cybersecurity_soc",
        title="Managed SOC, Threat Intelligence & NIS2/DORA Compliance",
        category="Enterprise Cybersecurity & Compliance Engineering",
        description="24/7 Managed Detection & Response (MDR), continuous attack surface reconnaissance, and regulatory compliance audits.",
        target_sectors=[
            "Critical National Infrastructure", "Energy & Utilities", "Financial Services",
            "Healthcare", "Logistics & Transport", "Manufacturing"
        ],
        target_wedges=[
            CommercialWedge(
                name="NIS2 & DORA Regulatory Compliance Audit",
                target_archetype="European essential and important entities subject to strict NIS2 cybersecurity directives",
                description="Comprehensive gap analysis, supply chain security verification, and automated compliance reporting.",
                value_driver="Guarantee audit readiness and avoid severe statutory non-compliance penalties (up to €10M or 2% of global revenue).",
            ),
            CommercialWedge(
                name="Managed SOC & Continuous Attack Surface Perimeter Monitoring",
                target_archetype="Enterprises with expanding digital footprints and exposed legacy infrastructure",
                description="Proactive perimeter vulnerability scanning, CISA KEV exploitation alerting, and managed incident response.",
                value_driver="Detect and neutralize weaponized zero-day exploits before ransomware deployment.",
            ),
        ],
        signal_keywords=["cybersecurity", "nis2", "dora", "soc", "vulnerability", "infosec", "iso 27001", "zero-day"],
        ats_roles=["CISO", "Security Operations Lead", "SOC Analyst", "Compliance Officer", "Penetration Tester"],
        tender_keywords=["managed soc", "cybersecurity audit", "penetration testing", "incident response services"],
        min_headcount=100,
        requires_physical_presence=False,
        disqualifiers=[
            "Company under active liquidation or bankruptcy proceedings",
        ],
    ),
}


class DecomposedOfferingDict(dict):
    """Dictionary subclass supporting attribute access for offering metadata."""

    @property
    def title(self) -> str:
        return self.get("offering_name", "")

    @property
    def target_sectors(self) -> List[str]:
        return self.get(
            "target_sectors",
            [
                "Logistics & Supply Chain",
                "Industrial Automation & Warehousing",
                "Manufacturing & Freight Operations",
            ],
        )

    @property
    def signal_keywords(self) -> List[str]:
        return self.get("connector_queries", {}).get("news", ["automation", "robotics", "logistics"])

    @property
    def ats_roles(self) -> List[str]:
        return self.get("connector_queries", {}).get("ats", ["Robotics Engineer", "Warehouse Operations"])

    @property
    def tender_keywords(self) -> List[str]:
        return self.get("connector_queries", {}).get("tenders", ["robotics", "automation", "procurement"])

    @property
    def requires_physical_presence(self) -> bool:
        lowered = (str(self.get("offering_name", "")) + " " + str(self.get("description", ""))).lower()
        return any(
            w in lowered
            for w in ["robot", "bike", "cargo", "warehouse", "drone", "solar", "fleet", "physical", "hub"]
        )


# ---------------------------------------------------------------------
# DYNAMIC DECOMPOSITION ENGINE
# ---------------------------------------------------------------------
def decompose_custom_offering(offering_text: str) -> Dict[str, Any]:
    """
    Decomposes an arbitrary commercial product or service mandate into an actionable
    JSON schema with structured signal rules, connector search queries, and disqualifiers.
    Uses Gemini API if configured; otherwise runs deterministic NLP decomposition.
    """
    clean_text = (offering_text or "").strip()
    if not clean_text:
        clean_text = "Enterprise Digital Solutions"

    # Attempt Gemini LLM decomposition if API key is set
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are a master enterprise B2B sales strategist.
Analyze the following commercial product or service offering that an IT/services provider wants to sell:
\"\"\"{clean_text}\"\"\"

Decompose this mandate into a structured prospecting strategy.
Output strictly a JSON object with this exact schema:
{{
  "offering_name": "Concise offering title",
  "description": "1-2 sentence description of what is being sold and its primary value proposition",
  "signal_rules": [
    {{
      "question": "Does the enterprise exhibit explicit demand or indicators for this offering?",
      "guidance_notes": "What evidence indicates an active need or budget",
      "weight": "HIGH",
      "is_negative": false
    }},
    {{
      "question": "Is the enterprise actively recruiting roles related to this domain?",
      "guidance_notes": "Role titles that prove hiring velocity and budget",
      "weight": "MEDIUM",
      "is_negative": false
    }},
    {{
      "question": "Is the company undergoing active insolvency or restructuring?",
      "guidance_notes": "Corporate distress eliminates purchasing ability",
      "weight": "DISQUALIFY",
      "is_negative": true
    }}
  ],
  "connector_queries": {{
    "news": ["keyword1", "keyword2", "keyword3"],
    "tenders": ["tender_kw1", "tender_kw2"],
    "ats": ["Role Title 1", "Role Title 2"],
    "developer": ["tech1", "tech2"],
    "security": ["sec1", "sec2"]
  }},
  "disqualifiers": [
    "Companies with no relevant operational or technological alignment",
    "Company under active bankruptcy or insolvency proceedings"
  ]
}}
Return raw JSON only without markdown code fences.
"""
            response = model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            if "offering_name" in data and "signal_rules" in data:
                return DecomposedOfferingDict(data)
        except Exception:
            pass

    # Deterministic Semantic Fallback
    lowered = clean_text.lower()
    is_bike = any(w in lowered for w in ["bike", "cargo", "bicycle", "cycle", "courier", "fleet"])
    is_solar = any(w in lowered for w in ["solar", "photovoltaic", "battery", "energy", "renewable"])
    is_cyber = any(w in lowered for w in ["cyber", "soc", "security", "nis2", "dora", "vulnerability"])
    is_robot = any(w in lowered for w in ["robot", "warehouse", "automation", "logistics hub"])

    if is_bike:
        return DecomposedOfferingDict({
            "offering_name": "Commercial Cargo E-Bikes for Last-Mile Courier Fleets",
            "description": "Heavy-duty electric cargo bikes and enterprise commuter fleet leasing.",
            "signal_rules": [
                {
                    "question": "Does the enterprise operate urban parcel delivery, logistics, or courier networks?",
                    "guidance_notes": "Urban distribution networks represent prime cargo bike replacement targets.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Has the organization committed to Net Zero, Scope 3, or fleet decarbonization targets?",
                    "guidance_notes": "ESG mandates accelerate electric fleet adoption.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Is the enterprise operating under active insolvency or court restructuring?",
                    "guidance_notes": "Credit distress prohibits fleet lease approval.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["cargo bike", "last mile delivery", "fleet decarbonization", "low emission zone"],
                "tenders": ["fleet leasing", "cargo bicycles", "electric bikes", "mobility services"],
                "ats": ["Fleet Manager", "Head of Last Mile", "Logistics Operations Lead"],
                "developer": ["telematics", "fleet tracking", "iot"],
                "security": ["telematics security", "fleet management"],
            },
            "disqualifiers": [
                "100% remote companies with zero physical offices, warehouses, or campus facilities",
                "Company under active bankruptcy or insolvency proceedings",
            ],
        })

    if is_solar:
        return DecomposedOfferingDict({
            "offering_name": "Commercial Solar Panels & Industrial Energy Storage",
            "description": "Turnkey rooftop photovoltaic systems and commercial battery energy storage solutions.",
            "signal_rules": [
                {
                    "question": "Does the enterprise operate large industrial manufacturing facilities or warehouses?",
                    "guidance_notes": "Large physical roof footprints are prerequisite for commercial PV installations.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Does the enterprise face high energy price exposure or ESG decarbonization mandates?",
                    "guidance_notes": "Rising electricity costs trigger energy independence investments.",
                    "weight": "MEDIUM",
                    "is_negative": False,
                },
                {
                    "question": "Is the organization insolvent or undergoing liquidation?",
                    "guidance_notes": "Solar capex requires strong long-term solvency.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["solar installation", "clean energy capex", "rooftop photovoltaic", "renewable energy"],
                "tenders": ["photovoltaic", "solar panels", "battery storage system", "energy performance contract"],
                "ats": ["Energy Manager", "Facilities Director", "Plant Operations Lead"],
                "developer": ["scada", "energy management software"],
                "security": ["scada security", "grid compliance"],
            },
            "disqualifiers": [
                "Companies with zero owned or long-lease physical manufacturing facilities",
                "Company under active bankruptcy or insolvency proceedings",
            ],
        })

    # Generic Enterprise Mandate
    short_title = clean_text[:40].strip().title()
    return DecomposedOfferingDict({
        "offering_name": short_title,
        "description": f"Enterprise procurement and deployment solutions for {clean_text}.",
        "signal_rules": [
            {
                "question": f"Does the enterprise demonstrate strategic business demand for {clean_text}?",
                "guidance_notes": "Look for explicit mentions of procurement, technology modernization, or transformation initiatives.",
                "weight": "HIGH",
                "is_negative": False,
            },
            {
                "question": "Is the company actively recruiting relevant specialist engineering or operational talent?",
                "guidance_notes": "Active job openings indicate funded budget allocation.",
                "weight": "MEDIUM",
                "is_negative": False,
            },
            {
                "question": "Is the enterprise undergoing active insolvency, bankruptcy, or court-mandated restructuring?",
                "guidance_notes": "Insolvency eliminates vendor contracting ability.",
                "weight": "DISQUALIFY",
                "is_negative": True,
            },
        ],
        "connector_queries": {
            "news": [clean_text[:20], "modernization", "digital transformation", "efficiency"],
            "tenders": [clean_text[:20], "procurement", "RFP", "contract award"],
            "ats": ["Project Manager", "Lead Architect", "Director of Operations"],
            "developer": ["software", "cloud", "api", "architecture"],
            "security": ["security", "compliance", "observability"],
        },
        "disqualifiers": [
            "Organizations with no functional or operational alignment with the offering",
            "Company under active bankruptcy or insolvency proceedings",
        ],
    })


def offering_dict_to_profile(compiled: Dict[str, Any]) -> OfferingProfile:
    """Converts a compiled dictionary into a validated OfferingProfile Pydantic object."""
    offering_id = f"custom_{uuid.uuid4().hex[:8]}"
    title = compiled.get("offering_name", "Custom Offering")
    description = compiled.get("description", "")
    queries = compiled.get("connector_queries", {})

    wedges = []
    # Generate 2-3 specialized commercial wedges from the title/description
    wedges.append(
        CommercialWedge(
            name=f"{title} - Enterprise Turnkey Deployment",
            target_archetype="Large enterprise operators and corporate divisions",
            description=f"Full lifecycle rollout of {title.lower()} integrated into existing workflows.",
            value_driver="Maximize operational throughput and accelerate time-to-value without vendor lock-in.",
        )
    )
    wedges.append(
        CommercialWedge(
            name=f"{title} - Managed Co-Delivery & Support",
            target_archetype="In-house engineering teams needing specialized partner squads",
            description="Dedicated co-delivery squads providing acceleration and operational support.",
            value_driver="Eliminate internal delivery backlogs and reduce execution risk.",
        )
    )

    # Determine if physical presence is required
    lowered = (title + " " + description).lower()
    requires_physical = any(
        w in lowered for w in ["bike", "cargo", "solar", "drone", "hardware", "robot", "fleet", "warehouse", "manufacturing"]
    )

    return OfferingProfile(
        offering_id=offering_id,
        title=title,
        category="Tailored Commercial Solution",
        description=description,
        target_sectors=["Enterprise & Industrials", "Logistics & Transport", "Technology Services"],
        target_wedges=wedges,
        signal_keywords=queries.get("news", ["transformation", "procurement", "modernization"]),
        ats_roles=queries.get("ats", ["Operations Lead", "Project Manager"]),
        tender_keywords=queries.get("tenders", ["procurement", "tender", "RFP"]),
        min_headcount=50,
        requires_physical_presence=requires_physical,
        disqualifiers=compiled.get("disqualifiers", ["Active insolvency proceedings"]),
    )
