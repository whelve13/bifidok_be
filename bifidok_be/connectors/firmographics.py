import logging
import re
import requests
from typing import Dict, Any, Optional
from services.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "EnterpriseSalesProspectingScout/1.0 (contact@sales-intelligence.internal)"}


def resolve_company_entity(company_name: str, domain_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolves canonical domain, name and overview using Clearbit Autocomplete and Wikipedia Summary REST API.
    Checks Redis / TTL cache before executing external HTTP calls, caching responses for 24 hours.
    """
    resolved = {
        "name": company_name,
        "domain": domain_hint or "",
        "legal_name": company_name,
        "description": "",
        "country": "EU",
    }

    # Clean stripped base for queries
    slug_base = re.sub(
        r'\b(ag|se|gmbh|sa|holding|group|corp|inc|co|plc|nv|bv)\b',
        '',
        company_name,
        flags=re.IGNORECASE,
    ).strip()

    # 1. Clearbit Autocomplete (Row 44 of XLSX)
    if not resolved["domain"]:
        clearbit_cache_key = f"cache:clearbit:{company_name.strip().lower()}"
        cached_clearbit = get_cache(clearbit_cache_key)

        data = None
        if cached_clearbit is not None:
            data = cached_clearbit
        else:
            for q in [company_name, slug_base]:
                if not q:
                    continue
                try:
                    url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={q}"
                    resp = requests.get(url, headers=HEADERS, timeout=4)
                    if resp.status_code == 200 and resp.json():
                        data = resp.json()
                        set_cache(clearbit_cache_key, data, ttl=86400)
                        break
                except Exception as exc:
                    logger.debug("Clearbit lookup failed for %s: %s", q, exc)

        if isinstance(data, list) and len(data) > 0:
            clean_first = (slug_base or company_name).lower().split()[0]
            for item in data:
                item_name = item.get("name", "").lower()
                item_dom = item.get("domain", "").lower()
                if clean_first in item_name or clean_first in item_dom:
                    resolved["domain"] = item.get("domain", "")
                    break

    if not resolved["domain"]:
        # Fallback to simple sanitized domain if still empty
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', slug_base or company_name).lower()
        resolved["domain"] = f"{clean_name}.com"

    # 2. Wikipedia Summary API (Row 45 of XLSX)
    candidates_to_try = [
        company_name.replace(" ", "_"),
        slug_base.replace(" ", "_") if slug_base else "",
    ]
    candidates_to_try = [c for c in candidates_to_try if c]

    wdata = None
    for cand in candidates_to_try:
        wiki_cache_key = f"cache:wikipedia:{cand.strip().lower()}"
        cached_wiki = get_cache(wiki_cache_key)
        if cached_wiki is not None:
            wdata = cached_wiki
            break
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{cand}"
            resp = requests.get(url, headers=HEADERS, timeout=4)
            if resp.status_code == 200:
                wdata = resp.json()
                set_cache(wiki_cache_key, wdata, ttl=86400)
                break
        except Exception as exc:
            logger.debug("Wikipedia lookup failed for %s: %s", cand, exc)

    if isinstance(wdata, dict):
        resolved["description"] = wdata.get("extract", "")
        resolved["short_description"] = wdata.get("description", "")
        resolved["legal_name"] = wdata.get("title", resolved["name"])

    return resolved
