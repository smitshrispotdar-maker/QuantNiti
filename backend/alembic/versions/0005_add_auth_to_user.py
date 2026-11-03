"""Add authentication fields to users table

Revision ID: 0005_add_auth_to_user
Revises: 0004_user_id_paper
Create Date: 2026-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_add_auth_to_user'
down_revision = '0004_user_id_paper'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hashed_password column (nullable for existing users)
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))
    
    # Add is_active column (default True for existing users)
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')