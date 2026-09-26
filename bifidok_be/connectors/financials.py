import logging
import requests
from typing import Dict, Any, Optional
import yfinance as yf
from services.cache import get_cache, set_cache

try:
    from services.proxy_manager import get_resilient_session, resilient_get
except ImportError:
    from bifidok_be.services.proxy_manager import get_resilient_session, resilient_get

logger = logging.getLogger(__name__)


def fetch_financial_signals(company_name: str) -> Dict[str, Any]:
    """
    Fetches financial metrics using Yahoo Finance Search API & Quote summary / yfinance.
    (Rows 6, 7 of data_api_endpoints.xlsx)
    Checks Redis / TTL cache before executing external queries, caching responses for 24 hours.
    """
    results = {
        "ticker": None,
        "headcount": None,
        "sector": None,
        "country": None,
        "operating_margin": None,
        "sga_margin_pressure": False,
        "evidence": [],
    }

    session = get_resilient_session()

    # Step 1: Resolve Ticker via Yahoo Finance Search API (Row 6)
    search_cache_key = f"cache:yahoo_search:{company_name.strip().lower()}"
    cached_search = get_cache(search_cache_key)

    quotes = []
    if cached_search is not None:
        quotes = cached_search.get("quotes", []) if isinstance(cached_search, dict) else []
    else:
        try:
            search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}&quotesCount=1"
            resp = resilient_get(search_url, requests_get_fn=requests.get, session=session, timeout=5)
            if resp.status_code == 200:
                search_data = resp.json()
                set_cache(search_cache_key, search_data, ttl=86400)
                quotes = search_data.get("quotes", [])
        except Exception as exc:
            logger.debug("Yahoo Finance search failed for %s: %s", company_name, exc)

    if quotes:
        results["ticker"] = quotes[0].get("symbol")

    if not results["ticker"]:
        # Fallback heuristic if ticker search didn't return
        results["evidence"].append("Public financial ticker not resolved.")
        return results

    # Step 2: Fetch Financial Ratios & Headcount (Row 7)
    ticker_str = str(results["ticker"]).strip().upper()
    info_cache_key = f"cache:yahoo_info:{ticker_str}"
    cached_info = get_cache(info_cache_key)

    info = {}
    if cached_info is not None and isinstance(cached_info, dict):
        info = cached_info
    else:
        try:
            ticker_obj = yf.Ticker(results["ticker"])
            raw_info = ticker_obj.info or {}
            if raw_info:
                info = raw_info
                set_cache(info_cache_key, info, ttl=86400)
        except Exception as e:
            results["evidence"].append(f"Financial summary partially retrieved: {str(e)}")

    headcount = info.get("fullTimeEmployees")
    sector = info.get("sector") or info.get("industry")
    country = info.get("country")
    op_margin = info.get("operatingMargins")

    results["headcount"] = headcount
    results["sector"] = sector
    results["country"] = country
    results["operating_margin"] = op_margin

    # Evaluate margin pressure / SG&A overhead trigger
    if op_margin is not None:
        if op_margin < 0.15:
            results["sga_margin_pressure"] = True
            results["evidence"].append(
                f"Operating margin is compressed at {op_margin*100:.1f}%, indicating operational overhead pressure."
            )
        else:
            results["evidence"].append(
                f"Audited operating margin is healthy at {op_margin*100:.1f}%."
            )

    if headcount:
        results["evidence"].append(f"Enterprise headcount: {headcount:,} full-time employees.")

    return results
