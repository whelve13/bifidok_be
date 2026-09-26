"""
Curated Candidate Universe for Autonomous Customer Prospecting.
Provides diverse enterprise accounts across Europe with verified firmographics,
operational archetypes, campus/fleet scales, and disqualification test cases.
"""
from typing import List, Dict, Any, Optional

ENTERPRISE_UNIVERSE: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # LOGISTICS, COURIERS & LAST-MILE DELIVERY
    # -------------------------------------------------------------
    {
        "name": "DHL Group",
        "domain": "dhl.com",
        "country": "DE",
        "sector": "Logistics & Express Delivery",
        "headcount": 590000,
        "ticker": "DHL.DE",
        "operational_attributes": {
            "has_last_mile_delivery": True,
            "has_large_campus": True,
            "has_urban_courier_fleet": True,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Global Hubs & Fleets)",
            "esg_net_zero_target": "2050 (60% e-vehicles by 2030)"
        },
        "description": "Deutsche Post DHL Group is the world's leading logistics enterprise, operating global courier delivery, freight transport, and urban delivery networks across 220+ countries."
    },
    {
        "name": "Just Eat Takeaway",
        "domain": "justeattakeaway.com",
        "country": "NL",
        "sector": "Food & Urban Grocery Delivery",
        "headcount": 15000,
        "ticker": "TKWY.AS",
        "operational_attributes": {
            "has_last_mile_delivery": True,
            "has_large_campus": False,
            "has_urban_courier_fleet": True,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (Thousands of urban delivery couriers)",
            "esg_net_zero_target": "100% Zero-Emission Delivery Fleets in Europe"
        },
        "description": "Just Eat Takeaway (Lieferando, Thuisbezorgd) is a leading global online food and grocery delivery marketplace employing thousands of city couriers across Europe."
    },
    {
        "name": "DPD Group",
        "domain": "dpd.com",
        "country": "FR",
        "sector": "Express Parcel Delivery & Couriers",
        "headcount": 120000,
        "ticker": None,
        "operational_attributes": {
            "has_last_mile_delivery": True,
            "has_large_campus": True,
            "has_urban_courier_fleet": True,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Pan-European depots and parcel vans)",
            "esg_net_zero_target": "Net Zero 2040; 350 low-emission European cities"
        },
        "description": "DPD Group (Geopost) delivers over 2 billion parcels annually with thousands of regional delivery depots and dedicated urban green fleet initiatives."
    },
    {
        "name": "PostNL",
        "domain": "postnl.nl",
        "country": "NL",
        "sector": "Postal & E-Commerce Logistics",
        "headcount": 35000,
        "ticker": "PNL.AS",
        "operational_attributes": {
            "has_last_mile_delivery": True,
            "has_large_campus": True,
            "has_urban_courier_fleet": True,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (National delivery and sorted sorting hubs)",
            "esg_net_zero_target": "Zero emission emission delivery in Benelux city centers by 2030"
        },
        "description": "PostNL is the national postal and e-commerce logistics operator in the Netherlands and Belgium, actively replacing combustion vans with cargo bikes."
    },

    # -------------------------------------------------------------
    # HEAVY INDUSTRIAL, CHEMICAL & MANUFACTURING CAMPUSES
    # -------------------------------------------------------------
    {
        "name": "Siemens AG",
        "domain": "siemens.com",
        "country": "DE",
        "sector": "Industrial Automation & Engineering",
        "headcount": 311000,
        "ticker": "SIE.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Siemens Campus Erlangen 3,200 acres + dozens of factories)",
            "esg_net_zero_target": "Carbon Neutral Operations by 2030"
        },
        "description": "Siemens AG is a global technology powerhouse in industrial automation, smart infrastructure, and mobility with expansive multi-square-kilometer factory campuses."
    },
    {
        "name": "BASF SE",
        "domain": "basf.com",
        "country": "DE",
        "sector": "Chemical & Industrial Manufacturing",
        "headcount": 111000,
        "ticker": "BAS.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Extremely Massive (Ludwigshafen 10 km² complex; 2,000+ buildings; 10,000 internal bikes)",
            "esg_net_zero_target": "Net Zero 2050; Scope 1 & 2 cut 25% by 2030"
        },
        "description": "BASF SE is the world's largest chemical company. Its Ludwigshafen Verbund site covers 10 square kilometers where internal bicycles and cargo trikes are the primary transport."
    },
    {
        "name": "BMW Group",
        "domain": "bmwgroup.com",
        "country": "DE",
        "sector": "Automotive Manufacturing",
        "headcount": 149000,
        "ticker": "BMW.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Multi-km assembly plants across Germany)",
            "esg_net_zero_target": "Complete climate neutrality by 2050"
        },
        "description": "BMW Group operates massive manufacturing facilities (Dingolfing, Munich, Leipzig) requiring extensive on-site plant transport and employee commuter programs."
    },
    {
        "name": "Airbus SE",
        "domain": "airbus.com",
        "country": "FR",
        "sector": "Aerospace & Defense",
        "headcount": 134000,
        "ticker": "AIR.PA",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Airfield-adjacent assembly plants spanning kilometers)",
            "esg_net_zero_target": "Scope 1 & 2 -63% by 2030"
        },
        "description": "Airbus SE manufactures commercial aircraft across vast aerodrome production complexes in Toulouse, Hamburg-Finkenwerder, and Bremen."
    },
    {
        "name": "Knorr-Bremse AG",
        "domain": "knorr-bremse.com",
        "country": "DE",
        "sector": "Rail & Commercial Vehicle Systems",
        "headcount": 33000,
        "ticker": "KBX.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (Industrial manufacturing plants in Munich and worldwide)",
            "esg_net_zero_target": "Carbon neutral production sites by 2030"
        },
        "description": "Knorr-Bremse is the global market leader for braking systems and supplier of safety-critical rail and commercial vehicle systems."
    },

    # -------------------------------------------------------------
    # CORPORATE CAMPUSES, TECH & RETAIL (COMMUTER BENEFIT / SCOPE 3)
    # -------------------------------------------------------------
    {
        "name": "Zalando SE",
        "domain": "zalando.de",
        "country": "DE",
        "sector": "E-Commerce & Digital Retail",
        "headcount": 15000,
        "ticker": "ZAL.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (Berlin corporate campus + European fulfillment centers)",
            "esg_net_zero_target": "Net Zero Carbon in own operations; Scope 3 -40%"
        },
        "description": "Zalando SE is Europe's leading online fashion and lifestyle platform with thousands of campus employees in Berlin and fulfillment logistics centers."
    },
    {
        "name": "SAP SE",
        "domain": "sap.com",
        "country": "DE",
        "sector": "Enterprise Software",
        "headcount": 107000,
        "ticker": "SAP.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (Walldorf global headquarters and regional campuses)",
            "esg_net_zero_target": "Net Zero across value chain by 2030"
        },
        "description": "SAP SE is the market leader in enterprise application software, with large campus headquarters in Walldorf and strong green commuter benefit initiatives."
    },
    {
        "name": "N26 Bank",
        "domain": "n26.com",
        "country": "DE",
        "sector": "Digital Banking & Fintech",
        "headcount": 1500,
        "ticker": None,
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": False,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Moderate (Urban office hubs in Berlin, Barcelona, Vienna)",
            "esg_net_zero_target": "Green office operations and commuter mobility perks"
        },
        "description": "N26 is Europe's leading digital mobile bank offering mobile checking accounts to millions of customers across the continent."
    },

    # -------------------------------------------------------------
    # PUBLIC TRANSPORTATION & AIRPORT INFRASTRUCTURE
    # -------------------------------------------------------------
    {
        "name": "Deutsche Bahn",
        "domain": "deutschebahn.com",
        "country": "DE",
        "sector": "Public Transport & Rail Mobility",
        "headcount": 338000,
        "ticker": None,
        "operational_attributes": {
            "has_last_mile_delivery": True,
            "has_large_campus": True,
            "has_urban_courier_fleet": True,
            "is_100pct_remote": False,
            "physical_footprint_level": "Massive (Stations, maintenance depots, Call-a-Bike network)",
            "esg_net_zero_target": "Climate Neutral by 2040"
        },
        "description": "Deutsche Bahn AG is the national railway company of Germany and Europe's largest railway operator, managing passenger rail, freight, and bike sharing."
    },
    {
        "name": "Lufthansa Group",
        "domain": "lufthansa.com",
        "country": "DE",
        "sector": "Aviation & Airline Operations",
        "headcount": 100000,
        "ticker": "LHA.DE",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": True,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "High (Frankfurt & Munich airport aprons, maintenance hangars)",
            "esg_net_zero_target": "Cut net carbon emissions by 50% by 2030"
        },
        "description": "Deutsche Lufthansa AG is Europe's largest airline group, operating major airline hubs, cargo terminals, and technical maintenance hangars."
    },

    # -------------------------------------------------------------
    # DISQUALIFICATION & NEGATIVE TEST CONTROLS
    # -------------------------------------------------------------
    {
        "name": "GitLab",
        "domain": "gitlab.com",
        "country": "US",
        "sector": "Developer Tools & Cloud Software",
        "headcount": 2100,
        "ticker": "GTLB",
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": False,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": True,
            "physical_footprint_level": "Zero (100% All-Remote Workforce, No Physical Offices)",
            "esg_net_zero_target": "Digital efficiency"
        },
        "description": "GitLab Inc. operates the DevSecOps platform and is famous for an entirely remote workforce with zero physical offices, campuses, or fleet needs."
    },
    {
        "name": "Signa Holding",
        "domain": "signa.at",
        "country": "AT",
        "sector": "Real Estate & Retail",
        "headcount": 250,
        "ticker": None,
        "operational_attributes": {
            "has_last_mile_delivery": False,
            "has_large_campus": False,
            "has_urban_courier_fleet": False,
            "is_100pct_remote": False,
            "physical_footprint_level": "Insolvent",
            "esg_net_zero_target": "None"
        },
        "description": "Signa Holding GmbH is a former Austrian real estate conglomerate currently under insolvency and liquidation proceedings."
    }
]

def get_candidate_universe(sectors: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Returns candidate accounts, optionally prioritized by target sectors.
    """
    if not sectors:
        return ENTERPRISE_UNIVERSE

    lowered_sectors = [s.lower() for s in sectors]
    matched = []
    others = []

    for comp in ENTERPRISE_UNIVERSE:
        comp_sector = comp.get("sector", "").lower()
        if any(sec in comp_sector or comp_sector in sec for sec in lowered_sectors):
            matched.append(comp)
        else:
            others.append(comp)

    # Return matched first, followed by remaining for broader discovery
    return matched + others

def find_candidate_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Finds candidate metadata by fuzzy name."""
    clean = name.lower().strip()
    for comp in ENTERPRISE_UNIVERSE:
        if clean in comp["name"].lower() or comp["name"].lower() in clean:
            return comp
    return None
