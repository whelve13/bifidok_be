import concurrent.futures
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

from connectors.firmographics import resolve_company_entity

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "EnterpriseSalesProspectingScout/1.0 (contact@sales-intelligence.internal)"}

# Generic words to exclude when extracting semantic search tokens from mandates
COMMON_STOP_WORDS = {
    "commercial", "enterprise", "solutions", "solution", "service", "services",
    "system", "systems", "platform", "platforms", "technology", "technologies",
    "for", "and", "the", "in", "of", "to", "a", "an", "with", "on", "at", "by",
    "its", "our", "all", "new", "high", "end", "best", "top", "leading",
    "we", "want", "sell", "provide", "providing", "offering", "products", "product",
}


def derive_discovery_queries(offering_mandate: str) -> Dict[str, Any]:
    """
    Derives search tokens, dynamic categories, and sector metadata dynamically
    from the offering text without relying on any hardcoded categories.
    """
    lowered = (offering_mandate or "").lower()
    tokens = [
        w for w in re.findall(r"[a-zA-Z]+", lowered)
        if w not in COMMON_STOP_WORDS and len(w) > 2
    ]

    dynamic_categories: List[str] = []

    # 1. Dynamically search Wikipedia Category namespace (srnamespace=14)
    if tokens:
        for t in tokens[:2]:
            search_kw = f'"{t} companies"'
            try:
                url = (
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srnamespace=14"
                    f"&srsearch={urllib.parse.quote(search_kw)}&format=json"
                )
                resp = requests.get(url, headers=HEADERS, timeout=4)
                if resp.status_code == 200:
                    for item in resp.json().get("query", {}).get("search", []):
                        cat_title = item.get("title", "")
                        lower_title = cat_title.lower()
                        if cat_title.startswith("Category:") and any(
                            w in lower_title for w in ["compan", "enterpris", "carrier", "operat", "service", "retail", "manufactur", "logistics"]
                        ):
                            if not any(bad in lower_title for bad in ["album", "song", "film", "band", "district", "neighborhood", "school", "park", "street", "los angeles"]):
                                if cat_title not in dynamic_categories:
                                    dynamic_categories.append(cat_title)
                        if len(dynamic_categories) >= 3:
                            break
            except Exception as exc:
                logger.debug("Dynamic category lookup failed for %s: %s", search_kw, exc)

    # 2. Synthesize dynamic category patterns from the extracted keywords as fallback
    for t in tokens[:3]:
        synth_cat = f"Category:{t.capitalize()}_companies"
        if synth_cat not in dynamic_categories:
            dynamic_categories.append(synth_cat)

    sector_name = (
        " ".join(w.capitalize() for w in tokens[:2]) + " & Operations"
        if tokens else "General Enterprise Operations"
    )

    return {
        "categories": dynamic_categories,
        "registry_terms": tokens[:4] if tokens else ["enterprise"],
        "sector": sector_name,
    }


