"""Add Reddit data tables for book metrics and recommendation edges

Revision ID: 002_add_reddit_tables
Revises: 001_add_why_choose
Create Date: 2025-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '002_add_reddit_tables'
down_revision = '001_add_why_choose'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create book_reddit_metrics table
    if not table_exists('book_reddit_metrics'):
        op.create_table(
            'book_reddit_metrics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('book_id', sa.Integer(), nullable=False),
            sa.Column('mention_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('recommendation_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('warning_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('sentiment_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('tropes_mentioned', JSON(), nullable=True),
            sa.Column('first_seen', sa.Date(), nullable=True),
            sa.Column('last_updated', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_book_reddit_metrics_book_id', 'book_reddit_metrics', ['book_id'], unique=True)
        op.create_index('ix_book_reddit_metrics_mention_count', 'book_reddit_metrics', ['mention_count'])
        op.create_index('ix_book_reddit_metrics_sentiment_score', 'book_reddit_metrics', ['sentiment_score'])

    # Create book_recommendation_edges table
    if not table_exists('book_recommendation_edges'):
        op.create_table(
            'book_recommendation_edges',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('source_book_id', sa.Integer(), nullable=False),
            sa.Column('target_book_id', sa.Integer(), nullable=False),
            sa.Column('mention_count', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('weight', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('sample_context', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['source_book_id'], ['books.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['target_book_id'], ['books.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('source_book_id', 'target_book_id', name='uq_recommendation_edge'),
        )
        op.create_index('ix_book_recommendation_edges_source_book_id', 'book_recommendation_edges', ['source_book_id'])
        op.create_index('ix_book_recommendation_edges_target_book_id', 'book_recommendation_edges', ['target_book_id'])


def downgrade() -> None:
    # Drop book_recommendation_edges table
    op.drop_index('ix_book_recommendation_edges_target_book_id', 'book_recommendation_edges')
    op.drop_index('ix_book_recommendation_edges_source_book_id', 'book_recommendation_edges')
    op.drop_table('book_recommendation_edges')

    # Drop book_reddit_metrics table
    op.drop_index('ix_book_reddit_metrics_sentiment_score', 'book_reddit_metrics')
    op.drop_index('ix_book_reddit_metrics_mention_count', 'book_reddit_metrics')
    op.drop_index('ix_book_reddit_metrics_book_id', 'book_reddit_metrics')
    op.drop_table('book_reddit_metrics')
