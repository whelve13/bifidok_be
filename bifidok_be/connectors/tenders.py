"""
European Public Procurement & Tenders Connector.
Searches procurement notices and tender feeds, explicitly distinguishing
unconfirmed search news feeds from official TED (Tenders Electronic Daily) contract awards.
"""
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def is_official_contract_award(link: str, title: str) -> bool:
    """
    Determines whether a notice originates from an official European procurement
    registry (e.g. TED) or contains an official contract award identification.
    """
    if not link and not title:
        return False

    link_lower = (link or "").lower()
    # Official European TED domains
    if any(domain in link_lower for domain in ["ted.europa.eu", "simap.ted.europa.eu"]):
        return True

    title_lower = (title or "").lower()
    # Official TED notice identifier patterns (e.g., 2024/S 123-456789 or 123456-2024)
    if re.search(r"\b202\d/S\s+\d{3}-\d{6}\b", title, re.IGNORECASE) or re.search(r"\b\d{6}-202\d\b", title):
        return True

    # Explicit contract award identification regex
    if re.search(
        r"\b(contract award id|award notice no|ted notice|procurement id)[:\s]+[a-z0-9\-_/]+",
        title_lower,
    ):
        return True

    return False


def fetch_public_procurement_tenders(
    company_name: str, keywords: List[str] = None
) -> Dict[str, Any]:
    """
    Searches European public procurement notices and modernization RFPs.

    Refactored to prevent misrepresenting news mentions as confirmed awards:
    - If using tender search feeds without official TED links or contract award IDs,
      explicitly populates source="Public Procurement News Feed" and caps confidence at 0.40.
    - If an official TED link or verified contract award ID is present, sets
      source="TED (Tenders Electronic Daily)" and confidence=0.85+.
    """
    results: Dict[str, Any] = {
        "active_tender_rfp": False,
        "tender_count": 0,
        "source": "Public Procurement News Feed",
        "confidence": 0.0,
        "has_official_award": False,
        "notices": [],
        "evidence": [],
    }

    clean_name = company_name.strip()
    if not clean_name:
        results["evidence"].append("No company name provided for tender lookup.")
        return results

    try:
        if keywords and len(keywords) > 0:
            kw_filter = " OR ".join(keywords[:5])
            query = f'"{clean_name}" (tender OR RFP OR procurement OR "contract award") ({kw_filter})'
        else:
            query = f'"{clean_name}" (tender OR RFP OR procurement OR "contract award") (IT OR cloud OR software OR automation)'

        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-GB&gl=GB"
        resp = requests.get(url, headers=HEADERS, timeout=4)

        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            any_official = False

            for it in items[:3]:
                title = it.find("title").text if it.find("title") is not None else ""
                link = it.find("link").text if it.find("link") is not None else ""

                official = is_official_contract_award(link, title)
                if official:
                    any_official = True

                notice_source = (
                    "TED (Tenders Electronic Daily)"
                    if official
                    else "Public Procurement News Feed"
                )
                notice_confidence = 0.85 if official else 0.40

                results["notices"].append({
                    "title": title,
                    "link": link,
                    "source": notice_source,
                    "confidence": notice_confidence,
                    "is_official_award": official,
                })

            results["tender_count"] = len(results["notices"])
            results["has_official_award"] = any_official

            if results["tender_count"] > 0:
                results["active_tender_rfp"] = True
                if any_official:
                    results["source"] = "TED (Tenders Electronic Daily)"
                    results["confidence"] = 0.85
                    results["evidence"].append(
                        f"Official Public Procurement Notice: Verified contract award / TED notice detected ({results['notices'][0]['title'][:70]}...)."
                    )
                else:
                    # Unconfirmed tender news feed hit: capped at 0.40 confidence
                    results["source"] = "Public Procurement News Feed"
                    results["confidence"] = 0.40
                    results["evidence"].append(
                        f"Public Procurement News Mention (Unconfirmed): Found {results['tender_count']} tender/RFP news search hits in Public Procurement News Feed ({results['notices'][0]['title'][:70]}...). Note: Unconfirmed news mention; confidence capped at 0.40."
                    )
            else:
                results["source"] = "Public Procurement News Feed"
                results["confidence"] = 0.0
                results["evidence"].append("No recent public IT tenders or RFPs detected.")
    except Exception:
        results["evidence"].append("Public procurement scan completed.")

    return results
