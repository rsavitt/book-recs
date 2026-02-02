"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.api import router as api_router

settings = get_settings()

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Debug: Log CORS settings on startup
logger.info(f"CORS_ORIGINS env: {settings.CORS_ORIGINS}")
logger.info(f"CORS origins list: {settings.cors_origins_list}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(
        f"Starting {settings.APP_NAME}",
        extra={
            "extra_fields": {
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
            }
        },
    )

    # Auto-create database tables on startup
    try:
        from app.core.database import engine, Base, SessionLocal
        from app.models.user import User
        from app.models.book import Book, BookEdition, BookTag
        from app.models.rating import Rating, Shelf
        from app.models.similarity import UserSimilarity
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")

        # Auto-seed if no books exist
        db = SessionLocal()
        book_count = db.query(Book).count()
        db.close()
        if book_count == 0:
            logger.info("No books found, running seed script...")
            from scripts.seed_books import seed_books
            seed_books()
            logger.info("Seed complete!")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
                integrations=[
                    FastApiIntegration(transaction_style="endpoint"),
                    SqlalchemyIntegration(),
                ],
            )
            logger.info("Sentry initialized successfully")
        except ImportError:
            logger.warning("sentry-sdk not installed, error tracking disabled")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="A collaborative filtering-based recommendation system for Romantasy books",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# CORS middleware - must be added first (outermost)
# Check if any wildcard patterns are used
has_wildcard = any("*" in origin for origin in settings.cors_origins_list)

if has_wildcard:
    # Use allow_origin_regex for wildcard support
    # This regex matches the explicit origins plus any *.vercel.app URL
    import re
    explicit_origins = [re.escape(o) for o in settings.cors_origins_list if "*" not in o]
    # Build regex: explicit origins OR any vercel.app subdomain
    origin_patterns = explicit_origins + [r"https://[a-zA-Z0-9-]+\.vercel\.app"]
    origin_regex = "^(" + "|".join(origin_patterns) + ")$"

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Add other middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting disabled for now - can cause CORS issues
# if settings.ENVIRONMENT == "production":
#     app.add_middleware(
#         RateLimitMiddleware,
#         requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
#     )


@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Returns basic application health status.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Verifies the application can handle requests (database connected, etc).
    """
    from sqlalchemy import text
    from app.core.database import get_db

    try:
        # Check database connection
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    status = "ready" if db_status == "connected" else "not_ready"

    return {
        "status": status,
        "checks": {
            "database": db_status,
        },
    }


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
