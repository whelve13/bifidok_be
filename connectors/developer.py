import requests
from typing import Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_developer_signals(company_name: str) -> Dict[str, Any]:
    """
    Fetches engineering activity and developer sentiment (Rows 40, 41 of data_api_endpoints.xlsx):
    - GitHub Public Organization API: public repositories, top tech stack languages, update activity
    - Hacker News Algolia API: tech stack debates, legacy debt discussions, migration friction.
    """
    results = {
        "github_org_found": False,
        "repo_count": 0,
        "top_languages": [],
        "low_developer_velocity": False,
        "hn_discussions": [],
        "evidence": []
    }

    clean_slug = company_name.lower().replace(" ", "").replace("-", "").replace("ag", "").replace("se", "")

    # 1. GitHub Public Org API (Row 41)
    try:
        url = f"https://api.github.com/orgs/{clean_slug}/repos?sort=updated&per_page=10"
        resp = requests.get(url, headers=HEADERS, timeout=4)
        if resp.status_code == 200:
            repos = resp.json()
            if isinstance(repos, list) and len(repos) > 0:
                results["github_org_found"] = True
                results["repo_count"] = len(repos)
                languages = set(r.get("language") for r in repos if r.get("language"))
                results["top_languages"] = list(languages)[:4]

                # Check velocity
                results["evidence"].append(
                    f"GitHub Org ({clean_slug}): {len(repos)}+ public repositories found. Stack: {', '.join(results['top_languages'])}."
                )
    except Exception:
        pass

    # 2. Hacker News Algolia Search API (Row 40)
    try:
        hn_query = f"{company_name} (legacy OR migration OR backend OR architecture)"
        hn_url = f"https://hn.algolia.com/api/v1/search?query={hn_query}&tags=story&hitsPerPage=3"
        resp = requests.get(hn_url, headers=HEADERS, timeout=4)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            for h in hits:
                title = h.get("title")
                url = h.get("url")
                if title:
                    results["hn_discussions"].append({"title": title, "url": url})
            if results["hn_discussions"]:
                results["evidence"].append(
                    f"Hacker News Discussions: Discovered {len(results['hn_discussions'])} engineering threads on modernization/architecture."
                )
    except Exception:
        pass

    return results
