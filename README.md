# Romantasy Recommender

A collaborative filtering-based recommendation system for Romantasy books. Import your Goodreads library, find readers with similar tastes, and discover your next favorite read.

## Project Structure

```
book-recs/
├── frontend/          # Next.js 14 + TypeScript + Tailwind
│   └── src/
│       ├── app/       # App router pages
│       ├── components/
│       ├── hooks/
│       ├── lib/       # API client
│       └── types/
├── backend/           # FastAPI + SQLAlchemy
│   └── app/
│       ├── api/       # Route handlers
│       ├── core/      # Config, database
│       ├── models/    # SQLAlchemy models
│       ├── schemas/   # Pydantic schemas
│       └── services/  # Business logic
└── plan.md           # Implementation roadmap
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your database credentials

# Create database
createdb romantasy

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### Access the app

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs (when DEBUG=true)

## Development

### Generate a new migration

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Run tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python 3.11, FastAPI, Pydantic |
| Database | PostgreSQL 15, SQLAlchemy 2.0 |
| Migrations | Alembic |
| Auth | JWT (PyJWT) |

## License

MIT
