# backend/news_fetcher.py

import feedparser
import urllib.parse
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict

def fetch_news(query: str, max_headlines: int = 5) -> List[Dict]:
    """
    Enhanced news fetcher with better query handling and multiple fallback strategies.
    Tries multiple query variations and endpoints to find relevant news articles.
    """
    # Clean and prepare the query
    base_query = query.split(' -')[0]  # Remove exclusions for initial search
    company_name = base_query.split('"')[-2] if '"' in base_query else base_query.split()[0]
    
    # Try multiple query variations
    query_variations = [
        # Original query with company name and ticker
        query,
        # Broader search with just company name and movement
        f'"{company_name}" stock {"up" if "up" in query else "down"}',
        # Just company name with recent time filter
        f'"{company_name}" after:{(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")}',
        # Most basic - just company name
        f'"{company_name}"'
    ]
    
    # Try different RSS endpoints
    endpoints = [
        "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q={}&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q={}&hl=en&gl=US&ceid=US:en"
    ]
    
    seen_links = set()
    articles = []
    
    for query_variant in query_variations:
        if len(articles) >= max_headlines:
            break
            
        for endpoint in endpoints:
            if len(articles) >= max_headlines:
                break
                
            try:
                # Add small delay to avoid rate limiting
                time.sleep(0.5 + random.random())
                
                # Format URL
                url = endpoint.format(urllib.parse.quote_plus(query_variant))
                
                # Add cache buster
                url += f"&_={int(time.time())}"
                
                # Fetch and parse feed
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    if len(articles) >= max_headlines:
                        break
                        
                    # Skip if we've seen this link before
                    link = entry.get('link', '')
                    if not link or link in seen_links:
                        continue
                        
                    # Skip very short titles
                    title = entry.get('title', '').strip()
                    if len(title) < 10:
                        continue
                        
                    # Add source information
                    source = entry.get('source', {}).get('title', '') if hasattr(entry, 'source') else 'Google News'
                    
                    articles.append({
                        'title': title,
                        'link': link,
                        'source': source,
                        'published': entry.get('published', ''),
                        'description': entry.get('description', '')
                    })
                    seen_links.add(link)
                    
            except Exception as e:
                print(f"Error fetching from {endpoint.split('?')[0]}: {str(e)}")
                continue
                
    return articles[:max_headlines]
