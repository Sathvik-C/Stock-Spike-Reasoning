from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Stock Spike Analyzer"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./stock_spike.db"

    # News API — set NEWSDATA_API_KEY in your environment or .env file
    newsdata_api_key: str = ""

    # Services
    finbert_model: str = "ProsusAI/finbert"
    summarization_model: str = "sshleifer/distilbart-cnn-12-6"
    cache_ttl: int = 43200  # 12 hours
    hf_endpoint: Optional[str] = None

    # NIFTY100 Configuration
    nifty100_lookback_days: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()