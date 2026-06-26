"""Service for fetching and deduplicating stock news from RSS feeds."""

import feedparser
import base64
import math
import urllib.parse
import time
import random
import re
import html
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional


TRUST_WEIGHTS = {
    "reuters": 1.0,
    "bloomberg": 0.95,
    "economic times": 0.9,
    "moneycontrol": 0.88,
    "livemint": 0.85,
    "business standard": 0.85,
    "cnbc": 0.82,
}

NOISE_KEYWORDS = {
    "subscribe", "subscription", "advertisement", "advertise", "sponsored",
    "follow us", "follow on", "share this", "share on", "tweet",
    "copyright", "all rights reserved", "cookie", "cookies",
    "privacy policy", "terms of service", "disclaimer",
    "related articles", "more stories", "read more", "read further",
    "trending now", "editor pick", "top story", "top trending",
    "listen to this article", "read full story",
    "etprime", "subscribe now", "unlock premium", "sign up",
    "live market", "live ticker",
}


def _is_noise_paragraph(text: str) -> bool:
    """Check if a paragraph is likely noise (ads, footer, nav, etc)."""
    if not text:
        return True
    lower = text.lower().strip()
    
    # Check for noise keywords
    for keyword in NOISE_KEYWORDS:
        if keyword in lower:
            return True
    
    # Skip very short paragraphs that are just clickbait or nav
    if len(lower) < 20:
        return True
    
    # Skip paragraphs that are mostly symbols or numbers
    alpha_count = sum(1 for c in lower if c.isalpha())
    if alpha_count < len(lower) * 0.3:
        return True
    
    # Skip if it's a short headline-like text (short + colon/dash, common in related articles sections)
    # Examples: "Title: Description", "Headline - Subheadline"
    words = lower.split()
    if len(words) < 8 and (':' in lower or ' - ' in lower):
        # Short line with dividers = likely a headline/link, not article body
        return True
    
    return False


def _merge_continuation_paragraphs(paragraphs: List[str]) -> List[str]:
    """Merge short paragraphs that are likely continuations of the previous one.
    
    Uses length-based merging: if a paragraph is under 120 chars it likely
    continues in the next one. Keep merging until combined length exceeds 120
    or we run out of paragraphs. This handles financial articles where a sentence
    spans multiple short <p> tags regardless of capitalisation.
    """
    if not paragraphs:
        return []

    merged = []
    i = 0
    while i < len(paragraphs):
        current = paragraphs[i].strip()
        # Keep absorbing next paragraphs while current is short
        while len(current) < 120 and i + 1 < len(paragraphs):
            next_para = paragraphs[i + 1].strip()
            if not next_para:
                break
            current = f"{current} {next_para}"
            i += 1
        merged.append(current)
        i += 1

    return merged


def _clean_paragraphs(paragraphs: List[str], min_length: int = 40, max_paragraphs: int = 16, debug: bool = False) -> List[str]:
    # First, merge continuations
    merged = _merge_continuation_paragraphs(paragraphs)
    
    cleaned: List[str] = []
    seen = set()
    for paragraph in merged:
        text = " ".join((paragraph or "").split()).strip()
        
        # Skip noise
        if _is_noise_paragraph(text):
            if debug:
                print(f"  [FILTERED as noise] {text[:80]}...")
            continue
        
        # Skip if too short
        if len(text) < min_length:
            if debug:
                print(f"  [FILTERED as too short] {text[:80]}...")
            continue
        
        # Skip duplicates
        key = text.lower()
        if key in seen:
            if debug:
                print(f"  [FILTERED as duplicate]")
            continue
        
        if debug:
            print(f"  [KEPT] {text[:80]}...")
        
        seen.add(key)
        cleaned.append(text)
        
        if len(cleaned) >= max_paragraphs:
            break
    
    return cleaned


