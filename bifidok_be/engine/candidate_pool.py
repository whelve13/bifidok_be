"""
Candidate Pool & Enterprise Universe Module.
Provides verified benchmark enterprise accounts and dynamic candidate lookups.
"""
from typing import Any, Dict, List, Optional


ENTERPRISE_UNIVERSE: List[Dict[str, Any]] = [
    {
        "name": "DHL Group",
        "domain": "dhl.com",
        "legal_name": "Deutsche Post AG",
        "country": "DE",
        "headcount": 590000,
        "sector": "Logistics & Express Delivery",
        "ticker": "DPWA.DU",
        "description": "Deutsche Post DHL Group is the world's leading logistics enterprise, operating global courier delivery, freight transport, and urban delivery networks across 220+ countries.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "Extensive",
            "urban_delivery_fleets": True,
            "esg_net_zero_target": "Zero-emissions logistics by 2050; 60% e-vehicles for last-mile by 2030",
        },
    },
    {
        "name": "BASF SE",
        "domain": "basf.com",
        "legal_name": "BASF SE",
        "country": "DE",
        "headcount": 111000,
        "sector": "Chemicals & Industrial Manufacturing",
        "ticker": "BAS.DE",
        "description": "BASF SE is the world's largest chemical producer, operating massive integrated Verbund industrial manufacturing complexes covering square kilometers in Ludwigshafen and Antwerp.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "Massive Industrial Campuses",
            "internal_campus_transit": True,
            "esg_net_zero_target": "Net zero emissions by 2050",
        },
    },
    {
        "name": "Lufthansa Group",
        "domain": "lufthansa.com",
        "legal_name": "Deutsche Lufthansa AG",
        "country": "DE",
        "headcount": 98000,
        "sector": "Aviation & Transportation",
        "ticker": "LHA.DE",
        "description": "Deutsche Lufthansa AG is Europe's leading airline group, comprising network carriers, cargo transport, and aviation MRO engineering services.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "Hub Airports & Campuses",
            "airport_apron_operations": True,
            "internal_software_division": "Lufthansa Systems",
        },
    },
    {
        "name": "Zalando SE",
        "domain": "zalando.com",
        "legal_name": "Zalando SE",
        "country": "DE",
        "headcount": 16000,
        "sector": "E-Commerce & Digital Retail",
        "ticker": "ZAL.DE",
        "description": "Zalando is Europe's leading online platform for fashion and lifestyle, operating large fulfillment logistics centers across Europe.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "Large Fulfillment Centers",
            "automated_logistics": True,
        },
    },
    {
        "name": "Siemens AG",
        "domain": "siemens.com",
        "legal_name": "Siemens AG",
        "country": "DE",
        "headcount": 311000,
        "sector": "Industrial Technology & Automation",
        "ticker": "SIE.DE",
        "description": "Siemens AG is a global technology powerhouse focusing on industry automation, smart infrastructure, and digital rail transport.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "Extensive Factories & Offices",
            "smart_mobility": True,
        },
    },
    {
        "name": "Signa Holding",
        "domain": "signa.at",
        "legal_name": "Signa Holding GmbH",
        "country": "AT",
        "headcount": 1500,
        "sector": "Real Estate & Retail",
        "ticker": None,
        "description": "Insolvent real estate and retail group undergoing judicial bankruptcy liquidation.",
        "is_solvent": False,
        "operational_attributes": {
            "physical_footprint_level": "Insolvent",
            "bankruptcy_filing": "Active insolvency proceedings under Austrian commercial court",
        },
    },
    {
        "name": "GitLab",
        "domain": "gitlab.com",
        "legal_name": "GitLab Inc.",
        "country": "US",
        "headcount": 2100,
        "sector": "Enterprise Software & DevOps",
        "ticker": "GTLB",
        "description": "GitLab is a leading DevSecOps software platform operating on an all-remote model with zero physical corporate offices, campus buildings, or vehicle fleets.",
        "is_solvent": True,
        "operational_attributes": {
            "physical_footprint_level": "100% Remote - Zero Physical Offices or Facilities",
            "remote_only": True,
        },
    },
]


def get_candidate_universe() -> List[Dict[str, Any]]:
    """Returns the candidate enterprise benchmark pool."""
    return ENTERPRISE_UNIVERSE


def find_candidate_by_name(name_or_domain: str) -> Optional[Dict[str, Any]]:
    """Finds a candidate account in the pool matching name or domain."""
    query = (name_or_domain or "").strip().lower()
    if not query:
        return None

    for c in ENTERPRISE_UNIVERSE:
        c_name = c["name"].lower()
        c_dom = c["domain"].lower()
        if query == c_name or query in c_name or query == c_dom or c_dom in query:
            return c

    return None
