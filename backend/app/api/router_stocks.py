from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import math
import time
from typing import Dict, Any
from app.database import get_db
from app.models import Stock
from app.services.spike_service import get_top_movers as get_top_movers_service, get_recent_data
from app.services.news_service import fetch_news
from app.services.sentiment_service import get_sentiment_analyzer
from app.services.summarization_service import get_summarization_service
from app.services.earnings_service import check_earnings_release
from app.services.sector_service import compare_stock_to_sector
from app.services.technical_service import calculate_technical_signals, check_technical_breakout
from app.services.bse_filings_service import get_latest_earnings_filing
from app.services.sector_clustering_service import get_full_cluster_mapping
from app.services.direction_predictor_service import predict_direction
from app.services.reason_engine import ReasonEngine
from app.utils.nifty100 import NIFTY100, NIFTY100_NAMES

_reason_engine = ReasonEngine()

# ── In-memory cache for news summaries ───────────────────────────────────────
# Structure: { ticker: { "data": {...}, "expires_at": float } }
_news_summary_cache: Dict[str, Any] = {}
NEWS_SUMMARY_TTL = 12 * 60 * 60  # 12 hours in seconds

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _safe_pct(value, default: float = 0.0) -> float:
    """Convert value to a finite float percentage, else return default."""
    try:
        pct = float(value)
        return pct if math.isfinite(pct) else default
    except (TypeError, ValueError):
        return default


@router.get("/")
def list_stocks(db: Session = Depends(get_db)):
    """List all NIFTY100 stocks."""
    stocks = db.query(Stock).all()
    if stocks:
        return stocks

    # Fallback before DB seed is implemented
    return [
        {
            "ticker": ticker,
            "name": NIFTY100_NAMES.get(ticker, ticker.replace(".NS", "")),
        }
        for ticker in NIFTY100
    ]


@router.get("/top-movers")
def get_top_movers(
    lookback_days: int = Query(1, ge=1, le=30),
    top_n: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db)
):
    """Get top gainers and losers for lookback period."""
    data = get_top_movers_service(NIFTY100, days=lookback_days, top_n=top_n)
    gainers = [
        {
            "ticker": ticker,
            "name": NIFTY100_NAMES.get(ticker, ticker.replace(".NS", "")),
            "change": change,
        }
        for ticker, change in data.get("gainers", {}).items()
    ]
    losers = [
        {
            "ticker": ticker,
            "name": NIFTY100_NAMES.get(ticker, ticker.replace(".NS", "")),
            "change": change,
        }
        for ticker, change in data.get("losers", {}).items()
    ]

    return {
        "lookback_days": lookback_days,
        "top_n": top_n,
        "gainers": gainers,
        "losers": losers,
        "error": data.get("error"),
    }


@router.get("/clusters")
def get_clusters(db: Session = Depends(get_db)):
    """Get the K-Means cluster mapping for all NIFTY 100 stocks."""
    mapping = get_full_cluster_mapping()
    return {"clusters": mapping}


def _confidence_label(score: int) -> str:
    if score >= 80:
        return "High"
    elif score >= 60:
        return "Medium"
    else:
        return "Low"

