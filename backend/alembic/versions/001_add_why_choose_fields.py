"""Add Why Choose / Reverse Harem classification fields

Revision ID: 001_add_why_choose
Revises:
Create Date: 2025-02-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_why_choose'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Why Choose classification fields to books table
    op.add_column('books', sa.Column('is_why_choose', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('books', sa.Column('why_choose_confidence', sa.Float(), nullable=False, server_default='0.0'))
    op.create_index('ix_books_is_why_choose', 'books', ['is_why_choose'])

    # Add user preference for excluding Why Choose
    op.add_column('users', sa.Column('exclude_why_choose', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    # Remove user preference
    op.drop_column('users', 'exclude_why_choose')

    # Remove Why Choose fields from books
    op.drop_index('ix_books_is_why_choose', 'books')
    op.drop_column('books', 'why_choose_confidence')
    op.drop_column('books', 'is_why_choose')
