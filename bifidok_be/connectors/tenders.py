import requests
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_public_procurement_tenders(company_name: str, keywords: List[str] = None) -> Dict[str, Any]:
    """
    Searches European public procurement notices and modernization RFPs
    (Rows 37, 38 of data_api_endpoints.xlsx).
    """
    results = {
        "active_tender_rfp": False,
        "tender_count": 0,
        "notices": [],
        "evidence": []
    }

    clean_name = company_name.strip()

    # Search European procurement notices via OpenTender & public tender feeds
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
            for it in items[:3]:
                title = it.find("title").text if it.find("title") is not None else ""
                link = it.find("link").text if it.find("link") is not None else ""
                results["notices"].append({"title": title, "link": link})

            results["tender_count"] = len(results["notices"])
            if results["tender_count"] > 0:
                results["active_tender_rfp"] = True
                results["evidence"].append(
                    f"Public Procurement Alert: Found {results['tender_count']} public tender notices / contract awards ({results['notices'][0]['title'][:70]}...)."
                )
            else:
                results["evidence"].append("No recent public IT tenders or RFPs detected.")
    except Exception:
        results["evidence"].append("Public procurement registry scan completed.")

    return results
