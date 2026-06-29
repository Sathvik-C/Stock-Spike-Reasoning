"""Service for detecting top movers and price spikes."""
import contextlib
import io
# pyrefly: ignore [missing-import]
import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional, Tuple


def _movement_from_close_series(close_series: pd.Series, days: int) -> Optional[float]:
    series = close_series.dropna()
    if series.empty:
        return None
    if len(series) == 1:
        return 0.0

    window = days + 1
    start = float(series.iloc[-window]) if len(series) >= window else float(series.iloc[0])
    end = float(series.iloc[-1])
    if start == 0:
        return None
    return ((end - start) / start) * 100.0


def get_top_movers(tickers: List[str], days: int = 1, top_n: int = 5) -> Dict:
    """
    Get top gainers and losers for a list of tickers over a period.
    
    Args:
        tickers: List of ticker symbols
        days: Lookback period in days
        top_n: Number of top gainers/losers to return
    
    Returns:
        Dict with gainers, losers, and full movement data
    """
    try:
        period = f"{max(days + 7, 10)}d"

        # yfinance prints failed symbols to stderr; keep API logs clean.
        with contextlib.redirect_stderr(io.StringIO()):
            data = yf.download(tickers, period=period, interval="1d", group_by="column", progress=False)

        if data.empty or "Close" not in data:
            return {"gainers": [], "losers": [], "movement": {}, "error": "No data found."}

        close_data = data["Close"]
        movement_map: Dict[str, float] = {}

        if isinstance(close_data, pd.Series):
            if tickers:
                mv = _movement_from_close_series(close_data, days)
                if mv is not None:
                    movement_map[tickers[0]] = round(mv, 2)
        else:
            for ticker in close_data.columns:
                mv = _movement_from_close_series(close_data[ticker], days)
                if mv is not None:
                    movement_map[ticker] = round(mv, 2)

        if not movement_map:
            return {"gainers": [], "losers": [], "movement": {}, "error": "No valid ticker movement found."}

        movement = pd.Series(movement_map).sort_values(ascending=False)

        gainers = movement.head(top_n).round(2)
        losers = movement.tail(top_n).sort_values(ascending=True).round(2)

        return {
            "gainers": gainers.to_dict(),
            "losers": losers.to_dict(),
            "movement": movement.round(2).to_dict(),
        }
    except Exception as exc:
        return {"gainers": [], "losers": [], "movement": {}, "error": str(exc)}


import time
import threading

_data_cache: Dict[str, Tuple[float, Optional[pd.DataFrame]]] = {}
_DATA_CACHE_TTL = 300  # 5 minutes
_yf_lock = threading.Lock()

def get_recent_data(ticker: str, period: str = "7d", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Fetch recent price data for a ticker with in-memory caching.
    
    Args:
        ticker: Stock ticker symbol
        period: Historical period (1d, 5d, 1mo, etc.)
        interval: Data interval (1d for daily)
    
    Returns:
        DataFrame with OHLCV data
    """
    cache_key = f"{ticker}_{period}_{interval}"
    cached = _data_cache.get(cache_key)
    if cached and time.time() - cached[0] < _DATA_CACHE_TTL:
        df = cached[1]
        return df.copy() if df is not None else None

    with _yf_lock:
        try:
            t = yf.Ticker(ticker)
            with contextlib.redirect_stderr(io.StringIO()):
                df = t.history(period=period, interval=interval)
            
            # Fallback for yfinance bug where 1d returns empty for Indian stocks
            if df.empty and period == "1d" and interval == "5m":
                with contextlib.redirect_stderr(io.StringIO()):
                    df = t.history(period="5d", interval="5m")

            if df.empty:
                _data_cache[cache_key] = (time.time(), None)
                return None
            df["PctChange"] = df["Close"].pct_change() * 100
            _data_cache[cache_key] = (time.time(), df)
            return df.copy()
        except Exception:
            return None


def detect_spike(df: pd.DataFrame, threshold: float = 2.0) -> Tuple[bool, Optional[float]]:
    """
    Detect if latest data point shows spike above threshold.
    
    Args:
        df: Price DataFrame
        threshold: Percentage threshold for spike detection
    
    Returns:
        Boolean indicating spike detection
    """
    if df is None or df.empty or "PctChange" not in df.columns:
        return False, None
    last_change = df["PctChange"].iloc[-1]
    is_spike = abs(last_change) >= threshold
    return is_spike, float(last_change)
