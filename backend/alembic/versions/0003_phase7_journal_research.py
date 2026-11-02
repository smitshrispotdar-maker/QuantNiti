"""Phase 7: Enhanced JournalEntry and ResearchRun models

Revision ID: 0003_phase7_journal_research
Revises: 0002_watchlist_items
Create Date: 2024-11-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '0003_phase7_journal_research'
down_revision = '0002_watchlist_items'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create research_runs table
    op.create_table(
        'research_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('strategy_id', sa.Integer(), sa.ForeignKey('strategies.id'), nullable=True),
        sa.Column('strategy_version', sa.Integer(), nullable=True),
        sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id'), nullable=True),
        sa.Column('backtest_run_id', sa.Integer(), sa.ForeignKey('backtest_runs.id'), nullable=True),
        sa.Column('deployment_id', sa.Integer(), sa.ForeignKey('paper_deployments.id'), nullable=True),
        sa.Column('strategy_spec_snapshot', sa.JSONB(), nullable=True),
        sa.Column('backtest_metrics_snapshot', sa.JSONB(), nullable=True),
        sa.Column('facts', sa.JSONB(), nullable=True),
        sa.Column('interpretations', sa.JSONB(), nullable=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('data_source', sa.String(), nullable=True),
        sa.Column('data_quality', sa.JSONB(), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_research_runs_user_id', 'research_runs', ['user_id'])
    op.create_index('ix_research_runs_strategy_id', 'research_runs', ['strategy_id'])
    op.create_index('ix_research_runs_conversation_id', 'research_runs', ['conversation_id'])
    op.create_index('ix_research_runs_backtest_run_id', 'research_runs', ['backtest_run_id'])
    op.create_index('ix_research_runs_deployment_id', 'research_runs', ['deployment_id'])

    # Add new columns to journal table
    op.add_column('journal', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, server_default='1'))
    op.add_column('journal', sa.Column('decision_type', sa.String(), nullable=False, server_default='general_note'))
    op.add_column('journal', sa.Column('status', sa.String(), nullable=False, server_default='draft'))
    op.add_column('journal', sa.Column('title', sa.String(), nullable=False, server_default=''))
    op.add_column('journal', sa.Column('conversation_id', sa.Integer(), sa.ForeignKey('conversations.id'), nullable=True))
    op.add_column('journal', sa.Column('backtest_run_id', sa.Integer(), sa.ForeignKey('backtest_runs.id'), nullable=True))
    op.add_column('journal', sa.Column('research_run_id', sa.Integer(), sa.ForeignKey('research_runs.id'), nullable=True))
    op.add_column('journal', sa.Column('deployment_id', sa.Integer(), sa.ForeignKey('paper_deployments.id'), nullable=True))
    op.add_column('journal', sa.Column('hypothesis_rationale', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('evidence_summary', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('risks_assumptions', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('decision_next_steps', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('expected_outcome', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('actual_outcome', sa.Text(), nullable=True))
    op.add_column('journal', sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()))
    
    # Remove server defaults after adding columns
    op.alter_column('journal', 'user_id', server_default=None)
    op.alter_column('journal', 'decision_type', server_default=None)
    op.alter_column('journal', 'status', server_default=None)
    op.alter_column('journal', 'title', server_default=None)

    op.create_index('ix_journal_user_id', 'journal', ['user_id'])
    op.create_index('ix_journal_strategy_id', 'journal', ['strategy_id'])
    op.create_index('ix_journal_conversation_id', 'journal', ['conversation_id'])
    op.create_index('ix_journal_backtest_run_id', 'journal', ['backtest_run_id'])
    op.create_index('ix_journal_research_run_id', 'journal', ['research_run_id'])
    op.create_index('ix_journal_deployment_id', 'journal', ['deployment_id'])
    op.create_index('ix_journal_status', 'journal', ['status'])
    op.create_index('ix_journal_decision_type', 'journal', ['decision_type'])


def downgrade() -> None:
    op.drop_index('ix_journal_decision_type', table_name='journal')
    op.drop_index('ix_journal_status', table_name='journal')
    op.drop_index('ix_journal_deployment_id', table_name='journal')
    op.drop_index('ix_journal_research_run_id', table_name='journal')
    op.drop_index('ix_journal_backtest_run_id', table_name='journal')
    op.drop_index('ix_journal_conversation_id', table_name='journal')
    op.drop_index('ix_journal_strategy_id', table_name='journal')
    op.drop_index('ix_journal_user_id', table_name='journal')

    op.drop_column('journal', 'updated_at')
    op.drop_column('journal', 'actual_outcome')
    op.drop_column('journal', 'expected_outcome')
    op.drop_column('journal', 'decision_next_steps')
    op.drop_column('journal', 'risks_assumptions')
    op.drop_column('journal', 'evidence_summary')
    op.drop_column('journal', 'hypothesis_rationale')
    op.drop_column('journal', 'deployment_id')
    op.drop_column('journal', 'research_run_id')
    op.drop_column('journal', 'backtest_run_id')
    op.drop_column('journal', 'conversation_id')
    op.drop_column('journal', 'title')
    op.drop_column('journal', 'status')
    op.drop_column('journal', 'decision_type')
    op.drop_column('journal', 'user_id')

    op.drop_index('ix_research_runs_deployment_id', table_name='research_runs')
    op.drop_index('ix_research_runs_backtest_run_id', table_name='research_runs')
    op.drop_index('ix_research_runs_conversation_id', table_name='research_runs')
    op.drop_index('ix_research_runs_strategy_id', table_name='research_runs')
    op.drop_index('ix_research_runs_user_id', table_name='research_runs')
    op.drop_table('research_runs')