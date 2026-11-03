"""Add user_id to paper_accounts

Revision ID: 0004_add_user_id_paper
Revises: 0003_phase7_journal_research
Create Date: 2026-11-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_user_id_paper'
down_revision = '0003_phase7_journal_research'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column to paper_accounts table
    op.add_column('paper_accounts', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    
    # Create index for user_id for query performance
    op.create_index('ix_paper_accounts_user_id', 'paper_accounts', ['user_id'])


def downgrade() -> None:
    # Drop the index first
    op.drop_index('ix_paper_accounts_user_id', table_name='paper_accounts')
    
    # Drop the foreign key constraint (Alembic will handle this)
    # We need to drop the constraint explicitly since we named it
    op.drop_constraint('paper_accounts_user_id_fkey', 'paper_accounts', type_='foreignkey')
    
    # Drop the column
    op.drop_column('paper_accounts', 'user_id')