"""Service for fetching BSE (Bombay Stock Exchange) filings.

Provides BSE corporate filing data for NIFTY 100 stocks, with focus on
earnings/financial results filings to supplement the earnings signal in
the ReasonEngine.
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


# ── NSE ticker → BSE scrip code mapping (top NIFTY 100 stocks) ────────────
NSE_TO_BSE: Dict[str, str] = {
    "INFY": "500209",
    "TCS": "532540",
    "HDFCBANK": "500180",
    "RELIANCE": "500325",
    "ICICIBANK": "532174",
    "WIPRO": "507685",
    "AXISBANK": "532215",
    "KOTAKBANK": "500247",
    "LT": "500510",
    "BAJFINANCE": "500034",
    "MARUTI": "532500",
    "DMART": "540376",
    "TITAN": "500114",
    "NESTLEIND": "500790",
    "HINDUNILVR": "500696",
    "SBIN": "500112",
    "ITC": "500875",
    "BHARTIARTL": "532454",
    "SUNPHARMA": "524715",
    "HCLTECH": "532281",
    "ASIANPAINT": "500820",
    "ULTRACEMCO": "532538",
    "TATAMOTORS": "500570",
    "BAJAJFINSV": "532978",
    "NTPC": "532555",
    "POWERGRID": "532898",
    "ONGC": "500312",
    "COALINDIA": "533278",
    "DRREDDY": "500124",
    "CIPLA": "500087",
    "TECHM": "532755",
    "HEROMOTOCO": "500182",
    "EICHERMOT": "505200",
    "BRITANNIA": "500825",
    "INDUSINDBK": "532187",
    "DIVISLAB": "532488",
    "JSWSTEEL": "500228",
    "HINDALCO": "500440",
    "GRASIM": "500300",
    "ADANIENT": "512599",
    "TATACONSUM": "500800",
    "APOLLOHOSP": "508869",
    "TATAPOWER": "500400",
    "DLF": "532868",
    "BAJAJ-AUTO": "532977",
    "HAVELLS": "517354",
    "SIEMENS": "500550",
}


BSE_ANNOUNCEMENTS_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
)

BSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com",
}


def get_bse_code(ticker: str) -> Optional[str]:
    """Map NSE ticker (e.g. 'INFY.NS' or 'INFY') to BSE scrip code."""
    symbol = ticker.replace(".NS", "").replace(".BO", "").upper()
    return NSE_TO_BSE.get(symbol)


def fetch_bse_filings(ticker: str, lookback_days: int = 7) -> List[Dict]:
    """Fetch recent corporate filings from BSE for a given stock.

    Args:
        ticker: NSE ticker symbol (e.g. 'INFY.NS')
        lookback_days: How many days back to look

    Returns:
        List of filing dicts with keys: headline, category, filed_at, attachment_url
    """
    scrip_code = get_bse_code(ticker)
    if not scrip_code:
        return []

    today = datetime.now(timezone.utc)
    from_date = (today - timedelta(days=lookback_days)).strftime("%Y%m%d")
    to_date = today.strftime("%Y%m%d")

    try:
        params = {
            "pageno": "1",
            "strCat": "-1",
            "strPrevDate": from_date,
            "strScrip": scrip_code,
            "strSearch": "P",
            "strToDate": to_date,
            "strType": "C",
        }
        resp = requests.get(
            BSE_ANNOUNCEMENTS_URL,
            params=params,
            headers=BSE_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[bse_filings_service] API error for {ticker}: {e}")
        return []

    if not isinstance(data, dict):
        return []

    table = data.get("Table") or []
    filings: List[Dict] = []

    for item in table:
        headline = (item.get("NEWSSUB") or item.get("NEWS_SUBJECT") or "").strip()
        category = (item.get("SUBCATNAME") or item.get("CATEGORYNAME") or "").strip()
        filed_at = (item.get("NEWS_DT") or item.get("DisssemDT") or "").strip()
        attachment_id = item.get("ATTACHMENTNAME") or ""
        attachment_url = ""
        if attachment_id:
            attachment_url = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment_id}"

        filings.append({
            "headline": headline,
            "category": category,
            "filed_at": filed_at,
            "attachment_url": attachment_url,
        })

    return filings


def get_latest_earnings_filing(ticker: str, lookback_days: int = 7) -> Optional[Dict]:
    """Find the most recent earnings/financial results filing for a stock.

    Filters filings where category or headline mentions 'Financial Results'.
    If nothing is found within the initial lookback_days window, progressively
    widens the search to 90, 180, and 365 days so the user always gets the
    latest quarterly results PDF even if it was filed months ago.

    Args:
        ticker: NSE ticker symbol
        lookback_days: Initial number of days back to look

    Returns:
        Most recent earnings filing dict, or None
    """
    EARNINGS_KEYWORDS = ["financial result", "quarterly result", "annual result"]

    # Try progressively wider windows until we find a filing
    windows = sorted(set([lookback_days, 90, 180, 365]))

    for window in windows:
        filings = fetch_bse_filings(ticker, lookback_days=window)
        if not filings:
            continue

        for filing in filings:
            combined = f"{filing.get('category', '')} {filing.get('headline', '')}".lower()
            if any(kw in combined for kw in EARNINGS_KEYWORDS):
                return filing

    return None
