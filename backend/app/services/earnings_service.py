"""Service for extracting and analyzing earnings data."""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
import yfinance as yf
import pandas as pd


def get_latest_earnings(ticker: str) -> Optional[Dict]:
    """
    Extract latest quarterly earnings from yfinance.
    
    Returns:
        Dict with earnings data or None if not available
    """
    try:
        t = yf.Ticker(ticker)
        qf = t.quarterly_financials
        if qf is None or qf.empty:
            return None

        latest_col = qf.columns[0]
        latest = qf[latest_col]

        return {
            "quarter_end": latest_col.date().isoformat() if hasattr(latest_col, "date") else str(latest_col),
            "total_revenue": float(latest.get("Total Revenue")) if pd.notna(latest.get("Total Revenue")) else None,
            "net_income": float(latest.get("Net Income")) if pd.notna(latest.get("Net Income")) else None,
            "operating_income": float(latest.get("Operating Income")) if pd.notna(latest.get("Operating Income")) else None,
            "gross_profit": float(latest.get("Gross Profit")) if pd.notna(latest.get("Gross Profit")) else None,
            "ebitda": float(latest.get("EBITDA")) if pd.notna(latest.get("EBITDA")) else (float(latest.get("Normalized EBITDA")) if pd.notna(latest.get("Normalized EBITDA")) else None),
        }
    except Exception:
        return None


def check_earnings_release(ticker: str, lookback_days: int = 1) -> Tuple[bool, Optional[Dict]]:
    """
    Check if earnings were released within lookback period.
    
    Returns:
        (released: bool, earnings_data: Dict or None)
    """
    try:
        t = yf.Ticker(ticker)
        cal = t.calendar
        latest_earnings = get_latest_earnings(ticker)
        if cal is None or cal.empty:
            return False, latest_earnings

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)

        # Try common yfinance calendar fields
        for key in ["Earnings Date", "Earnings", "Ex-Dividend Date"]:
            if key in cal.index:
                value = cal.loc[key]
                if isinstance(value, pd.Series):
                    dt = pd.to_datetime(value.iloc[0], utc=True, errors="coerce")
                else:
                    dt = pd.to_datetime(value, utc=True, errors="coerce")
                if pd.notna(dt) and dt.to_pydatetime() >= cutoff:
                    payload = latest_earnings or {}
                    payload["calendar_event"] = key
                    payload["calendar_date"] = dt.date().isoformat()
                    return True, payload
        return False, latest_earnings
    except Exception:
        return False, get_latest_earnings(ticker)


def calculate_beat_miss(actual: float, estimate: float) -> Tuple[str, float]:
    """
    Calculate if earnings beat or missed estimates.
    
    Returns:
        (direction: "beat" or "miss", pct_difference: float)
    """
    if estimate == 0:
        return "beat", 0.0
    diff_pct = ((actual - estimate) / abs(estimate)) * 100.0
    return ("beat" if diff_pct >= 0 else "miss", abs(diff_pct))
