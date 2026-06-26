"""K-Means sector clustering service for NIFTY 100 stocks.

Clusters stocks by correlation of daily returns over the past year.
Uses scikit-learn KMeans with 8 clusters. Results are cached for 24 hours.
"""

import time
from typing import Dict, List, Optional

import pandas as pd

try:
    from sklearn.cluster import KMeans
    _HAS_SKLEARN = True
except ImportError:
    KMeans = None
    _HAS_SKLEARN = False

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    yf = None
    _HAS_YFINANCE = False


# ── Module-level cache ────────────────────────────────────────────────────
_cluster_cache: Dict = {
    "mapping": None,       # Dict[str, int] — ticker → cluster_id
    "expires_at": 0.0,
}
_CACHE_TTL = 24 * 60 * 60  # 24 hours


def build_cluster_model(
    tickers: Optional[List[str]] = None,
    lookback_days: int = 252,
    n_clusters: int = 8,
) -> Dict[str, Dict]:
    """Build K-Means cluster model from daily return correlations.

    Args:
        tickers: List of ticker symbols. Defaults to NIFTY 100.
        lookback_days: Number of trading days to look back (default 252 ≈ 1 year).
        n_clusters: Number of clusters for KMeans.

    Returns:
        Dict mapping ticker → {"cluster": int, "x": float, "y": float}
    """
    # Return cached result if fresh
    if _cluster_cache["mapping"] and time.time() < _cluster_cache["expires_at"]:
        return _cluster_cache["mapping"]

    if not _HAS_SKLEARN or not _HAS_YFINANCE:
        print("[sector_clustering] scikit-learn or yfinance not available")
        return {}

    if tickers is None:
        from app.utils.nifty100 import NIFTY100
        tickers = NIFTY100

    try:
        import contextlib
        import io
        from sklearn.decomposition import PCA

        period = f"{lookback_days + 30}d"  # extra buffer for weekends/holidays

        with contextlib.redirect_stderr(io.StringIO()):
            data = yf.download(
                tickers,
                period=period,
                interval="1d",
                group_by="column",
                progress=False,
            )

        if data.empty or "Close" not in data:
            print("[sector_clustering] No price data returned from yfinance")
            return {}

        close = data["Close"]

        # Drop tickers with too many NaN values (>30% missing)
        threshold = len(close) * 0.7
        close = close.dropna(axis=1, thresh=int(threshold))

        # Compute daily returns
        returns = close.pct_change().dropna()

        if returns.empty or returns.shape[1] < n_clusters:
            print(f"[sector_clustering] Not enough valid tickers ({returns.shape[1]})")
            return {}

        # Compute correlation matrix
        corr_matrix = returns.corr()

        # Fill any remaining NaN with 0 (uncorrelated assumption)
        corr_matrix = corr_matrix.fillna(0)

        # Run KMeans on correlation matrix rows
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(corr_matrix.values)
        
        # Run PCA to reduce down to 2 dimensions for visualization
        pca = PCA(n_components=2, random_state=42)
        coords = pca.fit_transform(corr_matrix.values)

        mapping = {
            str(ticker): {
                "cluster": int(label),
                "x": round(float(coord[0]), 3),
                "y": round(float(coord[1]), 3)
            }
            for ticker, label, coord in zip(corr_matrix.index, labels, coords)
        }

        # Cache the result
        _cluster_cache["mapping"] = mapping
        _cluster_cache["expires_at"] = time.time() + _CACHE_TTL

        print(f"[sector_clustering] Built {n_clusters} clusters with PCA for {len(mapping)} tickers")
        return mapping

    except Exception as e:
        print(f"[sector_clustering] Error building cluster model: {e}")
        return {}


def get_stock_cluster(ticker: str) -> List[str]:
    """Get list of tickers in the same cluster as the given ticker.

    Args:
        ticker: Stock ticker symbol (e.g. 'INFY.NS')

    Returns:
        List of peer tickers in the same cluster (excluding the ticker itself)
    """
    mapping = build_cluster_model()
    if not mapping:
        return []

    cluster_data = mapping.get(ticker)
    if cluster_data is None:
        return []

    cluster_id = cluster_data["cluster"]
    peers = [t for t, data in mapping.items() if data["cluster"] == cluster_id and t != ticker]
    return sorted(peers)


def get_full_cluster_mapping() -> Dict[str, int]:
    """Return the full ticker → cluster_id mapping.

    Useful for the /api/stocks/clusters endpoint.
    """
    return build_cluster_model()
