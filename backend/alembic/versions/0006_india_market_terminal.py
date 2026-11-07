"""India market terminal: watchlist ordering + manual order take-profit

Revision ID: 0006_india_terminal
Revises: 0005_add_auth_to_user
Create Date: 2026-11-07

"""
from alembic import op
import sqlalchemy as sa


revision = '0006_india_terminal'
down_revision = '0005_add_auth_to_user'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('watchlist_items', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('paper_orders', sa.Column('take_profit_price', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('paper_orders', 'take_profit_price')
    op.drop_column('watchlist_items', 'position')
