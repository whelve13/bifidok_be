import re
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

    # Strip common corporate suffixes at word boundaries without damaging company names (e.g. Volkswagen, Siemens)
    slug_base = re.sub(r'\b(ag|se|gmbh|sa|holding|group|corp|inc|co|plc|nv|bv)\b', '', company_name, flags=re.IGNORECASE)
    clean_slug = re.sub(r'[^a-zA-Z0-9]', '', slug_base).lower()
    
    results = {
        "ats_provider": None,
        "total_openings": 0,
        "matched_roles": [],
        "evidence": [],
        "is_remote_first": False,
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
            if len(jobs) >= 5:
                remote_count = sum(
                    1 for j in jobs if "remote" in (j.get("location", {}).get("name") or "").lower()
                )
                if (remote_count / len(jobs)) >= 0.70:
                    results["is_remote_first"] = True
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
                if len(jobs) >= 5:
                    remote_count = sum(
                        1
                        for j in jobs
                        if "remote" in str(j.get("categories", {}).get("location", "")).lower()
                        or "remote" in j.get("text", "").lower()
                    )
                    if (remote_count / len(jobs)) >= 0.70:
                        results["is_remote_first"] = True
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
            results["hiring_velocity_score"] = min(1.0, (len(results["matched_roles"]) * 0.25) + 0.2)
            return results
    except Exception:
        pass

    # 4. SmartRecruiters Public Postings API
    try:
        sr_url = f"https://api.smartrecruiters.com/v1/companies/{clean_slug}/postings?limit=25"
        r = requests.get(sr_url, headers=HEADERS, timeout=2)
        if r.status_code == 200:
            sr_data = r.json()
            postings = sr_data.get("content", [])
            if postings:
                results["ats_provider"] = "SmartRecruiters"
                results["total_openings"] = len(postings)
                for p in postings:
                    title = p.get("name", "")
                    if any(kw in title.lower() for kw in lowered_kws):
                        results["matched_roles"].append(title)
                if results["matched_roles"]:
                    results["evidence"].append(
                        f"SmartRecruiters ATS: Found {len(results['matched_roles'])} target roles (e.g. {results['matched_roles'][:2]})."
                    )
                results["hiring_velocity_score"] = min(1.0, (len(results["matched_roles"]) * 0.25) + 0.2)
                return results
    except Exception:
        pass

    # 5. Ashby Public Job Board API
    try:
        ashby_url = f"https://api.ashbyhq.com/posting-api/job-board/{clean_slug}"
        r = requests.get(ashby_url, headers=HEADERS, timeout=2)
        if r.status_code == 200:
            ashby_data = r.json()
            jobs = ashby_data.get("jobs", [])
            if jobs:
                results["ats_provider"] = "Ashby"
                results["total_openings"] = len(jobs)
                for j in jobs:
                    title = j.get("title", "")
                    if any(kw in title.lower() for kw in lowered_kws):
                        results["matched_roles"].append(title)
                if results["matched_roles"]:
                    results["evidence"].append(
                        f"Ashby ATS: Found {len(results['matched_roles'])} target roles (e.g. {results['matched_roles'][:2]})."
                    )
                results["hiring_velocity_score"] = min(1.0, (len(results["matched_roles"]) * 0.25) + 0.2)
                return results
    except Exception:
        pass

    # 6. Fallback: Query Google News for public recruitment and hiring signals
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
                results["hiring_velocity_score"] = min(1.0, len(results["matched_roles"]) * 0.2)
                return results
    except Exception:
        pass

    results["hiring_velocity_score"] = 0.0
    results["evidence"].append("Enterprise ATS is custom hosted or private.")
    return results
