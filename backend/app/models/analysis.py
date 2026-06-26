from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Analysis(Base):
    """Analysis results model - cached analyst briefs."""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    analysis_date = Column(Date, index=True)
    
    # Movement data
    price_change_pct = Column(Numeric(5, 2))
    lookback_days = Column(Integer)
    
    # Primary reason
    reason_category = Column(String(50))  # earnings_beat, sector_rotation, technical_breakout, etc.
    reason_confidence = Column(Integer)  # 1-100
    reason_detail = Column(JSON)  # {earnings_pct, sector_move, ta_signals, etc}
    
    # Sector context
    sector_ticker = Column(String(10))
    sector_change_pct = Column(Numeric(5, 2))
    
    # Technical signals snapshot
    rsi = Column(Numeric(5, 2))
    macd_signal = Column(String(20))  # bullish, bearish, neutral
    volume_ratio = Column(Numeric(5, 2))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    stock = relationship("Stock", back_populates="analyses")
