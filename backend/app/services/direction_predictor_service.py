"""XGBoost-based next-day direction predictor for NIFTY 100 stocks.

Features per stock per day:
    RSI, MACD signal line, Bollinger %B, volume z-score,
    5-day return, sector return, sentiment score (FinBERT on latest headline).

Label: 1 if next-day close > today's close, 0 otherwise.

Models are trained lazily on first request per ticker and cached in memory.
"""

import time
from typing import Dict, Optional

import numpy as np
import pandas as pd

try:
    from xgboost import XGBClassifier
    _HAS_XGBOOST = True
except ImportError:
    XGBClassifier = None
    _HAS_XGBOOST = False

try:
    import yfinance as yf
    _HAS_YF = True
except ImportError:
    yf = None
    _HAS_YF = False


# ── In-memory model cache ────────────────────────────────────────────────
# { ticker: { "model": XGBClassifier, "scaler_means": ..., "trained_on_days": int, "expires_at": float } }
_model_cache: Dict[str, Dict] = {}
_MODEL_TTL = 24 * 60 * 60  # retrain after 24 hours


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI indicator."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _compute_macd_signal(close: pd.Series) -> pd.Series:
    """Compute MACD signal line."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return signal_line


def _compute_bollinger_pct_b(close: pd.Series, period: int = 20) -> pd.Series:
    """Compute Bollinger %B — where price sits within bands (0=lower, 1=upper)."""
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    pct_b = (close - lower) / (upper - lower).replace(0, np.nan)
    return pct_b


def _compute_volume_zscore(volume: pd.Series, period: int = 20) -> pd.Series:
    """Compute volume z-score relative to rolling mean."""
    mean = volume.rolling(period).mean()
    std = volume.rolling(period).std().replace(0, np.nan)
    return (volume - mean) / std


def _get_sentiment_score(ticker: str) -> float:
    """Get FinBERT sentiment score for latest headline. Returns 0.0 on failure."""
    try:
        from app.services.news_service import fetch_news
        from app.services.sentiment_service import get_sentiment_analyzer

        news = fetch_news(ticker, max_headlines=1, lookback_days=3, include_full_text=False)
        if not news:
            return 0.0
        analyzer = get_sentiment_analyzer()
        result = analyzer.analyse_sentiment(news[0].get("title", ""))
        return float(result.get("sentiment_score", 0.0))
    except Exception:
        return 0.0


def _get_sector_return(ticker: str, lookback_days: int = 5) -> float:
    """Get sector index return for the ticker. Returns 0.0 on failure."""
    try:
        from app.services.sector_service import get_sector_for_ticker
        sector_ticker = get_sector_for_ticker(ticker)
        if not sector_ticker:
            return 0.0

        import contextlib
        import io
        t = yf.Ticker(sector_ticker)
        with contextlib.redirect_stderr(io.StringIO()):
            hist = t.history(period=f"{lookback_days + 5}d", interval="1d")
        if hist is None or hist.empty or len(hist) < 2:
            return 0.0
        close = hist["Close"]
        start = float(close.iloc[-min(lookback_days + 1, len(close))])
        end = float(close.iloc[-1])
        return ((end - start) / start) * 100 if start != 0 else 0.0
    except Exception:
        return 0.0


def _build_features(ticker: str, years: int = 2) -> Optional[pd.DataFrame]:
    """Build feature matrix for training/prediction.

    Returns DataFrame with columns: RSI, MACD_signal, Bollinger_pctB,
    Volume_zscore, Return_5d, and a 'label' column (1 if next-day up, 0 otherwise).
    """
    if not _HAS_YF:
        return None

    try:
        import contextlib
        import io

        period = f"{years * 365 + 30}d"
        t = yf.Ticker(ticker)
        with contextlib.redirect_stderr(io.StringIO()):
            df = t.history(period=period, interval="1d")

        if df is None or df.empty or len(df) < 60:
            return None

        close = df["Close"]
        volume = df["Volume"]

        features = pd.DataFrame(index=df.index)
        features["RSI"] = _compute_rsi(close)
        features["MACD_signal"] = _compute_macd_signal(close)
        features["Bollinger_pctB"] = _compute_bollinger_pct_b(close)
        features["Volume_zscore"] = _compute_volume_zscore(volume)
        features["Return_5d"] = close.pct_change(5) * 100

        # Label: 1 if next day close > today's close
        features["label"] = (close.shift(-1) > close).astype(int)

        # Drop rows with NaN (from rolling calculations and the last row)
        features = features.dropna()

        return features

    except Exception as e:
        print(f"[direction_predictor] Error building features for {ticker}: {e}")
        return None


def predict_direction(ticker: str) -> Dict:
    """Predict next-day direction for a stock using XGBoost.

    Trains lazily on first call per ticker, caches the model in memory.

    Args:
        ticker: Stock ticker symbol (e.g. 'INFY.NS')

    Returns:
        {
            "direction": "bullish" | "bearish",
            "confidence": float (0-1),
            "features_used": [...],
            "trained_on_days": int,
        }
    """
    if not _HAS_XGBOOST or not _HAS_YF:
        return {
            "direction": "neutral",
            "confidence": 0.5,
            "features_used": [],
            "trained_on_days": 0,
            "error": "xgboost or yfinance not available",
        }

    # Check cache
    cached = _model_cache.get(ticker)
    if cached and time.time() < cached["expires_at"]:
        model = cached["model"]
        latest_features = cached.get("latest_features")
    else:
        # Build features and train
        feature_df = _build_features(ticker, years=2)
        if feature_df is None or len(feature_df) < 30:
            return {
                "direction": "neutral",
                "confidence": 0.5,
                "features_used": [],
                "trained_on_days": 0,
                "error": "Insufficient data for training",
            }

        feature_cols = ["RSI", "MACD_signal", "Bollinger_pctB", "Volume_zscore", "Return_5d"]
        X = feature_df[feature_cols].values
        y = feature_df["label"].values

        # Train/test — use all data for training since we're predicting the future
        model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X, y)

        latest_features = X[-1:]
        trained_days = len(feature_df)

        # Cache
        _model_cache[ticker] = {
            "model": model,
            "latest_features": latest_features,
            "trained_on_days": trained_days,
            "expires_at": time.time() + _MODEL_TTL,
        }

    # Predict
    try:
        # Get latest sentiment and sector return for enhanced prediction context
        sentiment = _get_sentiment_score(ticker)
        sector_ret = _get_sector_return(ticker)

        proba = model.predict_proba(latest_features)[0]
        # proba[0] = P(bearish), proba[1] = P(bullish)
        bullish_prob = float(proba[1]) if len(proba) > 1 else 0.5

        # Adjust slightly based on sentiment and sector
        sentiment_adj = sentiment * 0.05  # small nudge from sentiment
        bullish_prob = max(0.01, min(0.99, bullish_prob + sentiment_adj))

        direction = "bullish" if bullish_prob >= 0.5 else "bearish"
        confidence = bullish_prob if direction == "bullish" else 1 - bullish_prob

        trained_days = _model_cache.get(ticker, {}).get("trained_on_days", 0)

        return {
            "direction": direction,
            "confidence": round(confidence, 2),
            "features_used": ["RSI", "MACD", "Bollinger_%B", "Volume_zscore", "Return_5d", "sentiment"],
            "trained_on_days": trained_days,
        }

    except Exception as e:
        print(f"[direction_predictor] Prediction error for {ticker}: {e}")
        return {
            "direction": "neutral",
            "confidence": 0.5,
            "features_used": [],
            "trained_on_days": 0,
            "error": str(e),
        }
