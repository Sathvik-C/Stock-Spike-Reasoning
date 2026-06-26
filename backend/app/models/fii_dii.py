from sqlalchemy import Column, Integer, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class FIIDIIActivity(Base):
    """FII/DII activity model - optional for stretch goal."""
    __tablename__ = "fii_dii_activity"

    id = Column(Integer, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("stocks.id"), index=True)
    
    activity_date = Column(Date, index=True)
    fii_inflow = Column(Numeric(12, 2))
    dii_inflow = Column(Numeric(12, 2))
    
    fetched_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    stock = relationship("Stock", back_populates="fii_dii")
