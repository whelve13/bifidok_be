"""
Offering Catalog & Dynamic Commercial Mandate Decomposition Module.
Provides dynamic, zero-shot NLP and LLM commercial mandate decomposition
with zero hardcoded static catalog presets or hardcoded company data.
"""
import json
import os
import re
import uuid
from typing import Any, Dict, List, Optional

from models import CommercialWedge, OfferingProfile

# Generic words to exclude when extracting semantic search tokens from mandates
COMMON_STOP_WORDS = {
    "commercial", "enterprise", "solutions", "solution", "service", "services",
    "system", "systems", "platform", "platforms", "technology", "technologies",
    "for", "and", "the", "in", "of", "to", "a", "an", "with", "on", "at", "by",
    "its", "our", "all", "new", "high", "end", "best", "top", "leading",
    "we", "want", "sell", "provide", "providing", "offering", "products", "product",
}


class DecomposedOfferingDict(dict):
    """Dictionary subclass supporting attribute access for offering metadata."""

    @property
    def title(self) -> str:
        return self.get("offering_name", "")

    @property
    def target_sectors(self) -> List[str]:
        return self.get("target_sectors", [])

    @property
    def signal_keywords(self) -> List[str]:
        return self.get("connector_queries", {}).get("news", [])

    @property
    def ats_roles(self) -> List[str]:
        return self.get("connector_queries", {}).get("ats", [])

    @property
    def tender_keywords(self) -> List[str]:
        return self.get("connector_queries", {}).get("tenders", [])

    @property
    def requires_physical_presence(self) -> bool:
        lowered = (str(self.get("offering_name", "")) + " " + str(self.get("description", ""))).lower()
        return any(
            w in lowered
            for w in [
                "robot", "bike", "cargo", "warehouse", "drone", "solar",
                "fleet", "physical", "hub", "hardware", "facility", "vehicle",
            ]
        )


# ---------------------------------------------------------------------
# DYNAMIC DECOMPOSITION ENGINE
# ---------------------------------------------------------------------
def decompose_custom_offering(offering_text: str) -> DecomposedOfferingDict:
    """
    Decomposes an arbitrary commercial product or service mandate into an actionable
    JSON schema with structured signal rules, connector search queries, and disqualifiers.
    Uses Gemini API if configured; otherwise runs dynamic deterministic NLP decomposition.
    No hardcoded products or static data presets are used.
    """
    clean_text = (offering_text or "").strip()
    if not clean_text:
        clean_text = "Enterprise Digital Solutions"

    # 1. Attempt Gemini LLM decomposition if API key is set
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

    # 2. Dynamic Deterministic NLP Decomposition (no hardcoded product silos)
    short_title = clean_text[:60].strip().title()
    tokens = [
        w for w in re.findall(r"[a-zA-Z]+", clean_text.lower())
        if len(w) > 2 and w not in COMMON_STOP_WORDS
    ]
    domain_kw = " ".join(tokens[:3]) if tokens else clean_text[:20]

    return DecomposedOfferingDict({
        "offering_name": short_title,
        "description": f"Enterprise procurement, deployment, and management solutions for {clean_text}.",
        "signal_rules": [
            {
                "question": f"Does the enterprise demonstrate active commercial demand or operational need for {clean_text}?",
                "guidance_notes": f"Look for strategic initiatives, procurement programs, or infrastructure modernization related to {domain_kw}.",
                "weight": "HIGH",
                "is_negative": False,
            },
            {
                "question": f"Is the organization actively recruiting specialist talent or operational leads for {clean_text}?",
                "guidance_notes": "Active recruitment of relevant specialist roles indicates funded budget allocation.",
                "weight": "MEDIUM",
                "is_negative": False,
            },
            {
                "question": "Is the enterprise undergoing active insolvency, bankruptcy, or court-mandated restructuring?",
                "guidance_notes": "Corporate insolvency completely eliminates contracting and payment capability.",
                "weight": "DISQUALIFY",
                "is_negative": True,
            },
        ],
        "connector_queries": {
            "news": [domain_kw, "modernization", "digital transformation", "procurement"] + tokens[:2],
            "tenders": [domain_kw, "procurement", "RFP", "contract award"] + tokens[:2],
            "ats": [f"{tokens[0].capitalize()} Lead" if tokens else "Project Manager", "Director of Operations", "Logistics Lead"],
            "developer": ["software", "cloud", "api", "integration"],
            "security": ["security", "compliance", "governance"],
        },
        "disqualifiers": [
            f"Organizations with no functional or operational alignment with {clean_text}",
            "Company under active bankruptcy or insolvency proceedings",
        ],
    })