def _html_to_text(value: str) -> str:
    """Convert simple HTML fragments to plain text."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    text = " ".join(text.split()).strip()
    return text


def _metadata_fallback_text(title: str, description_html: str) -> str:
    """Build fallback article text from feed metadata when page scraping fails."""
    title_text = " ".join((title or "").split()).strip()
    desc_text = _html_to_text(description_html)
    if desc_text.lower().startswith(title_text.lower()):
        combined = desc_text
    elif title_text and desc_text:
        combined = f"{title_text}. {desc_text}"
    else:
        combined = title_text or desc_text
    return combined.strip()


def _decode_google_rss_article_url(url: str) -> str:
    """Try to decode publisher URL embedded in Google News RSS article token."""
    if not url:
        return ""

    try:
        parsed = urllib.parse.urlparse(url)
        if "news.google.com" not in parsed.netloc:
            return ""

        parts = [part for part in parsed.path.split("/") if part]
        if "articles" not in parts:
            return ""

        idx = parts.index("articles")
        if idx + 1 >= len(parts):
            return ""

        token = parts[idx + 1]
        token = token.replace("-", "+").replace("_", "/")
        token += "=" * ((4 - len(token) % 4) % 4)

        decoded_bytes = base64.b64decode(token)
        decoded_text = decoded_bytes.decode("utf-8", errors="ignore")
        matches = re.findall(r"https?://[^\s\"'<>]+", decoded_text)
        for candidate in matches:
            candidate = urllib.parse.unquote(candidate.strip())
            netloc = urllib.parse.urlparse(candidate).netloc
            if not netloc:
                continue
            if "news.google.com" in netloc:
                continue
            return candidate
    except Exception:
        return ""

    return ""


def _published_to_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _news_category(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["result", "earnings", "quarter", "profit", "eps"]):
        return "earnings"
    if any(k in lower for k in ["upgrade", "downgrade", "target price", "buy", "sell"]):
        return "analyst_call"
    if any(k in lower for k in ["merger", "acquisition", "stake", "deal", "approval"]):
        return "corporate_action"
    if any(k in lower for k in ["sector", "index", "nifty"]):
        return "sector_news"
    return "general"


def _trust_score(source: str) -> float:
    lower = (source or "").lower()
    for key, value in TRUST_WEIGHTS.items():
        if key in lower:
            return value
    return 0.7


def _build_query_variations(
    ticker: str,
    stock_name: Optional[str] = None,
    price_change_pct: Optional[float] = None,
) -> List[str]:
    """Build Google RSS search queries using stock name and price move direction."""
    symbol = ticker.replace(".NS", "")
    company_hint = symbol.split("-")[0]
    display_name = " ".join((stock_name or company_hint or symbol).split()).strip() or company_hint or symbol

    query_variations: List[str] = []

    positive = False
    magnitude = None
    if price_change_pct is not None:
        try:
            if math.isfinite(float(price_change_pct)) and float(price_change_pct) != 0:
                positive = float(price_change_pct) > 0
                magnitude = abs(float(price_change_pct))
        except Exception:
            positive = False
            magnitude = None

    if magnitude is not None:
        move_word = "up" if positive else "down"
        change_word = "rises" if positive else "falls"
        gain_word = "gain" if positive else "loss"
        query_variations.extend(
            [
                f'"{display_name}" stock {move_word} {magnitude:.1f}%',
                f'"{display_name}" shares {change_word}',
                f'"{display_name}" {gain_word} {magnitude:.1f}%',
                f'"{company_hint}" stock {move_word} {magnitude:.1f}%',
            ]
        )

    query_variations.extend(
        [
            f'"{display_name}" stock',
            f'"{display_name}" earnings',
            f'"{display_name}"',
            f'"{company_hint}" stock',
            f'"{company_hint}" earnings',
            f'"{company_hint}"',
        ]
    )

    # Preserve order while removing duplicates.
    seen = set()
    unique_queries: List[str] = []
    for query in query_variations:
        if query in seen:
            continue
        seen.add(query)
        unique_queries.append(query)

    return unique_queries


def fetch_news(
    ticker: str,
    max_headlines: int = 10,
    lookback_days: int = 3,
    include_full_text: bool = False,
    max_scrapes: int = 5,
    allow_metadata_fallback: bool = False,
    stock_name: Optional[str] = None,
    price_change_pct: Optional[float] = None,
) -> List[Dict]:
    """Fetch and rank recent news by recency and source trust."""
    query_variations = _build_query_variations(ticker, stock_name=stock_name, price_change_pct=price_change_pct)

    # Direct source RSS feeds — give real article URLs, no Google redirect
    stock_name_query = urllib.parse.quote_plus(stock_name or ticker.replace(".NS", ""))

    DIRECT_RSS_FEEDS = [
        # NDTV Profit — scrapeable, direct URLs
        f"https://feeds.feedburner.com/ndtvprofit-latest",
        # Financial Express — direct URLs
        f"https://www.financialexpress.com/feed/",
        # Business Today — direct URLs  
        f"https://www.businesstoday.in/rss/home",
        # Reuters India business
        f"https://feeds.reuters.com/reuters/INbusinessNews",
        # Yahoo Finance ticker feed — direct URLs
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={urllib.parse.quote_plus(ticker)}&region=IN&lang=en-IN",
        # PTI News
        f"https://www.ptinews.com/rss/business.xml",
    ]

    # Google News RSS — useful for headlines but URLs need resolution
    GOOGLE_NEWS_ENDPOINTS = [
        "https://news.google.com/rss/search?q={}&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en",
    ]

    seen_keys = set()
    articles: List[Dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    target_count = max(0, int(max_headlines))
    candidate_pool_size = target_count

    def _add_entry(entry, source_override: str = ""):
        """Parse a feed entry and add to articles if relevant and not duplicate."""
        if len(articles) >= candidate_pool_size:
            return
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        description = entry.get("description", "").strip()
        source = source_override or (
            entry.get("source", {}).get("title", "") if hasattr(entry, "source") else ""
        )
        published_raw = entry.get("published", "")
        published_dt = _published_to_datetime(published_raw)

        dedupe_key = (title.lower()[:120], source.lower())
        if not title or not link or dedupe_key in seen_keys:
            return
        if published_dt and published_dt < cutoff:
            return

        # Filter for ticker relevance in direct feeds
        ticker_symbol = ticker.replace(".NS", "").upper()
        name_hint = (stock_name or ticker_symbol).lower()
        combined = f"{title} {description}".lower()
        
        # Build multiple search terms to match variations
        search_terms = [
            ticker_symbol.lower(),           # e.g. "hdfcbank"
            name_hint[:8].lower(),           # first 8 chars of name
            ticker_symbol[:4].lower(),       # first 4 chars e.g. "hdfc"
            ticker_symbol.replace("BANK", " BANK").lower().strip(),  # "hdfc bank"
            ticker_symbol.replace("LTD", "").lower().strip(),
        ]
        # Also split camelcase/joined words e.g. HDFCBANK -> HDFC BANK
        split_ticker = re.sub(r'([A-Z][a-z])', r' \1', ticker_symbol).lower().strip()
        if split_ticker != ticker_symbol.lower():
            search_terms.append(split_ticker)

        if not any(term in combined for term in search_terms if len(term) >= 3):
            return  # Article not about this stock

        seen_keys.add(dedupe_key)
        article_text = f"{title} {description}".strip()
        articles.append({
            "title": title,
            "link": link,
            "source": source or "Unknown",
            "published": published_raw,
            "published_ts": published_dt.isoformat() if published_dt else "",
            "description": description,
            "category": _news_category(article_text),
            "trust_score": _trust_score(source),
            "is_direct_url": "news.google.com" not in link,
        })

    # ── Step 1: Try direct RSS feeds first (give real scrapeable URLs) ────
    for feed_url in DIRECT_RSS_FEEDS:
        if len(articles) >= candidate_pool_size:
            break
        try:
            time.sleep(0.2)
            feed = feedparser.parse(feed_url)
            source_name = urllib.parse.urlparse(feed_url).netloc.replace("www.", "").replace("feeds.", "")
            for entry in feed.entries:
                _add_entry(entry, source_override=source_name)
        except Exception:
            continue

    # ── Step 2: Google News RSS for remaining slots (headlines only) ──────
    for query in query_variations:
        if len(articles) >= candidate_pool_size:
            break
        for endpoint in GOOGLE_NEWS_ENDPOINTS:
            if len(articles) >= candidate_pool_size:
                break
            try:
                time.sleep(0.25 + random.random() * 0.5)
                url = endpoint.format(urllib.parse.quote_plus(query))
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    if len(articles) >= candidate_pool_size:
                        break
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()
                    description = entry.get("description", "").strip()
                    source = entry.get("source", {}).get("title", "") if hasattr(entry, "source") else ""
                    published_raw = entry.get("published", "")
                    published_dt = _published_to_datetime(published_raw)
                    dedupe_key = (title.lower()[:120], source.lower())
                    if not title or not link or dedupe_key in seen_keys:
                        continue
                    if published_dt and published_dt < cutoff:
                        continue
                    seen_keys.add(dedupe_key)
                    article_text = f"{title} {description}".strip()
                    articles.append({
                        "title": title,
                        "link": link,
                        "source": source or "Unknown",
                        "published": published_raw,
                        "published_ts": published_dt.isoformat() if published_dt else "",
                        "description": description,
                        "category": _news_category(article_text),
                        "trust_score": _trust_score(source),
                        "is_direct_url": False,
                    })
            except Exception:
                continue

    now = datetime.now(timezone.utc)

    def rank_score(article: Dict) -> float:
        published_ts = article.get("published_ts")
        recency_score = 0.5
        if published_ts:
            try:
                dt = datetime.fromisoformat(published_ts)
                age_hours = max((now - dt).total_seconds() / 3600.0, 0.0)
                recency_score = max(0.0, 1.0 - min(age_hours / (lookback_days * 24), 1.0))
            except Exception:
                recency_score = 0.5
        return 0.6 * recency_score + 0.4 * float(article.get("trust_score", 0.7))

    ranked = sorted(articles, key=rank_score, reverse=True)
    if not include_full_text:
        return ranked[:max_headlines]

    # ── include_full_text path: enrich with metadata fallback ─────────────
    # Scraping has been removed; use title + description as full_text.
    selected: List[Dict] = []
    seen_titles = set()

    for article in ranked:
        item = dict(article)
        title_key = (item.get("title") or "").strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        fallback_text = _metadata_fallback_text(
            str(item.get("title") or ""),
            str(item.get("description") or ""),
        )

        # Try to decode actual publisher URL from Google News links
        link = item.get("link") or ""
        decoded_url = _decode_google_rss_article_url(link) if "news.google.com" in link else link
        item["resolved_url"] = decoded_url or link
        item["full_text"] = fallback_text if fallback_text else None
        item["paragraphs"] = [fallback_text] if fallback_text else []
        item["scraped"] = False
        item["content_mode"] = "metadata_fallback" if fallback_text else "none"

        selected.append(item)
        if len(selected) >= target_count:
            break

    return selected[:target_count]