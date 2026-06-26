# Stock Spike Analyzer - Full Stack (FastAPI + React)

## Project Structure

```
stock-spike-analyzer-fullstack/
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── services/         # Business logic
│   │   ├── main.py           # FastAPI app entry
│   │   ├── config.py         # Settings
│   │   └── database.py       # Database setup
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/                  # React application
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── api/              # API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml        # Orchestration
└── README.md
```

## Getting Started

### Local Development (Docker Compose)

```bash
# Start all services
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# Database: localhost:5432
# API Docs: http://localhost:8000/docs
```

### Manual Setup

**Backend**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Update .env with PostgreSQL credentials
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

- `GET /health` — Health check
- `GET /api/stocks/` — List all stocks
- `GET /api/stocks/top-movers` — Top gainers/losers
- `GET /api/stocks/{ticker}/analysis` — Complete analyst brief
- `GET /api/stocks/{ticker}/chart-data` — Price history
- `GET /api/stocks/{ticker}/earnings` — Earnings data
- `GET /api/stocks/{ticker}/news` — News articles
- `GET /api/stocks/{ticker}/sector` — Sector comparison
- `GET /api/stocks/{ticker}/technical` — Technical indicators

## Phase 1: Lift & Shift (Next)

Move existing Python modules into FastAPI services and create basic API endpoints.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 18, Vite, Axios, Plotly
- **Infra**: Docker, Docker Compose

## Development Notes

- All timestamps are UTC
- Database uses alembic for migrations
- React components are styled with inline CSS (can migrate to CSS modules later)
- API documentation available at `/docs` (Swagger)
