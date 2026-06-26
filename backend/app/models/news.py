from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class NewsArticle(Base):
    """News articles model - cached with sentiment."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    
    title = Column(String(500))
    description = Column(Text)
    source = Column(String(100))
    url = Column(String(1000), unique=True, index=True)
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Sentiment from FinBERT
    sentiment_label = Column(String(20))  # positive, neutral, negative
    sentiment_score = Column(Numeric(3, 2))  # -1 to 1
    
    # Keywords/classification
    contains_earnings = Column(Boolean, default=False)
    contains_analyst_upgrade = Column(Boolean, default=False)
    category = Column(String(50))  # earnings, analyst_call, sector_news, regulatory, etc.
    
    # Relationship
    stock = relationship("Stock", back_populates="news_articles")