def discover_companies_via_wikipedia(category_title: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Discovers active company articles from a Wikipedia Category."""
    results = []
    try:
        encoded_cat = urllib.parse.quote(category_title)
        url = (
            f"https://en.wikipedia.org/w/api.php?action=query&list=categorymembers"
            f"&cmtitle={encoded_cat}&cmlimit={max_results}&format=json"
        )
        resp = requests.get(url, headers=HEADERS, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            members = data.get("query", {}).get("categorymembers", [])
            for m in members:
                title = m.get("title", "")
                if title.startswith(("Category:", "Template:", "List of", "Portal:", "File:")):
                    continue
                clean_title = re.sub(r"\s*\([^)]*\)", "", title).strip()
                if clean_title:
                    results.append({"name": clean_title, "source": f"Wikipedia:{category_title}"})
    except Exception as exc:
        logger.debug("Wikipedia category discovery failed for %s: %s", category_title, exc)

    return results


def search_companies_via_wikipedia(search_term: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Directly searches Wikipedia articles to discover relevant enterprise entities."""
    results = []
    try:
        url = (
            f"https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(search_term)}&format=json&srlimit={max_results * 2}"
        )
        resp = requests.get(url, headers=HEADERS, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("query", {}).get("search", [])
            company_hints = (
                "company", "corporation", "inc", "ag", "se", "gmbh", "ltd", "firm",
                "founded", "headquartered", "manufacturer", "operator", "producer",
                "retailer", "courier", "logistics", "provider", "supplier", "enterprise",
            )
            for item in items:
                title = item.get("title", "")
                snippet = item.get("snippet", "").lower()
                t_lower = title.lower()
                if title.startswith(("List of", "Template:", "Category:", "Portal:", "Wikipedia:", "File:")):
                    continue
                if any(ind in snippet or ind in t_lower for ind in company_hints):
                    clean_title = re.sub(r"\s*\([^)]*\)", "", title).strip()
                    if clean_title:
                        results.append({"name": clean_title, "source": f"Wikipedia:Search:{search_term}"})
                if len(results) >= max_results:
                    break
    except Exception as exc:
        logger.debug("Wikipedia entity search failed for %s: %s", search_term, exc)

    return results


# Curated European Enterprise Index across major sectors for high-scale discovery
EUROPEAN_ENTERPRISE_INDEX: List[Dict[str, Any]] = [
    # Logistics, Fleets & Last-Mile Distribution
    {"name": "DHL Group", "sector": "Logistics & Supply Chain", "country": "DE", "keywords": ["logistics", "courier", "delivery", "cargo", "freight", "transport", "bike", "fleet", "warehouse", "automation"]},
    {"name": "Maersk Group", "sector": "Logistics & Supply Chain", "country": "DK", "keywords": ["logistics", "shipping", "freight", "cargo", "transport", "cloud", "supply chain"]},
    {"name": "Kuehne+Nagel", "sector": "Logistics & Supply Chain", "country": "CH", "keywords": ["logistics", "freight", "cargo", "transport", "supply chain", "warehouse", "automation"]},
    {"name": "DSV Global Transport", "sector": "Logistics & Supply Chain", "country": "DK", "keywords": ["transport", "logistics", "freight", "cargo", "warehouse", "supply chain"]},
    {"name": "DB Schenker", "sector": "Logistics & Supply Chain", "country": "DE", "keywords": ["logistics", "transport", "freight", "cargo", "rail", "supply chain", "fleet"]},
    {"name": "PostNL", "sector": "Logistics & Postal", "country": "NL", "keywords": ["postal", "delivery", "courier", "parcel", "last-mile", "bike", "fleet", "logistics"]},
    {"name": "Geopost", "sector": "Logistics & Courier", "country": "FR", "keywords": ["parcel", "delivery", "courier", "logistics", "last-mile", "bike", "fleet", "express"]},
    {"name": "Hapag-Lloyd", "sector": "Maritime Transport", "country": "DE", "keywords": ["shipping", "container", "freight", "cargo", "transport", "fleet", "logistics"]},
    {"name": "Dachser", "sector": "Logistics & Freight", "country": "DE", "keywords": ["logistics", "transport", "freight", "warehouse", "supply chain", "cargo"]},
    {"name": "Ceva Logistics", "sector": "Logistics & Supply Chain", "country": "CH", "keywords": ["logistics", "freight", "contract", "warehouse", "supply chain"]},

    # Industrial Manufacturing & Automation
    {"name": "Siemens AG", "sector": "Industrial Manufacturing", "country": "DE", "keywords": ["manufacturing", "industrial", "automation", "cloud", "software", "infrastructure", "iot", "security"]},
    {"name": "BASF SE", "sector": "Chemicals & Manufacturing", "country": "DE", "keywords": ["chemicals", "manufacturing", "industrial", "campus", "plant", "process", "automation", "efficiency"]},
    {"name": "Schneider Electric SE", "sector": "Energy Management & Automation", "country": "FR", "keywords": ["energy", "automation", "industrial", "security", "soc", "iot", "infrastructure"]},
    {"name": "ABB Ltd", "sector": "Industrial Automation & Robotics", "country": "CH", "keywords": ["robotics", "automation", "industrial", "electrification", "power", "manufacturing"]},
    {"name": "Robert Bosch GmbH", "sector": "Automotive & Industrial", "country": "DE", "keywords": ["automotive", "manufacturing", "industrial", "iot", "automation", "software", "fleet"]},
    {"name": "Thyssenkrupp AG", "sector": "Industrial & Materials", "country": "DE", "keywords": ["steel", "industrial", "engineering", "manufacturing", "plant", "modernization"]},
    {"name": "Continental AG", "sector": "Automotive & Technology", "country": "DE", "keywords": ["automotive", "tires", "manufacturing", "software", "autonomous", "fleet"]},
    {"name": "KION Group", "sector": "Intralogistics & Warehouse", "country": "DE", "keywords": ["warehouse", "forklift", "intralogistics", "automation", "robotics", "supply chain", "fleet"]},
    {"name": "Jungheinrich AG", "sector": "Intralogistics & Warehouse", "country": "DE", "keywords": ["warehouse", "automation", "forklift", "robotics", "fleet", "logistics"]},
    {"name": "Alstom SA", "sector": "Transportation & Rail", "country": "FR", "keywords": ["rail", "train", "transport", "infrastructure", "fleet", "mobility", "manufacturing"]},
    {"name": "Atlas Copco", "sector": "Industrial Tools & Equipment", "country": "SE", "keywords": ["industrial", "compressors", "manufacturing", "equipment", "plant"]},
    {"name": "Sandvik AB", "sector": "Engineering & Mining", "country": "SE", "keywords": ["engineering", "machining", "mining", "manufacturing", "equipment", "automation"]},

    # Cloud, IT & Digital Services
    {"name": "SAP SE", "sector": "Enterprise Software", "country": "DE", "keywords": ["software", "cloud", "erp", "enterprise", "database", "modernization", "automation"]},
    {"name": "Capgemini SE", "sector": "IT Consulting & Services", "country": "FR", "keywords": ["cloud", "consulting", "digital", "transformation", "software", "cybersecurity", "ai"]},
    {"name": "Atos SE", "sector": "IT Infrastructure & Security", "country": "FR", "keywords": ["cloud", "cybersecurity", "infrastructure", "hpc", "modernization", "digital"]},
    {"name": "Orange Business", "sector": "Telecommunications & Cloud", "country": "FR", "keywords": ["telecom", "cloud", "cybersecurity", "connectivity", "infrastructure", "iot"]},
    {"name": "Deutsche Telekom AG", "sector": "Telecommunications & Cloud", "country": "DE", "keywords": ["telecom", "cloud", "network", "security", "infrastructure", "t-systems"]},
    {"name": "Telefónica SA", "sector": "Telecommunications", "country": "ES", "keywords": ["telecom", "cloud", "security", "tech", "digital", "network"]},
    {"name": "ASML Holding", "sector": "Semiconductor Equipment", "country": "NL", "keywords": ["semiconductor", "lithography", "manufacturing", "chip", "engineering", "tech"]},

    # Financial Services, Banking & Cyber Compliance (NIS2 / DORA)
    {"name": "Deutsche Bank AG", "sector": "Banking & Financial Services", "country": "DE", "keywords": ["banking", "finance", "security", "soc", "compliance", "dora", "cloud", "fintech"]},
    {"name": "BNP Paribas SA", "sector": "Banking & Financial Services", "country": "FR", "keywords": ["banking", "finance", "compliance", "security", "cloud", "risk", "investment"]},
    {"name": "Banco Santander SA", "sector": "Banking & Financial Services", "country": "ES", "keywords": ["banking", "finance", "cloud", "digital", "security", "compliance", "retail"]},
    {"name": "ING Group", "sector": "Banking & Financial Services", "country": "NL", "keywords": ["banking", "digital", "finance", "cloud", "automation", "compliance", "security"]},
    {"name": "Allianz SE", "sector": "Insurance & Asset Management", "country": "DE", "keywords": ["insurance", "finance", "risk", "security", "cloud", "claims", "automation"]},
    {"name": "AXA SA", "sector": "Insurance & Asset Management", "country": "FR", "keywords": ["insurance", "risk", "security", "cloud", "automation", "finance"]},
    {"name": "Adyen NV", "sector": "Payment Platforms & FinTech", "country": "NL", "keywords": ["payments", "fintech", "cloud", "platform", "security", "compliance", "scale"]},

    # Retail, E-Commerce & Consumer
    {"name": "Zalando SE", "sector": "E-Commerce & Fashion Tech", "country": "DE", "keywords": ["ecommerce", "retail", "platform", "cloud", "logistics", "delivery", "automation", "ai"]},
    {"name": "Carrefour SA", "sector": "Retail & Supermarkets", "country": "FR", "keywords": ["retail", "supermarket", "supply chain", "logistics", "fleet", "cloud", "efficiency"]},
    {"name": "Ahold Delhaize", "sector": "Retail & Supermarkets", "country": "NL", "keywords": ["retail", "grocery", "ecommerce", "supply chain", "logistics", "automation"]},
    {"name": "Inditex SA", "sector": "Retail & Apparel", "country": "ES", "keywords": ["retail", "fashion", "zara", "supply chain", "logistics", "cloud", "rfid"]},
    {"name": "Otto Group", "sector": "E-Commerce & Retail", "country": "DE", "keywords": ["ecommerce", "retail", "logistics", "delivery", "warehouse", "automation"]},
    {"name": "Delivery Hero SE", "sector": "On-Demand Delivery", "country": "DE", "keywords": ["delivery", "food", "courier", "last-mile", "bike", "fleet", "platform"]},

    # Energy, Utilities & Infrastructure
    {"name": "TotalEnergies SE", "sector": "Energy & Petrochemicals", "country": "FR", "keywords": ["energy", "oil", "gas", "renewables", "industrial", "plant", "solar", "fleet"]},
    {"name": "Enel SpA", "sector": "Electric Utilities & Energy", "country": "IT", "keywords": ["energy", "electricity", "renewables", "grid", "smart", "infrastructure", "cloud"]},
    {"name": "Iberdrola SA", "sector": "Electric Utilities", "country": "ES", "keywords": ["energy", "electricity", "renewables", "wind", "solar", "grid", "security"]},
    {"name": "Engie SA", "sector": "Utilities & Energy Transition", "country": "FR", "keywords": ["energy", "renewables", "gas", "infrastructure", "facility", "efficiency"]},
    {"name": "E.ON SE", "sector": "Energy Networks & Infrastructure", "country": "DE", "keywords": ["energy", "grid", "infrastructure", "electricity", "smart", "digital"]},

    # Healthcare & Pharmaceuticals
    {"name": "Novartis AG", "sector": "Pharmaceuticals", "country": "CH", "keywords": ["pharma", "healthcare", "research", "manufacturing", "clinical", "ai", "compliance"]},
    {"name": "Sanofi SA", "sector": "Healthcare & Pharmaceuticals", "country": "FR", "keywords": ["pharma", "healthcare", "manufacturing", "research", "digital", "ai"]},
    {"name": "AstraZeneca PLC", "sector": "Biopharmaceuticals", "country": "GB", "keywords": ["pharma", "biotech", "research", "manufacturing", "clinical", "cloud", "data"]},
    {"name": "Fresenius SE", "sector": "Healthcare & Hospitals", "country": "DE", "keywords": ["healthcare", "hospitals", "medical", "devices", "compliance", "nis2", "operations"]},
    {"name": "Philips NV", "sector": "Health Technology", "country": "NL", "keywords": ["healthtech", "medical", "devices", "cloud", "software", "healthcare", "ai"]},
]

try:
    from data.global_enterprise_universe import GLOBAL_ENTERPRISE_UNIVERSE
    GLOBAL_ENTERPRISE_INDEX = []
    for g in GLOBAL_ENTERPRISE_UNIVERSE:
        if g.get("is_solvent", True):
            GLOBAL_ENTERPRISE_INDEX.append({
                "name": g["name"],
                "sector": g.get("sector", "Enterprise"),
                "country": g.get("country", "Global"),
                "domain": g.get("domain", ""),
                "keywords": [w.lower() for w in g.get("ats_roles", []) + [g.get("sector", ""), g["name"]]],
            })
    # Merge with European Enterprise Index
    for e in EUROPEAN_ENTERPRISE_INDEX:
        if not any(g["name"] == e["name"] for g in GLOBAL_ENTERPRISE_INDEX):
            GLOBAL_ENTERPRISE_INDEX.append(e)
except Exception:
    GLOBAL_ENTERPRISE_INDEX = EUROPEAN_ENTERPRISE_INDEX

# Alias for backward compatibility
EUROPEAN_ENTERPRISE_INDEX = GLOBAL_ENTERPRISE_INDEX


def discover_candidate_universe(
    offering_mandate: str,
    target_count: int = 16,
    include_benchmarks: bool = False,
) -> List[Dict[str, Any]]:
    """
    Autonomous prospecting scout: discovers real target companies on the fly
    matching the commercial offering mandate via multi-source global discovery:
    1. For custom offerings: live Wikipedia category & entity search first for exact niche companies.
    2. Curated Global Enterprise Index for high-confidence domain matches.
    3. Seamless multi-source deduplication.
    """
    query_info = derive_discovery_queries(offering_mandate)
    tokens = query_info.get("registry_terms", [])
    lowered_mandate = (offering_mandate or "").lower()

    # Determine if mandate is one of the flagship commercial categories or a custom product/service
    is_flagship = any(
        f in lowered_mandate
        for f in [
            "agentic", "automation", "managed soc", "soc & nis2", "soc",
            "cloud architecture", "cloud modernization", "cloud",
            "commercial bikes", "bike", "fleet", "logistics", "cargo"
        ]
    )

    discovered_names: List[str] = []
    discovered_items: List[Dict[str, Any]] = []

    # A. Match from Curated Global Enterprise Index first for high-confidence domain fit
    for entry in GLOBAL_ENTERPRISE_INDEX:
        name = entry["name"]
        keywords = entry.get("keywords", [])
        sector = entry.get("sector", "")

        score = 0
        # Require exact non-generic domain keyword matches
        matched_kws = [t for t in keywords if t in lowered_mandate and t not in COMMON_STOP_WORDS]
        if matched_kws:
            score += len(matched_kws) * 2
        if any(t in sector.lower() for t in tokens if t not in COMMON_STOP_WORDS):
            score += 1

        # Accept domain fit (score >= 1)
        if score >= 1 and name not in discovered_names:
            discovered_names.append(name)
            discovered_items.append({
                "name": name,
                "source": f"Global Index:{sector}",
                "country": entry.get("country", "Global"),
                "sector": sector,
                "domain": entry.get("domain", ""),
            })
        if len(discovered_names) >= target_count:
            break

    # B. For CUSTOM commercial offerings needing more entities, search Wikipedia
    if len(discovered_names) < target_count and tokens:
        search_kw = " ".join(tokens[:2]) + " enterprise corporation"
        search_hits = search_companies_via_wikipedia(search_kw, max_results=target_count)
        for h in search_hits:
            if h["name"] not in discovered_names:
                discovered_names.append(h["name"])
                discovered_items.append(h)
            if len(discovered_names) >= target_count:
                break

    # C. Supplement with flagship baseline enterprises if still below target
    if len(discovered_names) < target_count:
        for entry in GLOBAL_ENTERPRISE_INDEX:
            name = entry["name"]
            if name not in discovered_names:
                discovered_names.append(name)
                discovered_items.append({
                    "name": name,
                    "source": f"Global Index:{entry.get('sector', 'Enterprise')}",
                    "country": entry.get("country", "Global"),
                    "sector": entry.get("sector", "Enterprise Operations"),
                    "domain": entry.get("domain", ""),
                })
            if len(discovered_names) >= target_count:
                break

    # 4. Enrich and resolve canonical entities concurrently
    resolved_companies: List[Dict[str, Any]] = []

    def _enrich(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            entity = resolve_company_entity(item["name"])
            short_desc = str(entity.get("short_description") or "").lower()
            full_desc = str(entity.get("description") or "").lower()
            combined = short_desc + " " + full_desc

            clean_name = item["name"].strip().lower()
            # Reject generic non-entity category concepts
            if clean_name in [
                "software", "technology", "artificial intelligence", "cloud computing",
                "cybersecurity", "company", "corporation", "industry", "automation",
                "robotics", "logistics", "freight transport", "cargo",
            ]:
                return None

            # Reject non-commercial articles (schools, parks, geographic areas)
            if any(bad in combined for bad in ["school", "district", "neighborhood", "community in", "park", "song", "album"]):
                return None

            clean_dom = re.sub(r"[^a-zA-Z0-9]", "", item["name"]).lower()

            # Attempt to extract employee count from description if available
            extracted_hc = 2500  # realistic mid-to-large enterprise baseline
            hc_match = re.search(r"(\d{1,3}(?:,\d{3})+|\d+)\s+employees", combined)
            if hc_match:
                try:
                    extracted_hc = int(hc_match.group(1).replace(",", ""))
                except Exception:
                    pass

            return {
                "name": entity.get("name", item["name"]),
                "domain": entity.get("domain") or f"{clean_dom}.com",
                "legal_name": entity.get("legal_name", item["name"]),
                "country": entity.get("country", "EU"),
                "headcount": entity.get("headcount") or extracted_hc,
                "sector": entity.get("sector") or query_info["sector"],
                "ticker": entity.get("ticker"),
                "description": entity.get("description") or f"Enterprise operator aligned with {offering_mandate}.",
                "is_solvent": True,
                "operational_attributes": {},
            }
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_enrich, item) for item in discovered_items[:target_count * 2]]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res and res["name"] not in [c["name"] for c in resolved_companies]:
                resolved_companies.append(res)
            if len(resolved_companies) >= target_count:
                break

    return resolved_companies
