"""add watchlist_items table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'watchlist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'symbol', name='uq_watchlist_user_symbol')
    )
    op.create_index('ix_watchlist_items_user_id', 'watchlist_items', ['user_id'])


def downgrade():
    op.drop_index('ix_watchlist_items_user_id', table_name='watchlist_items')
    op.drop_table('watchlist_items')