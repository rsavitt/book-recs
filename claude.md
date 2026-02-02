# Romantasy Book Recommender

A collaborative filtering-based recommendation system for Romantasy books. Users import their Goodreads libraries to find similar readers and discover personalized book recommendations.

## Project Structure

```
book-recs/
├── frontend/          # Next.js 16 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── app/       # App router pages
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/api.ts # Centralized API client
│   │   └── types/
│   ├── e2e/           # Playwright tests
│   └── __tests__/     # Jest tests
│
├── backend/           # FastAPI + Python 3.11
│   ├── app/
│   │   ├── main.py    # App entry point
│   │   ├── api/       # Route handlers
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   ├── alembic/       # Database migrations
│   ├── scripts/       # Utility scripts
│   └── tests/         # pytest tests
│
└── docker-compose.yml # Local dev (PostgreSQL, Redis, backend, frontend)
```

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy 2.0, Pydantic 2.x
- **Database**: PostgreSQL 15+, Redis (optional caching)
- **Auth**: JWT with PyJWT + bcrypt
- **Testing**: Jest, Playwright (frontend), pytest (backend)

## Running the Project

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
alembic upgrade head
uvicorn app.main:app --reload  # http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

### Docker (All-in-One)
```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Common Commands

### Backend
```bash
pytest                              # Run tests
alembic revision --autogenerate -m "msg"  # New migration
alembic upgrade head                # Apply migrations
python -m scripts.seed_books        # Seed database
```

### Frontend
```bash
npm run dev          # Dev server
npm run build        # Production build
npm test             # Jest tests
npm run test:e2e     # Playwright tests
```

## API Endpoints (prefix: `/api/v1`)

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /books/`, `GET /books/{id}`, `GET /books/romantasy`
- `GET /users/profile`, `GET /users/neighbors`
- `POST /imports/goodreads`
- `GET /recommendations/`, `GET /recommendations/popular`
- `GET /health`, `GET /health/ready`

## Key Configuration

### Backend (`backend/app/core/config.py`)
- `DATABASE_URL`: PostgreSQL connection
- `SECRET_KEY`: JWT signing (32+ bytes in prod)
- `CORS_ORIGINS`: Allowed frontend origins
- `MIN_OVERLAP_FOR_SIMILARITY`: Default 5 books
- `MAX_NEIGHBORS_PER_USER`: Default 200

### Frontend
- `NEXT_PUBLIC_API_URL`: Backend API URL
- Image domains configured in `next.config.ts`

## Code Quality

- **Backend**: Black (formatting), Ruff (linting), pytest
- **Frontend**: ESLint, Jest, Playwright

## Core Algorithm

User-user collaborative filtering with Pearson correlation + cosine similarity. Similarity scores are adjusted with significance weighting based on rating overlap count.
