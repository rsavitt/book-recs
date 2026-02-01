# Romantasy Book Recommender - Implementation Plan

A collaborative filtering-based recommendation system for Romantasy books, using Goodreads CSV exports as the primary data source.

---

## Phase 1: Project Setup & Infrastructure

### 1.1 Initialize Project Structure
- [x] Set up monorepo structure (frontend + backend)
- [x] Initialize Next.js frontend with TypeScript
- [x] Initialize FastAPI backend with Python 3.11+
- [x] Configure ESLint, Prettier, Black, Ruff for code quality
- [x] Set up environment variable management (.env files)

### 1.2 Database Setup
- [ ] Set up PostgreSQL (local dev + production config)
- [x] Design and create schema:
  - `users` - account info, preferences, privacy settings
  - `books` - normalized book catalog (title, author, ISBN, OLID)
  - `book_editions` - edition variants linking to canonical books
  - `ratings` - user_id, book_id, rating (1-5), read_date, source
  - `shelves` - user-defined shelves/tags from imports
  - `book_tags` - genre/trope tags (romantasy, fae, enemies-to-lovers, etc.)
  - `user_similarities` - precomputed similarity scores between users
- [x] Set up database migrations (Alembic)
- [ ] Create seed data for development

### 1.3 External API Integration Setup
- [x] Set up Open Library API client (book metadata, covers)
- [x] Set up Google Books API client (fallback metadata)
- [ ] Create book metadata caching layer (deferred - using in-memory for MVP)

---

## Phase 2: Core Data Pipeline

### 2.1 Goodreads CSV Parser
- [x] Parse Goodreads export CSV format
  - Book Id, Title, Author, ISBN, ISBN13, My Rating, Date Read, Bookshelves, etc.
- [x] Handle edge cases (missing ISBNs, malformed dates, encoding issues)
- [x] Extract and normalize shelf/tag data
- [x] Map ratings to internal 1-5 scale
- [x] Create import validation and error reporting

### 2.2 Book Deduplication & Normalization
- [x] Primary matching: ISBN-13 → ISBN-10 → OLID
- [x] Fallback matching: fuzzy title + author (Levenshtein distance)
- [x] Handle series entries (e.g., "A Court of Thorns and Roses #1")
- [x] Create canonical book records, link editions
- [x] Build author normalization (handle pen names, co-authors)

### 2.3 Book Metadata Enrichment
- [x] Fetch covers from Open Library / Google Books
- [x] Pull descriptions, page counts, publication dates
- [x] Store and cache metadata locally
- [x] Handle missing metadata gracefully

---

## Phase 3: Romantasy Classification

### 3.1 Seed List Curation
- [x] Create initial Romantasy seed list (200-500 books)
  - ACOTAR series, Fourth Wing, From Blood and Ash, etc.
- [x] Tag with sub-genres: fae, vampires, academy, etc.
- [x] Tag with tropes: enemies-to-lovers, forced proximity, slow burn, etc.
- [x] Add spice level ratings (0-5 scale, user-contributed over time)

### 3.2 Shelf/Tag Inference
- [x] Define Romantasy-indicating shelf patterns:
  - Direct: "romantasy", "fantasy-romance"
  - Indirect: "fae", "enemies-to-lovers", "spicy-fantasy"
- [x] Score books by shelf signal strength across user imports
- [x] Threshold for auto-classification vs. manual review queue

### 3.3 Genre Boundary Definition
- [ ] Create "What counts as Romantasy?" documentation
- [x] Define edge cases (paranormal romance, romantic fantasy, etc.)
- [x] Build admin tool for manual genre tagging
- [ ] Allow user feedback on genre classifications (deferred to post-MVP)

---

## Phase 4: Recommendation Algorithm

### 4.1 User-User Similarity Computation
- [x] Implement Pearson correlation on overlapping ratings
- [x] Implement cosine similarity (mean-centered) as alternative
- [x] Add significance weighting:
  ```
  adjusted_sim = raw_sim * (overlap_count / (overlap_count + shrinkage))
  ```
- [x] Set minimum overlap threshold (e.g., 5 books)
- [x] Store top-K neighbors per user (K=100-200)

### 4.2 Batch Similarity Pipeline
- [x] Create nightly batch job for full recomputation
- [ ] Implement incremental updates on new imports (deferred - batch is sufficient for MVP)
- [x] Optimize with sparse matrix operations (scipy/numpy)
- [x] Add progress tracking and logging

### 4.3 Recommendation Scoring
- [x] For each candidate book not read by user:
  ```
  score = Σ (similarity[u,v] * rating[v,b]) / Σ similarity[u,v]
  ```
- [x] Filter to Romantasy-classified books only
- [x] Apply diversity constraints (avoid same-author clusters)
- [x] Generate top-50 recommendations per user

