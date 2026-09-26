import requests
from typing import Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_CISA_CACHE = None

def get_cisa_vulnerabilities() -> List[Dict[str, Any]]:
    global _CISA_CACHE
    if _CISA_CACHE is not None:
        return _CISA_CACHE
    try:
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            _CISA_CACHE = resp.json().get("vulnerabilities", [])
            return _CISA_CACHE
    except Exception:
        pass
    return []

def evaluate_vulnerability_exposure(discovered_subdomains: List[str], tech_stack: List[str] = None) -> Dict[str, Any]:
    """
    Cross-references discovered company subdomains and software tooling with CISA Known Exploited
    Vulnerabilities (KEV) to trigger urgent Managed SOC outreach hooks (Row 28 of data_api_endpoints.xlsx).
    """
    vulns = get_cisa_vulnerabilities()
    results = {
        "active_kev_count": 0,
        "matched_cves": [],
        "has_critical_exposure": False,
        "evidence": []
    }

    if not vulns:
        return results

    # Targets to match against CISA KEV
    keywords = ["citrix", "vpn", "fortinet", "sap", "gitlab", "jira", "cisco", "paloalto"]
    detected_vendors = set()

    for sub in discovered_subdomains:
        for kw in keywords:
            if kw in sub.lower():
                detected_vendors.add(kw)

    if tech_stack:
        for t in tech_stack:
            for kw in keywords:
                if kw in t.lower():
                    detected_vendors.add(kw)

    # Search in CISA KEV
    for v in vulns:
        vendor = v.get("vendorProject", "").lower()
        if any(dv in vendor for dv in detected_vendors):
            results["matched_cves"].append({
                "cveID": v.get("cveID"),
                "vendor": v.get("vendorProject"),
                "product": v.get("product"),
                "name": v.get("vulnerabilityName")
            })

    results["active_kev_count"] = len(results["matched_cves"])
    if results["matched_cves"]:
        results["has_critical_exposure"] = True
        top = results["matched_cves"][0]
        results["evidence"].append(
            f"CISA KEV Alert: Discovered {len(results['matched_cves'])} weaponized vulnerabilities affecting exposed stack ({top['vendor']} {top['product']} - {top['cveID']})."
        )
    else:
        results["evidence"].append("No active weaponized CISA KEV zero-days detected on current external assets.")

    return results
