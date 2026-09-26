import logging
import re
import requests
from typing import Dict, Any, Optional, List
import yfinance as yf
from services.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


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

    # Step 1: Resolve Ticker via Yahoo Finance Search API (Row 6)
    search_cache_key = f"cache:yahoo_search:{company_name.strip().lower()}"
    cached_search = get_cache(search_cache_key)

    quotes: List[Dict[str, Any]] = []
    if cached_search is not None and isinstance(cached_search, dict):
        quotes = cached_search.get("quotes", [])
    else:
        # Search queries to try: original name, and name with corporate legal suffixes stripped
        slug_base = re.sub(
            r'\b(ag|se|gmbh|sa|holding|group|corp|inc|co|plc|nv|bv)\b',
            '',
            company_name,
            flags=re.IGNORECASE,
        ).strip()
        queries_to_try = [company_name]
        if slug_base and slug_base.lower() != company_name.lower():
            queries_to_try.append(slug_base)

        for q in queries_to_try:
            try:
                search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(q)}&quotesCount=5"
                resp = requests.get(search_url, headers=HEADERS, timeout=5)
                if resp.status_code == 200:
                    search_data = resp.json()
                    curr_quotes = search_data.get("quotes", [])
                    if curr_quotes:
                        quotes.extend(curr_quotes)
                        set_cache(search_cache_key, search_data, ttl=86400)
                        break
            except Exception as exc:
                logger.debug("Yahoo Finance search failed for %s: %s", q, exc)

    # Prioritize equity quotes
    candidate_symbols = []
    for q in quotes:
        sym = q.get("symbol")
        qtype = str(q.get("quoteType", "")).upper()
        if sym:
            if qtype == "EQUITY":
                candidate_symbols.insert(0, sym)
            else:
                candidate_symbols.append(sym)

    if not candidate_symbols:
        results["evidence"].append("Public financial ticker not resolved.")
        return results

    # Step 2: Fetch Financial Ratios & Headcount (Row 7)
    info = {}
    chosen_symbol = candidate_symbols[0]

    for sym in candidate_symbols[:3]:
        ticker_str = str(sym).strip().upper()
        info_cache_key = f"cache:yahoo_info:{ticker_str}"
        cached_info = get_cache(info_cache_key)

        if cached_info is not None and isinstance(cached_info, dict):
            curr_info = cached_info
        else:
            try:
                ticker_obj = yf.Ticker(sym)
                curr_info = ticker_obj.info or {}
                if curr_info:
                    set_cache(info_cache_key, curr_info, ttl=86400)
            except Exception as e:
                curr_info = {}

        if curr_info.get("fullTimeEmployees") or curr_info.get("operatingMargins") is not None:
            info = curr_info
            chosen_symbol = sym
            break
        elif not info and curr_info:
            info = curr_info
            chosen_symbol = sym

    results["ticker"] = chosen_symbol

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