### 4.4 Explainability Engine
- [x] Track which neighbors contributed to each recommendation
- [x] Generate explanation strings:
  - "12 similar readers rated this 4.6★ average"
  - "You and 8 neighbors all loved Fourth Wing"
- [x] Store explanation metadata for UI display

---

## Phase 5: User Authentication & Profiles

### 5.1 Authentication
- [x] Implement email/password auth (or OAuth providers)
- [x] Session management with JWT
- [x] Password reset flow
- [x] Account deletion (GDPR compliance)

### 5.2 User Profiles
- [x] Profile page: username, bio, reading stats
- [x] Privacy settings: private (default) vs. public profile
- [x] Opt-in for "allow my data to power recommendations"
- [x] Data export functionality

### 5.3 Onboarding Flow
- [x] CSV upload option (primary)
- [x] Manual book selection fallback ("Pick 10 books you've read")
- [x] Preference questionnaire:
  - Spice level preference (0-5)
  - YA vs. Adult preference
  - Favorite tropes (multi-select)
  - Tropes to avoid

---

## Phase 6: Frontend Implementation

### 6.1 Core Pages
- [x] Landing page with value prop
- [x] Sign up / Login
- [x] Import page (CSV upload with progress) - part of onboarding
- [x] Profile summary (rating distribution, top shelves, stats)
- [x] "Readers Like You" page (top 20 similar users)
- [x] Recommendations page (filterable, sortable)
- [x] Book detail page
- [x] Browse Romantasy page (public catalog)

### 6.2 Recommendation UI
- [x] Card-based recommendation display (RecommendationCard component)
- [x] "Why this book?" explanation tooltips/modals
- [x] Filters: spice level, YA/adult, tropes
- [x] "Not interested" / "Already read" dismissal
- [x] Add to "Want to Read" list

### 6.3 Social Features (Post-MVP)
- [ ] "Find neighbors" search within app
- [ ] Invite friends via email/link
- [ ] Compare libraries with another user
- [ ] Share recommendation lists

---

## Phase 7: Testing & Quality

### 7.1 Backend Testing
- [x] Unit tests for CSV parser edge cases
- [x] Unit tests for similarity calculations
- [x] Integration tests for import pipeline
- [x] API endpoint tests (auth, books, recommendations)
- [x] pytest configuration with fixtures (conftest.py)

### 7.2 Frontend Testing
- [x] Component tests (Jest + React Testing Library)
  - BookCard, Header, RecommendationCard components
  - API client tests
- [x] E2E tests for critical flows (Playwright)
  - Auth flows (login, register, forgot password)
  - Browse page with filters
  - Landing page navigation

### 7.3 Algorithm Validation
- [ ] Offline evaluation: hold-out test set, measure precision@K
- [x] User feedback collection (thumbs up/down on recs) - implemented in UI

---

## Phase 8: Deployment & Operations

### 8.1 Infrastructure
- [x] Docker configuration (Dockerfile for backend + frontend)
- [x] Docker Compose for local development
- [x] Deploy backend configs (Railway, Fly.io, Render)
- [x] Deploy frontend config (Vercel)
- [x] Set up CI/CD pipelines (GitHub Actions)
- [x] Comprehensive deployment documentation (DEPLOYMENT.md)

### 8.2 Monitoring & Logging
- [x] Application logging (structured JSON in production)
- [x] Request logging middleware with request IDs
- [x] Error tracking (Sentry integration)
- [x] Health check endpoints (/health, /health/ready)
- [x] Security headers middleware

### 8.3 Scaling Considerations
- [x] Database indexing strategy (documented)
- [x] Caching layer (Redis) configuration
- [x] Rate limiting middleware
- [x] Environment-based configuration

---

## MVP Milestone Checklist

The minimum viable product includes:

- [x] Project plan documented
- [x] Database schema implemented
- [x] CSV import + parsing working
- [x] Book deduplication (ISBN + fuzzy matching)
- [x] Romantasy seed list loaded (200+ books)
- [x] User-user similarity computation
- [x] Top-50 recommendations generated
- [x] Basic web UI:
  - [x] Upload CSV (onboarding flow)
  - [x] View recommendations with explanations
  - [x] Filter by spice/tropes
- [x] Deploy to production (infrastructure ready)

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+, TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic |
| Database | PostgreSQL 15+ |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Task Queue | Celery + Redis (or APScheduler for MVP) |
| Auth | JWT (PyJWT) or NextAuth |
| Hosting | Vercel (FE) + Railway/Render (BE) + Supabase/Neon (DB) |

---

## Open Questions

1. **Spice level data source** - User-contributed? Curated list? External source?
2. **Minimum user base for useful recs** - How many imports before similarity is meaningful?
3. **Content moderation** - How to handle inappropriate usernames/bios?
4. **International books** - Support for non-English Romantasy?
5. **Series handling** - Recommend whole series or individual books?
