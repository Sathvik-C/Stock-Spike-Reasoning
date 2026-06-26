"""
Service for fetching stock news via NewsData.io API.

Free tier: title + description (no full content).
We combine title + description as input for distilbart summarization.

Works from any IP including cloud deployments.
"""

import re
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

NEWSDATA_API_URL = "https://newsdata.io/api/1/news"


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split()).strip()
    return text


def fetch_news_newsdata(
    ticker: str,
    stock_name: str,
    api_key: str,
    max_articles: int = 5,
) -> List[Dict]:
    """
    Fetch recent news for a stock via NewsData.io.

    Returns list of article dicts with:
        title, description, link, source, published_ts, full_text, scraped=False
    """
    if not api_key:
        return []

    symbol = ticker.replace(".NS", "").replace(".BO", "")
    name = stock_name or symbol
    # Use stock name without quotes for broader matching
    # but filter irrelevant results after fetching
    query = f"{name} stock India"

    try:
        resp = requests.get(
            NEWSDATA_API_URL,
            params={
                "apikey": api_key,
                "q": query,
                "country": "in",
                "language": "en",
                "category": "business,top",
                "size": max_articles * 2,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[newsdata_service] API error: {e}")
        return []

    results = data.get("results", [])
    articles = []
    seen_titles = set()

    for item in results:
        title = _clean_text(item.get("title") or "")
        description = _clean_text(item.get("description") or "")
        link = item.get("link") or ""
        source = item.get("source_name") or "Unknown"
        pub_date = item.get("pubDate") or ""

        if not title or title.lower() in seen_titles:
            continue

        # Skip articles that don't mention the stock name or symbol
        combined_lower = f"{title} {description}".lower()
        name_lower = name.lower()
        symbol_lower = symbol.lower()
        if name_lower not in combined_lower and symbol_lower not in combined_lower:
            continue

        seen_titles.add(title.lower())

        # Combine title + description as the text for summarization
        full_text = f"{title}. {description}".strip() if description else title
        # Only include if we have meaningful content
        if len(full_text) < 20:
            continue

        # Parse published date
        published_ts = ""
        try:
            dt = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            published_ts = dt.isoformat()
        except Exception:
            pass

        articles.append({
            "title": title,
            "description": description,
            "link": link,
            "source": source,
            "published_ts": published_ts,
            "paragraphs": [full_text],
            "full_text": full_text,
            "scraped": False,
            "content_source": "newsdata_api",
        })

        if len(articles) >= max_articles:
            break

    return articles