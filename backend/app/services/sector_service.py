"""Service for sector analysis and context."""
from typing import Dict, Optional
import yfinance as yf
from app.services.spike_service import get_top_movers


SECTOR_MAP = {
    "TCS.NS": "^CNXIT",
    "INFY.NS": "^CNXIT",
    "HCLTECH.NS": "^CNXIT",
    "WIPRO.NS": "^CNXIT",
    "TECHM.NS": "^CNXIT",
    "HDFCBANK.NS": "^NSEBANK",
    "ICICIBANK.NS": "^NSEBANK",
    "SBIN.NS": "^NSEBANK",
    "KOTAKBANK.NS": "^NSEBANK",
    "AXISBANK.NS": "^NSEBANK",
    "RELIANCE.NS": "^CNXENERGY",
    "ONGC.NS": "^CNXENERGY",
    "NTPC.NS": "^CNXENERGY",
    "TATAPOWER.NS": "^CNXENERGY",
}

DEFAULT_SECTOR = "^NSEI"


def get_sector_for_ticker(ticker: str) -> Optional[str]:
    """Get the sector and sub-sector index for a ticker."""
    return SECTOR_MAP.get(ticker, DEFAULT_SECTOR)


def get_sector_movement(sector_ticker: str, lookback_days: int = 1) -> Optional[float]:
    """
    Get sector index movement for comparison.
    
    Returns:
        Percentage change of sector
    """
    try:
        period = f"{max(lookback_days, 1)}d"
        movement = get_top_movers([sector_ticker], days=lookback_days).get("movement", {})
        val = movement.get(sector_ticker)
        if val is not None:
            return val
    except Exception as e:
        pass

    try:
        data = yf.download(sector_ticker, period=period, interval="1d", progress=False)
        if data.empty:
            return None
        open_first = float(data["Open"].iloc[0].squeeze())
        close_last = float(data["Close"].iloc[-1].squeeze())
        return ((close_last - open_first) / open_first) * 100.0 if open_first else 0.0
    except Exception as e:
        print(f"Sector error: {e}")
        return None


def compare_stock_to_sector(stock_ticker: str, stock_change: float, lookback_days: int = 1) -> Dict:
    """
    Compare stock movement relative to sector.
    
    Returns:
        Dict with sector ticker, sector change, relative outperformance
    """
    sector_ticker = get_sector_for_ticker(stock_ticker)
    sector_change = get_sector_movement(sector_ticker, lookback_days) if sector_ticker else None
    relative = None
    fired = False
    if sector_change is not None:
        relative = stock_change - sector_change
        fired = abs(sector_change) >= 0.8

    return {
        "fired": fired,
        "sector_ticker": sector_ticker,
        "sector_change_pct": round(sector_change, 2) if sector_change is not None else None,
        "relative_performance_pct": round(relative, 2) if relative is not None else None,
    }

