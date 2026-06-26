# Spike Terminal

NIFTY 100 stock spike analysis terminal. Detects abnormal price movements and explains the most likely cause using a layered signal engine.

## Stack
- **Frontend:** React 18 + Vite + Tailwind CSS + React Query + Framer Motion
- **Backend:** FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **ML:** FinBERT (sentiment) + DistilBART (summarization)
- **Scraping:** Playwright (headless Chromium)

## Running locally

### Backend
```bash
cd Stock-Spike-Reasoning-main
python -m venv .venv
.\.venv\Scripts\activate       # Windows
# source .venv/bin/activate    # Mac/Linux
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Or use root scripts
```bash
npm run backend    # starts FastAPI on :8000
npm run frontend   # starts Vite on :5173
```

## Project structure
```
backend/
  app/
    api/          # FastAPI routers
    models/       # SQLAlchemy models
    services/     # Business logic (sentiment, summarization, news, etc.)
    utils/        # NIFTY100 ticker list
    config.py     # Settings
    database.py   # DB setup
    main.py       # App entry point
frontend/
  src/
    api/          # Axios client
    components/   # Reusable components
    pages/        # Home, StockDetail, etc.
```
