import sys
sys.path.append('.')
from app.services.news_service import fetch_news
print(fetch_news('RELIANCE.NS'))
