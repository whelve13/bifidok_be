import requests
from typing import Dict, Any, Optional

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def resolve_company_entity(company_name: str, domain_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Resolves canonical domain, name and overview using Clearbit Autocomplete and Wikipedia Summary REST API.
    """
    resolved = {
        "name": company_name,
        "domain": domain_hint or "",
        "legal_name": company_name,
        "description": "",
        "country": "EU"
    }

    # 1. Clearbit Autocomplete (Row 44 of XLSX)
    if not resolved["domain"]:
        try:
            url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}"
            resp = requests.get(url, headers=HEADERS, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    clean_first = company_name.lower().split()[0]
                    for item in data:
                        item_name = item.get("name", "").lower()
                        item_dom = item.get("domain", "").lower()
                        if clean_first in item_name or clean_first in item_dom:
                            resolved["domain"] = item.get("domain", "")
                            resolved["name"] = item.get("name", company_name)
                            break
        except Exception:
            pass

    if not resolved["domain"]:
        # Fallback to simple sanitized domain if still empty
        clean_name = company_name.lower().replace(" ", "").replace("-", "").replace("ag", "").replace("se", "")
        resolved["domain"] = f"{clean_name}.com"

    # 2. Wikipedia Summary API (Row 45 of XLSX)
    try:
        wiki_title = resolved["name"].replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}"
        resp = requests.get(url, headers=HEADERS, timeout=4)
        if resp.status_code == 200:
            wdata = resp.json()
            resolved["description"] = wdata.get("extract", "")
            resolved["legal_name"] = wdata.get("title", resolved["name"])
    except Exception:
        pass

    return resolved
