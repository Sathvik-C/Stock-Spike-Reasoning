from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from app.database import Base


class Stock(Base):
    """Stock model - NIFTY100 stocks."""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True)
    name = Column(String(100))
    sector = Column(String(50))
    subsector = Column(String(50))

    # Relationships
    analyses = relationship("Analysis", back_populates="stock", cascade="all, delete-orphan")
    news_articles = relationship("NewsArticle", back_populates="stock", cascade="all, delete-orphan")
    fii_dii = relationship("FIIDIIActivity", back_populates="stock", cascade="all, delete-orphan")
