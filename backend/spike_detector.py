import yfinance as yf
import pandas as pd
from typing import Optional, Tuple

def get_recent_data(ticker: str, period: str = "7d", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch stock data from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            return None
        df["PctChange"] = df["Close"].pct_change() * 100
        return df
    except Exception:
        return None

def detect_spike(df: pd.DataFrame, threshold: float) -> Tuple[bool, Optional[float]]:
    """Detect if a spike happened within threshold range."""
    if df is None or df.empty or "PctChange" not in df.columns:
        return False, None
    last_change = df["PctChange"].iloc[-1]
    is_spike = abs(last_change) >= threshold
    return is_spike, last_change
