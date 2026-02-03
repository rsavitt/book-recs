"""Add Why Choose / Reverse Harem classification fields

Revision ID: 001_add_why_choose
Revises:
Create Date: 2025-02-01

"""
import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = '001_add_why_choose'
down_revision = None
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add Why Choose classification fields to books table (if they don't exist)
    if not column_exists('books', 'is_why_choose'):
        op.add_column('books', sa.Column('is_why_choose', sa.Boolean(), nullable=False, server_default='false'))
    if not column_exists('books', 'why_choose_confidence'):
        op.add_column('books', sa.Column('why_choose_confidence', sa.Float(), nullable=False, server_default='0.0'))

    # Create index if column exists
    try:
        op.create_index('ix_books_is_why_choose', 'books', ['is_why_choose'])
    except Exception:
        pass  # Index may already exist

    # Add user preference for excluding Why Choose
    if not column_exists('users', 'exclude_why_choose'):
        op.add_column('users', sa.Column('exclude_why_choose', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    # Remove user preference
    op.drop_column('users', 'exclude_why_choose')

    # Remove Why Choose fields from books
    op.drop_index('ix_books_is_why_choose', 'books')
    op.drop_column('books', 'why_choose_confidence')
    op.drop_column('books', 'is_why_choose')
