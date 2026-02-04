"""Add pgvector extension and embedding tables for trope classification

Revision ID: 003_add_pgvector_embeddings
Revises: 002_add_reddit_tables
Create Date: 2025-02-03

"""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_add_pgvector_embeddings"
down_revision = "002_add_reddit_tables"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create book_review_embeddings table
    if not table_exists("book_review_embeddings"):
        op.create_table(
            "book_review_embeddings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("book_id", sa.Integer(), nullable=False),
            sa.Column("embedding", sa.dialects.postgresql.ARRAY(sa.Float()), nullable=False),
            sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_review_words", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_review_rating", sa.Float(), nullable=True),
            sa.Column(
                "source_dataset",
                sa.String(50),
                nullable=False,
                server_default="ucsd_goodreads",
            ),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.Column(
                "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_book_review_embeddings_book_id",
            "book_review_embeddings",
            ["book_id"],
            unique=True,
        )
        # Replace the ARRAY column with actual vector type
        op.execute("ALTER TABLE book_review_embeddings DROP COLUMN embedding")
        op.execute(
            "ALTER TABLE book_review_embeddings ADD COLUMN embedding vector(384) NOT NULL"
        )
        # Create IVFFlat index for cosine similarity search
        op.execute(
            "CREATE INDEX ix_book_review_embeddings_embedding "
            "ON book_review_embeddings USING ivfflat (embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )

    # Create trope_seed_embeddings table
    if not table_exists("trope_seed_embeddings"):
        op.create_table(
            "trope_seed_embeddings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("trope_slug", sa.String(100), nullable=False),
            sa.Column("seed_phrase", sa.Text(), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_trope_seed_embeddings_trope_slug",
            "trope_seed_embeddings",
            ["trope_slug"],
        )
        # Add vector column
        op.execute(
            "ALTER TABLE trope_seed_embeddings ADD COLUMN embedding vector(384) NOT NULL"
        )

    # Create book_trope_scores table
    if not table_exists("book_trope_scores"):
        op.create_table(
            "book_trope_scores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("book_id", sa.Integer(), nullable=False),
            sa.Column("trope_slug", sa.String(100), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=False),
            sa.Column(
                "auto_tagged", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column(
                "computed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("book_id", "trope_slug", name="uq_book_trope_score"),
        )
        op.create_index(
            "ix_book_trope_scores_book_id", "book_trope_scores", ["book_id"]
        )
        op.create_index(
            "ix_book_trope_scores_trope_slug", "book_trope_scores", ["trope_slug"]
        )
        op.create_index(
            "ix_book_trope_scores_similarity_score",
            "book_trope_scores",
            ["similarity_score"],
        )
        op.create_index(
            "ix_book_trope_scores_auto_tagged", "book_trope_scores", ["auto_tagged"]
        )


def downgrade() -> None:
    op.drop_table("book_trope_scores")
    op.drop_table("trope_seed_embeddings")
    op.drop_table("book_review_embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
