from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Profile
    display_name: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)

    # Privacy settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_data_for_recs: Mapped[bool] = mapped_column(Boolean, default=True)

    # Preferences (onboarding)
    spice_preference: Mapped[int | None] = mapped_column(Integer)  # 0-5 scale
    prefers_ya: Mapped[bool | None] = mapped_column(Boolean)  # True=YA, False=Adult, None=Both
    exclude_why_choose: Mapped[bool] = mapped_column(Boolean, default=True)  # Filter out reverse harem/why choose

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_import_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    ratings: Mapped[list["Rating"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    shelves: Mapped[list["Shelf"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# Forward reference for type hints
from app.models.rating import Rating, Shelf  # noqa: E402
