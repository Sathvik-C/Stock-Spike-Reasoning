"""FastAPI application entry point."""
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import router_stocks
from app.models import Stock, Analysis, NewsArticle, FIIDIIActivity
from app.utils.nifty100 import NIFTY100
from app.services.spike_service import precompute_top_movers

# Create all database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm caches on startup so the first visitor gets instant results."""
    # Fire-and-forget background thread so it doesn't block the server boot
    t = threading.Thread(target=precompute_top_movers, args=(NIFTY100,), daemon=True)
    t.start()
    yield


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS middleware — allow all origins (public stock data API)
import os as _os
_raw_origins = _os.environ.get("ALLOWED_ORIGINS", "*")
if _raw_origins.strip() == "*":
    _allowed_origins = ["*"]
else:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


@app.get("/ping")
def ping():
    """Ultra-lightweight keep-alive endpoint for cron pings."""
    return {"pong": True}


# Include routers
app.include_router(router_stocks.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
