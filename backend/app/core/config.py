from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Romantasy Recommender"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production

    # Logging
    LOG_LEVEL: str = "INFO"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"  # Comma-separated list

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/romantasy"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        """Convert postgres:// to postgresql:// for SQLAlchemy compatibility."""
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    # Redis (for caching and job queue)
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Auth
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # External APIs
    OPEN_LIBRARY_BASE_URL: str = "https://openlibrary.org"
    GOOGLE_BOOKS_API_KEY: str = ""
    GOOGLE_BOOKS_BASE_URL: str = "https://www.googleapis.com/books/v1"

    # Recommendation settings
    MIN_OVERLAP_FOR_SIMILARITY: int = 5
    SIMILARITY_SHRINKAGE_FACTOR: int = 10
    MAX_NEIGHBORS_PER_USER: int = 200
    RECOMMENDATIONS_PER_USER: int = 50

    # Rate limiting
    RATE_LIMIT_IMPORTS_PER_HOUR: int = 5
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Sentry (error tracking)
    SENTRY_DSN: str = ""

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "romantasy-recs/1.0"

    # Reddit integration weights (for future recommendation integration)
    REDDIT_SENTIMENT_BOOST: float = 0.05  # 5% rating boost for high sentiment
    REDDIT_MIN_MENTIONS_FOR_SIGNAL: int = 3  # Minimum mentions to trust data

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string.

        Supports wildcard patterns for Vercel preview URLs:
        - https://*.vercel.app matches any Vercel preview URL
        """
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

        # Expand Vercel wildcard pattern to allow all Vercel preview URLs
        expanded = []
        for origin in origins:
            if origin == "https://*.vercel.app":
                # Special marker - handled by custom CORS logic
                expanded.append(origin)
            else:
                expanded.append(origin)
        return expanded

    def is_origin_allowed(self, origin: str) -> bool:
        """Check if an origin is allowed, supporting wildcard patterns."""
        if not origin:
            return False

        for allowed in self.cors_origins_list:
            if allowed == origin:
                return True
            # Support Vercel wildcard pattern
            if (
                allowed == "https://*.vercel.app"
                and origin.endswith(".vercel.app")
                and origin.startswith("https://")
            ):
                return True
        return False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
