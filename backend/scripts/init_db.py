"""
Initialize database tables.

Run this once after deployment to create all tables.
Usage: python -m scripts.init_db
"""

from app.core.database import engine, Base
from app.models import *  # noqa: F401, F403


def init_db():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
