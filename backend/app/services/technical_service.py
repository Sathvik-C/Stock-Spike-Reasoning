"""Service for technical analysis indicators via pandas-ta."""
from typing import Dict, Optional, Tuple
import math
import pandas as pd

try:
    import pandas_ta as ta
    _HAS_PANDAS_TA = True
except Exception:
    ta = None
    _HAS_PANDAS_TA = False


def _manual_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _safe_float(value):
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _latest_matching_column(frame: pd.DataFrame, prefixes) -> Optional[float]:
    for column in frame.columns:
        if any(str(column).startswith(prefix) for prefix in prefixes):
            return _safe_float(frame[column].iloc[-1])
    return None


def calculate_technical_signals(price_df: pd.DataFrame) -> Dict:
    """
    Calculate technical indicators: RSI, MACD, Bollinger Bands, Volume ratio.
    
    Args:
        price_df: DataFrame with OHLCV data
    
    Returns:
        Dict with all technical signals
    """
    if price_df is None or price_df.empty:
        return {}

    df = price_df.copy()
    close = df["Close"]

    if _HAS_PANDAS_TA:
        rsi_series = ta.rsi(close, length=14)
        macd_df = ta.macd(close)
        bb_df = ta.bbands(close, length=20)
    else:
        rsi_series = _manual_rsi(close, period=14)
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_df = pd.DataFrame({"MACD_12_26_9": macd_line, "MACDs_12_26_9": signal_line})
        ma = close.rolling(20).mean()
        std = close.rolling(20).std()
        bb_df = pd.DataFrame({"BBU_20_2.0": ma + 2 * std, "BBL_20_2.0": ma - 2 * std})

    current_close = float(close.iloc[-1])
    current_volume = float(df["Volume"].iloc[-1]) if "Volume" in df.columns and not df["Volume"].empty else 0.0
    avg_volume_20 = float(df["Volume"].tail(20).mean()) if "Volume" in df.columns and not df["Volume"].empty else 0.0
    volume_ratio = (current_volume / avg_volume_20) if avg_volume_20 else 0.0

    macd_signal = "neutral"
    if macd_df is not None and not macd_df.empty:
        last_macd = float(macd_df["MACD_12_26_9"].iloc[-1])
        last_signal = float(macd_df["MACDs_12_26_9"].iloc[-1])
        if last_macd > last_signal:
            macd_signal = "bullish"
        elif last_macd < last_signal:
            macd_signal = "bearish"

    bb_position = "middle"
    if bb_df is not None and not bb_df.empty:
        upper = _latest_matching_column(bb_df, ("BBU_", "BBU"))
        lower = _latest_matching_column(bb_df, ("BBL_", "BBL"))
        if upper is not None and current_close >= upper:
            bb_position = "upper"
        elif lower is not None and current_close <= lower:
            bb_position = "lower"

    try:
        ma_20 = float(close.rolling(20).mean().iloc[-1])
        ma_50 = float(close.rolling(50).mean().iloc[-1])
        ma_200 = float(close.rolling(200).mean().iloc[-1])
        
        trend = "uptrend" if (current_close > ma_20 > ma_50) else \
                "downtrend" if (current_close < ma_20 < ma_50) else "sideways"
    except Exception:
        ma_20 = ma_50 = ma_200 = None
        trend = "sideways"

    try:
        if _HAS_PANDAS_TA and "High" in df.columns and "Low" in df.columns:
            atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=14)
            atr_value = float(atr_series.iloc[-1]) if atr_series is not None else 0.0
        elif "High" in df.columns and "Low" in df.columns:
            atr_value = float((df["High"] - df["Low"]).rolling(14).mean().iloc[-1])
        else:
            atr_value = 0.0
        atr_pct = (atr_value / current_close) * 100 if current_close else 0.0
    except Exception:
        atr_pct = 0.0

    try:
        high_52w = float(close.tail(252).max())
        low_52w = float(close.tail(252).min())
        position_52w = (current_close - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else 0.5
    except Exception:
        high_52w = low_52w = position_52w = None

    try:
        recent_high_20d = float(close.tail(20).max())
        recent_low_20d = float(close.tail(20).min())
        near_20d_high = current_close >= recent_high_20d * 0.99
        near_20d_low = current_close <= recent_low_20d * 1.01
    except Exception:
        near_20d_high = near_20d_low = False

    return {
        "rsi": _safe_float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else None,
        "macd_signal": macd_signal,
        "volume_ratio": _safe_float(round(volume_ratio, 2)),
        "bollinger_position": bb_position,
        "ma_20": _safe_float(ma_20),
        "ma_50": _safe_float(ma_50),
        "ma_200": _safe_float(ma_200),
        "trend": trend,
        "atr_pct": _safe_float(round(atr_pct, 2)) if atr_pct is not None else None,
        "position_52w": _safe_float(round(position_52w, 2)) if position_52w is not None else None,
        "high_52w": _safe_float(high_52w),
        "low_52w": _safe_float(low_52w),
        "near_20d_high": near_20d_high,
        "near_20d_low": near_20d_low,
    }


def check_technical_breakout(signals: Dict) -> Tuple[bool, str]:
    if not signals:
        return False, "No technical data"

    rsi = signals.get("rsi") or 50
    macd_signal = signals.get("macd_signal", "neutral")
    volume_ratio = signals.get("volume_ratio") or 0
    bb_position = signals.get("bollinger_position", "middle")
    trend = signals.get("trend", "sideways")
    near_high = signals.get("near_20d_high", False)
    near_low = signals.get("near_20d_low", False)

    # Bullish score
    bull_score = 0
    if rsi >= 55: bull_score += 1
    if rsi >= 65: bull_score += 1
    if macd_signal == "bullish": bull_score += 1
    if volume_ratio >= 1.5: bull_score += 1
    if volume_ratio >= 2.0: bull_score += 1
    if bb_position == "upper": bull_score += 1
    if trend == "uptrend": bull_score += 1
    if near_high: bull_score += 2

    # Bearish score
    bear_score = 0
    if rsi <= 45: bear_score += 1
    if rsi <= 35: bear_score += 1
    if macd_signal == "bearish": bear_score += 1
    if volume_ratio >= 1.5: bear_score += 1
    if volume_ratio >= 2.0: bear_score += 1
    if bb_position == "lower": bear_score += 1
    if trend == "downtrend": bear_score += 1
    if near_low: bear_score += 2

    if bull_score >= 4:
        return True, f"Bullish breakout (score {bull_score}/8): RSI {rsi:.1f}, {macd_signal} MACD, {volume_ratio:.1f}x volume, {trend}"
    if bear_score >= 4:
        return True, f"Bearish breakdown (score {bear_score}/8): RSI {rsi:.1f}, {macd_signal} MACD, {volume_ratio:.1f}x volume, {trend}"
    return False, f"No breakout (bull {bull_score}/8, bear {bear_score}/8)"
