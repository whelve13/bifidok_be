import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_ats_hiring_signals(company_name: str, keywords: List[str] = None) -> Dict[str, Any]:
    """
    Scans public Applicant Tracking Systems (Greenhouse, Lever, Personio)
    for active tech openings matching target criteria (Rows 20, 21, 22 of data_api_endpoints.xlsx).
    """
    if keywords is None:
        keywords = ["uipath", "celonis", "rpa", "process mining", "automation", "ai", "cloud"]

    clean_slug = company_name.lower().replace(" ", "").replace("-", "").replace("ag", "").replace("se", "")
    
    results = {
        "ats_provider": None,
        "total_openings": 0,
        "matched_roles": [],
        "evidence": []
    }

    lowered_kws = [k.lower() for k in keywords]

    # 1. Greenhouse Public Board (Row 20)
    try:
        gh_url = f"https://boards-api.greenhouse.io/v1/boards/{clean_slug}/jobs"
        r = requests.get(gh_url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            data = r.json()
            jobs = data.get("jobs", [])
            results["ats_provider"] = "Greenhouse"
            results["total_openings"] = len(jobs)
            for j in jobs:
                title = j.get("title", "")
                if any(kw in title.lower() for kw in lowered_kws):
                    results["matched_roles"].append(title)
            if results["matched_roles"]:
                results["evidence"].append(
                    f"Greenhouse ATS: Found {len(results['matched_roles'])} target roles (e.g., {results['matched_roles'][:2]})."
                )
            return results
    except Exception:
        pass

    # 2. Lever Public API (Row 21)
    try:
        lever_url = f"https://api.lever.co/v0/postings/{clean_slug}"
        r = requests.get(lever_url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            jobs = r.json()
            if isinstance(jobs, list):
                results["ats_provider"] = "Lever"
                results["total_openings"] = len(jobs)
                for j in jobs:
                    title = j.get("text", "")
                    if any(kw in title.lower() for kw in lowered_kws):
                        results["matched_roles"].append(title)
                if results["matched_roles"]:
                    results["evidence"].append(
                        f"Lever ATS: Found {len(results['matched_roles'])} target roles: {results['matched_roles'][:2]}."
                    )
                return results
    except Exception:
        pass

    # 3. Personio Public XML (Row 22)
    try:
        personio_url = f"https://{clean_slug}.jobs.personio.de/xml"
        r = requests.get(personio_url, headers=HEADERS, timeout=3)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            positions = root.findall(".//position")
            results["ats_provider"] = "Personio"
            results["total_openings"] = len(positions)
            for p in positions:
                name_elem = p.find("name")
                if name_elem is not None and name_elem.text:
                    title = name_elem.text
                    if any(kw in title.lower() for kw in lowered_kws):
                        results["matched_roles"].append(title)
            if results["matched_roles"]:
                results["evidence"].append(
                    f"Personio ATS: Found {len(results['matched_roles'])} target roles."
                )
            return results
    except Exception:
        pass

    # Fallback: Query Google News for public recruitment and hiring signals
    try:
        import urllib.parse
        kw_filter = " OR ".join(keywords[:5]) if keywords else "hiring OR vacancies"
        q = urllib.parse.quote(f"{company_name} (hiring OR recruitment OR vacancies) ({kw_filter})")
        url = f"https://news.google.com/rss/search?q={q}&hl=en-GB&gl=GB"
        resp = requests.get(url, headers=HEADERS, timeout=3)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            for it in items[:3]:
                t = it.find("title").text if it.find("title") is not None else ""
                results["matched_roles"].append(t)
            if results["matched_roles"]:
                results["ats_provider"] = "Public Press / Career Disclosures"
                results["total_openings"] = len(results["matched_roles"])
                results["evidence"].append(
                    f"Recruitment Signals detected in press: {results['matched_roles'][0][:60]}..."
                )
                return results
    except Exception:
        pass

    results["evidence"].append("Enterprise ATS is custom hosted or private.")
    return results
