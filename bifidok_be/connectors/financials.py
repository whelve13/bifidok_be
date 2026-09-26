import requests
from typing import Dict, Any, Optional
import yfinance as yf

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_financial_signals(company_name: str) -> Dict[str, Any]:
    """
    Fetches financial metrics using Yahoo Finance Search API & Quote summary / yfinance.
    (Rows 6, 7 of data_api_endpoints.xlsx)
    """
    results = {
        "ticker": None,
        "headcount": None,
        "sector": None,
        "country": None,
        "operating_margin": None,
        "sga_margin_pressure": False,
        "evidence": []
    }

    # Step 1: Resolve Ticker via Yahoo Finance Search API (Row 6)
    try:
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company_name}&quotesCount=1"
        resp = requests.get(search_url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            quotes = resp.json().get("quotes", [])
            if quotes:
                results["ticker"] = quotes[0].get("symbol")
    except Exception:
        pass

    if not results["ticker"]:
        # Fallback heuristic if ticker search didn't return
        results["evidence"].append("Public financial ticker not resolved.")
        return results

    # Step 2: Fetch Financial Ratios & Headcount (Row 7)
    try:
        ticker_obj = yf.Ticker(results["ticker"])
        info = ticker_obj.info or {}
        
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

    except Exception as e:
        results["evidence"].append(f"Financial summary partially retrieved: {str(e)}")

    return results
