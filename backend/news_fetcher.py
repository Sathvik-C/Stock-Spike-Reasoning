import feedparser

def fetch_news_rss(query: str, max_headlines: int = 5):
    """Fetch latest Google News headlines using RSS."""
    try:
        feed_url = f"https://news.google.com/rss/search?q={query}+stock"
        feed = feedparser.parse(feed_url)
        headlines = []
        for entry in feed.entries[:max_headlines]:
            headlines.append({"title": entry.title, "link": entry.link})
        return headlines
    except Exception:
        return []
