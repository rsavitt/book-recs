# Deployment Guide

This guide covers deploying the Romantasy Recommender to production.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vercel    │────▶│  Backend    │────▶│  PostgreSQL │
│  (Frontend) │     │  (API)      │     │  (Database) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │  (Cache)    │
                    └─────────────┘
```

## Prerequisites

- Docker and Docker Compose (for local development)
- PostgreSQL 15+ database
- Redis 7+ (optional, for caching)
- Domain name with DNS access
- Accounts on deployment platforms

## Quick Start (Docker Compose)

```bash
# Clone the repository
git clone https://github.com/yourusername/book-recs.git
cd book-recs

# Copy environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# Edit environment files with your values
# Then start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Seed the database
docker-compose exec backend python -m app.scripts.seed_database
```

## Production Deployment

### Option 1: Railway (Recommended for Simplicity)

1. **Create Railway Project**
   - Go to [railway.app](https://railway.app)
   - Create new project from GitHub repo

2. **Add Services**
   - Add PostgreSQL service
   - Add Redis service (optional)

3. **Configure Backend**
   ```bash
   # In Railway dashboard, add environment variables:
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   SECRET_KEY=<generate with: openssl rand -hex 32>
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-frontend-domain.vercel.app
   ```

4. **Deploy Frontend to Vercel**
   ```bash
   cd frontend
   vercel --prod
   ```

### Option 2: Fly.io

1. **Install Fly CLI**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Create App**
   ```bash
   cd backend
   fly launch --no-deploy
   ```

3. **Create PostgreSQL Database**
   ```bash
   fly postgres create --name romantasy-db
   fly postgres attach romantasy-db
   ```

4. **Set Secrets**
   ```bash
   fly secrets set SECRET_KEY=$(openssl rand -hex 32)
   fly secrets set ENVIRONMENT=production
   fly secrets set CORS_ORIGINS=https://your-frontend-domain.vercel.app
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

6. **Run Migrations**
   ```bash
   fly ssh console -C "cd /app && alembic upgrade head"
   ```

### Option 3: Render

1. **Create Web Service**
   - Connect GitHub repository
   - Set root directory to `backend`
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. **Add PostgreSQL**
   - Create new PostgreSQL database
   - Copy Internal Database URL

3. **Environment Variables**
   ```
   DATABASE_URL=<internal database url>
   SECRET_KEY=<generate with: openssl rand -hex 32>
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-frontend-domain.vercel.app
   ```

### Frontend Deployment (Vercel)

1. **Import Project**
   - Go to [vercel.com](https://vercel.com)
   - Import from GitHub
   - Set root directory to `frontend`

2. **Environment Variables**
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api/v1
   ```

3. **Deploy**
   - Vercel will auto-deploy on push to main

## Database Setup

### Initial Migration

```bash
# Generate migration if models changed
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Seed Data

```bash
# Seed Romantasy books and tags
python -m app.scripts.seed_database
```

## Monitoring & Observability

### Sentry (Error Tracking)

1. Create project at [sentry.io](https://sentry.io)
2. Add DSN to environment:
   ```
   SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```

### Health Checks

- Liveness: `GET /health`
- Readiness: `GET /health/ready`

### Logging

Logs are output in JSON format in production:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Request completed",
  "request_id": "abc123",
  "method": "GET",
  "path": "/api/v1/recommendations",
  "status_code": 200,
  "duration_ms": 45.2
}
```

## CI/CD

GitHub Actions workflows are configured for:

1. **CI** (`.github/workflows/ci.yml`)
   - Runs on every push/PR
   - Backend tests (pytest)
   - Frontend tests (Jest)
   - E2E tests (Playwright)
   - Build verification

2. **Deploy** (`.github/workflows/deploy.yml`)
   - Runs on push to main
   - Deploys backend to Railway/Render/Fly.io
   - Deploys frontend to Vercel
   - Runs database migrations

### Required Secrets

Set these in GitHub repository settings:

```
# For Railway
RAILWAY_TOKEN

# For Render
RENDER_DEPLOY_HOOK_URL

# For Fly.io
FLY_API_TOKEN

# For Vercel
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID

# For migrations
DATABASE_URL

# Optional
SLACK_WEBHOOK_URL
```

## Scaling

### Database Indexing

Key indexes are created via migrations:
- `idx_ratings_user_id` - Fast user rating lookups
- `idx_ratings_book_id` - Fast book rating lookups
- `idx_books_isbn13` - ISBN deduplication
- `idx_user_similarities_user_id` - Neighbor lookups

### Caching Strategy

With Redis enabled:
- User similarity scores (1 hour TTL)
- Book metadata (24 hour TTL)
- Recommendation results (15 minute TTL)

### Background Jobs

Similarity computation runs as a scheduled job:
```bash
# Manual run
python -m app.scripts.compute_similarities

# Cron (daily at 3 AM)
0 3 * * * cd /app && python -m app.scripts.compute_similarities
```

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check migrations status
alembic current
alembic history
```

### API Not Responding

```bash
# Check health
curl https://your-api.com/health

# Check readiness (includes DB)
curl https://your-api.com/health/ready
```

### Frontend Can't Connect to API

1. Verify CORS_ORIGINS includes frontend domain
2. Check NEXT_PUBLIC_API_URL is correct
3. Ensure API is accessible (not blocked by firewall)

## Security Checklist

- [ ] SECRET_KEY is unique and secure (32+ bytes)
- [ ] DATABASE_URL uses SSL in production
- [ ] CORS_ORIGINS is restrictive (not `*`)
- [ ] HTTPS is enforced
- [ ] Rate limiting is enabled
- [ ] Sentry is configured for error tracking
- [ ] No sensitive data in logs
