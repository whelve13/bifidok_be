import urllib.parse
import xml.etree.ElementTree as ET
import requests
from typing import List, Dict, Any

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_company_news(company_name: str, custom_keywords: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches real-time European business news and strategic announcements from Google News RSS feeds.
    (Rows 15, 16 of data_api_endpoints.xlsx)
    """
    news_items = []
    
    # Target search queries for sales triggers
    if custom_keywords and len(custom_keywords) > 0:
        kw_str = " OR ".join(custom_keywords[:5])
        queries = [
            f'"{company_name}" ({kw_str})',
            f'{company_name} ({kw_str})'
        ]
    else:
        queries = [
            f'{company_name} (automation OR efficiency OR restructuring OR AI OR cloud)',
            f'{company_name} (Automatisierung OR Stellenabbau OR Kostensenkung)'
        ]

    for q in queries:
        try:
            encoded_query = urllib.parse.quote(q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-GB&gl=GB"
            resp = requests.get(rss_url, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item")[:5]:
                    title_elem = item.find("title")
                    pubdate_elem = item.find("pubDate")
                    link_elem = item.find("link")

                    title = title_elem.text if title_elem is not None else ""
                    pubdate = pubdate_elem.text if pubdate_elem is not None else ""
                    link = link_elem.text if link_elem is not None else ""

                    # Avoid duplicates
                    if any(n["title"] == title for n in news_items):
                        continue

                    news_items.append({
                        "title": title,
                        "pubDate": pubdate,
                        "link": link
                    })
        except Exception:
            pass

    return news_items

def evaluate_news_relevance(news_items: List[Dict[str, Any]], target_keywords: List[str]) -> Dict[str, Any]:
    """
    Evaluates whether the collected news articles contain the target criteria keywords.
    """
    matched = []
    normalized_keywords = [k.lower() for k in target_keywords]

    for item in news_items:
        title_lower = item["title"].lower()
        found_kws = [k for k in normalized_keywords if k in title_lower]
        if found_kws:
            matched.append({
                "title": item["title"],
                "keywords": found_kws,
                "date": item["pubDate"],
                "link": item["link"]
            })

    # Executive & leadership appointment detection
    exec_roles = ["cio", "ciso", "cto", "cdo", "chief information", "chief technology", "chief security", "head of it", "head of security", "new ceo"]
    leadership_matches = []
    for item in news_items:
        t_low = item["title"].lower()
        if any(role in t_low for role in exec_roles) and any(verb in t_low for verb in ["appoint", "name", "join", "hire", "step", "elect"]):
            leadership_matches.append(item)

    return {
        "matched_count": len(matched),
        "articles": matched,
        "is_detected": len(matched) > 0,
        "has_leadership_change": len(leadership_matches) > 0,
        "leadership_articles": leadership_matches,
    }