@router.get("/{ticker}/analysis")
def get_stock_analysis(
    ticker: str,
    lookback_days: int = Query(1, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """Get complete analyst research brief for a stock."""
    period = f"{lookback_days}d"
    price_df = get_recent_data(ticker, period=period, interval="1d")
    if price_df is None or price_df.empty:
        return {"ticker": ticker, "error": "No price data found.", "price_change": 0.0}
    try:
        change_pct_raw = get_top_movers_service([ticker], days=lookback_days).get("movement", {}).get(ticker)
        change_pct = _safe_pct(change_pct_raw)
    except:
        open_first = float(price_df["Open"].iloc[0])
        close_last = float(price_df["Close"].iloc[-1])
        change_pct = ((close_last - open_first) / open_first) * 100 if open_first else 0.0

    technical = calculate_technical_signals(price_df)
    technical_fired, technical_summary = check_technical_breakout(technical)

    news_items = fetch_news(
        ticker,
        max_headlines=10,
        lookback_days=max(lookback_days, 3),
        include_full_text=True,
        max_scrapes=5,
    )
    analyzer = get_sentiment_analyzer()
    for article in news_items:
        sentiment = analyzer.analyse_sentiment(article.get("title", ""))
        article["sentiment_label"] = sentiment["label"]
        article["sentiment_score"] = sentiment["sentiment_score"]

    major_news = {"fired": False}
    if news_items:
        scored = sorted(news_items, key=lambda x: abs(float(x.get("sentiment_score", 0.0))), reverse=True)
        best = scored[0]
        major_news = {
            "fired": True,
            "headline": best.get("title", ""),
            "source": best.get("source", "Unknown"),
            "category": best.get("category", "general"),
            "sentiment_score": best.get("sentiment_score", 0.0),
        }

    earnings_fired, earnings_data = check_earnings_release(ticker, lookback_days=lookback_days)
    earnings_signal = {"fired": earnings_fired}
    if earnings_data:
        earnings_signal.update(earnings_data)
        
    if not earnings_fired:
        bse_filing = get_latest_earnings_filing(ticker, lookback_days=lookback_days)
        if bse_filing:
            earnings_signal["bse_headline"] = bse_filing.get("headline", "")

    sector = compare_stock_to_sector(ticker, change_pct, lookback_days=lookback_days)

    signals = {
        "earnings_release": earnings_signal,
        "major_news": major_news,
        "sector_rotation": sector,
        "technical_breakout": {
            "fired": technical_fired,
            "summary": technical_summary,
            **technical,
        },
        "generic_momentum": {"fired": True},
    }

    reason_category, confidence, reason_detail = _reason_engine.combine_signals(signals)
    summary = _reason_engine.generate_summary(ticker, change_pct, reason_category, reason_detail)

    direction_pred = predict_direction(ticker)

    return {
        "ticker": ticker,
        "lookback_days": lookback_days,
        "price_change": round(change_pct, 2),
        "reason_category": reason_category,
        "reason_confidence": _confidence_label(confidence),
        "reason_detail": summary,
        "signals": {
            "earnings": earnings_signal,
            "sector": sector,
            "technical": {"summary": technical_summary, **technical},
        },
        "top_news": news_items[:5],
        "direction_prediction": direction_pred,
    }


@router.get("/{ticker}/chart-data")
def get_chart_data(
    ticker: str,
    lookback_days: int = Query(1, ge=1, le=4000),
    db: Session = Depends(get_db)
):
    """Get price history for charting."""
    period = f"{lookback_days}d"
    interval = "5m" if lookback_days == 1 else "1d"
    df = get_recent_data(ticker, period=period, interval=interval)
    if df is None or df.empty:
        return {"ticker": ticker, "data": [], "error": "No chart data found."}

    data = []
    for idx, row in df.iterrows():
        data.append(
            {
                "date": idx.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            }
        )
    change_pct_raw = get_top_movers_service([ticker], days=lookback_days).get("movement", {}).get(ticker)
    change_pct = _safe_pct(change_pct_raw)

    return {
        "ticker": ticker,
        "data": data,
        "pct_change": change_pct
    }


@router.get("/{ticker}/earnings")
def get_earnings_data(ticker: str, db: Session = Depends(get_db)):
    """Get quarterly earnings data."""
    fired, earnings = check_earnings_release(ticker, lookback_days=1)
    bse_filing = get_latest_earnings_filing(ticker, lookback_days=30)
    
    return {
        "ticker": ticker,
        "recent_release": fired,
        "earnings": earnings,
        "bse_filing": bse_filing
    }


@router.get("/{ticker}/news")
def get_stock_news(
    ticker: str,
    limit: int = Query(10, ge=1, le=50),
    include_full_text: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get top news articles with sentiment scores."""
    news = fetch_news(
        ticker,
        max_headlines=limit,
        lookback_days=3,
        include_full_text=include_full_text,
        max_scrapes=min(limit, 8),
    )

    # Fallback to NewsData.io API when RSS scraping returns nothing
    if not news:
        try:
            from app.services.newsdata_service import fetch_news_newsdata
            from app.config import settings
            api_key = getattr(settings, "newsdata_api_key", "")
            stock_name = NIFTY100_NAMES.get(ticker.upper(), ticker.replace(".NS", ""))
            newsdata_articles = fetch_news_newsdata(
                ticker=ticker,
                stock_name=stock_name,
                api_key=api_key,
                max_articles=limit,
            )
            # Normalize fields to match RSS article shape
            for a in newsdata_articles:
                if "link" not in a and "url" in a:
                    a["link"] = a["url"]
            news = newsdata_articles
        except Exception:
            pass

    analyzer = get_sentiment_analyzer()
    for article in news:
        sentiment = analyzer.analyse_sentiment(article.get("title", ""))
        article["sentiment_label"] = sentiment["label"]
        article["sentiment_score"] = sentiment["sentiment_score"]

    return {
        "ticker": ticker,
        "news": news,
    }


@router.get("/{ticker}/sector")
def get_sector_comparison(ticker: str, db: Session = Depends(get_db)):
    """Get sector context and comparison."""
    stock_change_raw = get_top_movers_service([ticker], days=1).get("movement", {}).get(ticker)

    stock_change = _safe_pct(stock_change_raw, default=float("nan"))
    if not math.isfinite(stock_change):
        df = get_recent_data(ticker, period="1d", interval="1d")
        stock_change = 0.0
        if df is not None and not df.empty:
            open_first = float(df["Open"].iloc[0])
            close_last = float(df["Close"].iloc[-1])
            stock_change = ((close_last - open_first) / open_first) * 100 if open_first else 0.0

    sector = compare_stock_to_sector(ticker, stock_change, lookback_days=1)
    return {
        "ticker": ticker,
        "sector": sector,
    }


@router.get("/{ticker}/technical")
def get_technical_signals(ticker: str, db: Session = Depends(get_db)):
    """Get technical indicators (RSI, MACD, Volume, Bollinger Bands)."""
    df = get_recent_data(ticker, period="3mo", interval="1d")
    signals = calculate_technical_signals(df) if df is not None else {}
    breakout, summary = check_technical_breakout(signals)

    return {
        "ticker": ticker,
        "signals": signals,
        "breakout": breakout,
        "summary": summary,
    }







@router.get("/{ticker}/news-summary")
def get_news_summary(
    ticker: str,
    db: Session = Depends(get_db)
):
    """
    Fetch news via NewsData.io API and return:
    - top_news: top 5 headlines from RSS (fast)
    - news_summary: distilbart summary of article titles + descriptions

    Works from any IP including cloud deployments.
    Results are cached in-memory for 12 hours.
    """
    from app.services.newsdata_service import fetch_news_newsdata
    from app.config import settings
    from datetime import datetime, timezone

    ticker = ticker.upper()

    # ── Check cache ───────────────────────────────────────────────────────
    cached = _news_summary_cache.get(ticker)
    if cached and time.time() < cached["expires_at"]:
        return cached["data"]

    stock_name = NIFTY100_NAMES.get(ticker, ticker.replace(".NS", ""))

    # ── Top 5 headlines from RSS (fast, unchanged) ────────────────────────
    top_news = fetch_news(
        ticker,
        max_headlines=5,
        lookback_days=3,
        include_full_text=False,
    )

    # ── Fetch articles via NewsData.io API ────────────────────────────────
    api_key = getattr(settings, "newsdata_api_key", "")
    newsdata_articles = fetch_news_newsdata(
        ticker=ticker,
        stock_name=stock_name,
        api_key=api_key,
        max_articles=5,
    )

    # Fallback for top_news if RSS failed
    if not top_news and newsdata_articles:
        top_news = newsdata_articles.copy()

    # ── Summarize combined descriptions ───────────────────────────────────
    summarizer = get_summarization_service()
    summary_result = summarizer.summarize_combined(newsdata_articles)

    # ── Build response ────────────────────────────────────────────────────
    response = {
        "ticker": ticker,
        "top_news": top_news,
        "news_summary": {
            "overall_summary": summary_result.get("overall_summary"),
            "articles": [
                {
                    "title": a.get("title"),
                    "source": a.get("source"),
                    "url": a.get("link"),
                    "description": a.get("description"),
                }
                for a in newsdata_articles
            ],
            "article_count": len(newsdata_articles),
            "content_source": "newsdata_api",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # ── Store in cache ────────────────────────────────────────────────────
    # Only cache if we actually got some valid news or summary
    has_news = bool(top_news or newsdata_articles)
    if has_news:
        _news_summary_cache[ticker] = {
            "data": response,
            "expires_at": time.time() + NEWS_SUMMARY_TTL,
        }

    return response