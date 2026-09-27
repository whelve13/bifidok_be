import logging
import re
import requests
from typing import Dict, Any, Optional
from services.cache import get_cache, set_cache

try:
    from services.proxy_manager import get_resilient_session, resilient_get
except ImportError:
    from bifidok_be.services.proxy_manager import get_resilient_session, resilient_get

logger = logging.getLogger(__name__)

WIKI_USER_AGENT = "OrangeSystemsSalesIntelligence/1.0 (compliance@orangesystems.eu; European Market Intel)"
HEADERS = {"User-Agent": WIKI_USER_AGENT}


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
        "country": "Global",
    }
    session = get_resilient_session(user_agent=WIKI_USER_AGENT)

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
                    resp = resilient_get(url, headers=HEADERS, requests_get_fn=requests.get, session=session, timeout=4)
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
            resp = resilient_get(url, headers=HEADERS, requests_get_fn=requests.get, session=session, timeout=4)
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

    # Dynamic country resolution from domain TLD
    dom = (resolved.get("domain") or "").lower()
    tld_map = {
        ".de": "DE", ".uk": "UK", ".co.uk": "UK", ".fr": "FR", ".nl": "NL",
        ".ch": "CH", ".se": "SE", ".it": "IT", ".es": "ES", ".ca": "CA",
        ".au": "AU", ".jp": "JP", ".kr": "KR", ".in": "IN", ".sg": "SG",
        ".at": "AT", ".dk": "DK", ".fi": "FI", ".ie": "IE", ".us": "US",
    }
    for tld, c_code in tld_map.items():
        if dom.endswith(tld):
            resolved["country"] = c_code
            break

    # Dynamic country resolution from summary text if still Global
    if resolved["country"] == "Global":
        text_corpus = f"{resolved.get('description', '')} {resolved.get('short_description', '')}".lower()
        if any(w in text_corpus for w in ["american", "united states", "headquartered in new york", "california", "texas", "washington"]):
            resolved["country"] = "US"
        elif any(w in text_corpus for w in ["british", "united kingdom", "london", "england", "scotland"]):
            resolved["country"] = "UK"
        elif any(w in text_corpus for w in ["german", "germany", "munich", "berlin", "frankfurt"]):
            resolved["country"] = "DE"
        elif any(w in text_corpus for w in ["french", "france", "paris"]):
            resolved["country"] = "FR"
        elif any(w in text_corpus for w in ["japanese", "japan", "tokyo"]):
            resolved["country"] = "JP"
        elif any(w in text_corpus for w in ["swiss", "switzerland", "zurich", "geneva", "basel"]):
            resolved["country"] = "CH"
        elif any(w in text_corpus for w in ["dutch", "netherlands", "amsterdam"]):
            resolved["country"] = "NL"
        elif any(w in text_corpus for w in ["swedish", "sweden", "stockholm"]):
            resolved["country"] = "SE"
        elif any(w in text_corpus for w in ["australian", "australia", "sydney", "melbourne"]):
            resolved["country"] = "AU"

    return resolved
