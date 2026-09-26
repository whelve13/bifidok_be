"""
GDELT 2.0 Doc API Connector.
Retrieves real-time global news coverage and strategic business events.
"""
import json
import logging
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_gdelt_signals(
    company_name: str,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Queries the GDELT Doc 2.0 API for news articles and mentions for a given company.
    Endpoint: https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&maxrecords=5&format=json

    Args:
        company_name: Name of the target company.
        keywords: Optional list of signal trigger keywords.

    Returns:
        List of structured article dicts:
        [{"title": ..., "url": ..., "seendate": ..., "domain": ..., "raw_text": ...}]
    """
    clean_name = company_name.strip().strip("\"'")
    if not clean_name:
        return []

    if keywords and len(keywords) > 0:
        cleaned_kw = [k.strip() for k in keywords if k.strip()]
        if cleaned_kw:
            kw_part = " OR ".join(cleaned_kw[:5])
            query = f'"{clean_name}" ({kw_part})'
        else:
            query = f'"{clean_name}"'
    else:
        query = f'"{clean_name}"'

    encoded_query = urllib.parse.quote(query)
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={encoded_query}&mode=ArtList&maxrecords=5&format=json"

    results: List[Dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=6)
        if resp.status_code == 200 and resp.text.strip():
            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError):
                logger.warning("GDELT response was not valid JSON for query: %s", query)
                return []

            articles = data.get("articles", [])
            for art in articles[:5]:
                title = art.get("title", "") or ""
                article_url = art.get("url", "") or ""
                seendate = art.get("seendate", "") or ""
                domain = art.get("domain", "") or ""
                raw_text = art.get("raw_text") or art.get("snippet") or title or ""

                results.append({
                    "title": title,
                    "url": article_url,
                    "seendate": seendate,
                    "domain": domain,
                    "raw_text": raw_text,
                })
        else:
            logger.info("GDELT API returned status %s for query: %s", resp.status_code, query)
    except Exception as exc:
        logger.warning("Failed to fetch GDELT signals for '%s': %s", company_name, exc)

    return results