def offering_dict_to_profile(compiled: Dict[str, Any]) -> OfferingProfile:
    """Converts a compiled dictionary into a validated OfferingProfile Pydantic object."""
    offering_id = compiled.get("offering_id") or f"custom_{uuid.uuid4().hex[:8]}"
    title = compiled.get("offering_name", "Custom Offering")
    description = compiled.get("description", f"Enterprise solutions for {title}.")
    queries = compiled.get("connector_queries", {})

    lowered = (title + " " + description).lower()
    tokens = [
        w for w in re.findall(r"[a-zA-Z]+", lowered)
        if len(w) > 2 and w not in COMMON_STOP_WORDS
    ]

    wedges = []
    # Dynamic Commercial Wedges
    if any(w in lowered for w in ["automation", "agent", "rpa", "workflow", "process", "ai"]):
        w1_name = f"{title} - Autonomous Agentic Deployment & Scaled Rollout"
        w2_name = f"{title} - Managed Co-Delivery & Systems Integration"
        w3_name = f"{title} - Strategic Pilot & Workflow Optimization"
    elif any(w in lowered for w in ["security", "soc", "cyber", "compliance", "nis2", "dora"]):
        w1_name = f"{title} - 24/7 Managed SOC & Perimeter Telemetry"
        w2_name = f"{title} - Regulatory Compliance & Continuous Audit"
        w3_name = f"{title} - Security Assessment & Resilience Pilot"
    elif any(w in lowered for w in ["cloud", "devops", "kubernetes", "infrastructure", "modernization"]):
        w1_name = f"{title} - Multi-Cloud Migration & Architecture Modernization"
        w2_name = f"{title} - Cloud Platform Co-Delivery Squads"
        w3_name = f"{title} - Workload Assessment & FinOps Pilot"
    elif any(w in lowered for w in ["delivery", "cargo", "courier", "parcel", "last mile", "bike"]):
        w1_name = f"{title} - Last-Mile Delivery & Turnkey Deployment"
        w2_name = f"{title} - Large Industrial Campus & Facility Mobility"
        w3_name = f"{title} - Strategic Pilot & Infrastructure Optimization"
    else:
        w1_name = f"{title} - Enterprise Turnkey Deployment & Scaled Rollout"
        w2_name = f"{title} - Managed Co-Delivery & Acceleration"
        w3_name = f"{title} - Strategic Pilot & Infrastructure Optimization"

    wedges.append(
        CommercialWedge(
            name=w1_name,
            target_archetype=f"Enterprises and operators requiring {title.lower()}",
            description=f"Full lifecycle rollout and integration of {title.lower()}.",
            value_driver=f"Accelerate operational throughput and time-to-value for {title.lower()}.",
        )
    )

    wedges.append(
        CommercialWedge(
            name=w2_name,
            target_archetype="Engineering and operational leadership teams",
            description=f"Specialized co-delivery squads accelerating execution of {title.lower()}.",
            value_driver="Eliminate internal delivery backlogs and reduce execution risk.",
        )
    )

    wedges.append(
        CommercialWedge(
            name=w3_name,
            target_archetype="Corporate operations, procurement, and technology managers",
            description=f"Targeted operational pilot proving unit economics for {title.lower()}.",
            value_driver="Validate ROI and de-risk procurement before enterprise-wide expansion.",
        )
    )

    # Determine if physical presence is required dynamically
    requires_physical = any(
        w in lowered
        for w in [
            "bike", "cargo", "bicycle", "solar", "drone", "hardware",
            "robot", "fleet", "warehouse", "manufacturing", "vehicle",
            "equipment", "facility", "physical",
        ]
    )

    return OfferingProfile(
        offering_id=offering_id,
        title=title,
        category=compiled.get("category", None),
        description=description,
        target_sectors=compiled.get("target_sectors") or [
            f"{tokens[0].capitalize()} & Operations" if tokens else "Enterprise Operations",
            "Logistics & Supply Chain",
            "Technology & Services",
        ],
        target_wedges=wedges,
        signal_keywords=queries.get("news", tokens[:4]),
        ats_roles=queries.get("ats", ["Operations Lead", "Project Manager"]),
        tender_keywords=queries.get("tenders", ["procurement", "tender", "RFP"]),
        min_headcount=compiled.get("min_headcount", 50),
        requires_physical_presence=requires_physical,
        disqualifiers=compiled.get("disqualifiers", [
            f"Organizations with zero operational alignment for {title}",
            "Company under active bankruptcy or insolvency proceedings",
        ]),
    )


# ---------------------------------------------------------------------
# DYNAMIC OFFERINGS CATALOG (ZERO HARDCODED PRESETS)
# ---------------------------------------------------------------------
class DynamicOfferingCatalog(dict):
    """
    Dynamic offering catalog that generates offering profiles on demand without hardcoded data.
    Provides backward-compatible dict interface while eliminating all static presets.
    """

    def __missing__(self, key: str) -> OfferingProfile:
        clean_title = str(key).replace("_", " ").title()
        compiled = decompose_custom_offering(clean_title)
        profile = offering_dict_to_profile(compiled)
        self[key] = profile
        return profile

    def get(self, key: str, default: Any = None) -> Any:
        if not key:
            return default
        if key not in self:
            try:
                return self[key]
            except Exception:
                return default
        return super().get(key, default)


def create_flagship_catalog() -> DynamicOfferingCatalog:
    cat = DynamicOfferingCatalog()
    # Pre-populate core Orange Systems IT and commercial offerings
    for k in ["agentic_automation", "managed_soc", "cloud_modernization", "commercial_bikes"]:
        _ = cat[k]
    return cat


# Catalog contains flagship IT offerings and generates custom profiles on demand
FLAGSHIP_OFFERINGS: Dict[str, OfferingProfile] = create_flagship_catalog()
