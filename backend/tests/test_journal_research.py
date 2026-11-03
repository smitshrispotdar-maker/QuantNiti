"""Tests for the Journal router (journal.py)."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

class MockJournalEntry:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockJournalEntry:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

from app.models import JournalEntry, Strategy, Conversation, BacktestRun, PaperDeployment, ResearchRun
from app.schemas import JournalEntryCreate, JournalEntryUpdate


class TestJournalRouter:
    """Tests for the journal router endpoints."""

    def test_list_entries_empty(self):
        """Test listing entries when none exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        from app.routers.journal import list_entries
        result = list_entries(page=1, page_size=20, db=mock_db)

        assert result.total == 0
        assert result.items == []
        assert result.page == 1
        assert result.page_size == 20

    def test_list_entries_with_data(self):
        """Test listing entries with data."""
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.user_id = 1
        mock_entry.title = "Test Entry"
        mock_entry.decision_type = "strategy_hypothesis"
        mock_entry.status = "draft"
        mock_entry.strategy_id = 1
        mock_entry.strategy_version = 1
        mock_entry.conversation_id = None
        mock_entry.backtest_run_id = None
        mock_entry.research_run_id = None
        mock_entry.deployment_id = None
        mock_entry.hypothesis_rationale = "Test hypothesis"
        mock_entry.evidence_summary = "Test evidence"
        mock_entry.risks_assumptions = "Test risks"
        mock_entry.decision_next_steps = "Test next steps"
        mock_entry.expected_outcome = "Expected profit"
        mock_entry.actual_outcome = None
        mock_entry.recommendation = "Buy"
        mock_entry.evidence = {"key": "value"}
        mock_entry.outcome_review = None
        mock_entry.title = "Test Entry"
        mock_entry.created_at = datetime.now()
        mock_entry.updated_at = datetime.now()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_entry]

        from app.routers.journal import list_entries
        result = list_entries(page=1, page_size=20, db=mock_db)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].title == "Test Entry"
        assert result.items[0].decision_type == "strategy_hypothesis"
        assert result.items[0].status == "draft"

    def test_create_entry_valid(self):
        """Test creating a valid journal entry."""
        mock_db = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.user_id = 1
        mock_db.get.return_value = mock_strategy
        
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        from app.routers.journal import create_entry
        body = JournalEntryCreate(
            title="Test Strategy",
            decision_type="strategy_hypothesis",
            status="draft",
            strategy_id=1,
            hypothesis_rationale="Test hypothesis",
        )
        
        from app.routers.journal import _to_response
        # Mock the _to_response function
        with patch('app.routers.journal._to_response') as mock_to_response:
            mock_to_response.return_value = MagicMock()
            result = create_entry(body, mock_db)
            
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_entry_invalid_strategy(self):
        """Test creating entry with invalid strategy ID."""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        from app.routers.journal import create_entry
        body = JournalEntryCreate(
            title="Test Strategy",
            decision_type="strategy_hypothesis",
            strategy_id=999,
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            create_entry(body, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Strategy not found" in str(exc_info.value.detail)

    def test_get_entry(self):
        """Test getting a single journal entry."""
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.user_id = 1
        mock_entry.title = "Test Entry"
        mock_entry.decision_type = "strategy_hypothesis"
        mock_entry.status = "draft"
        mock_entry.strategy_id = 1
        mock_entry.strategy_version = 1
        mock_entry.conversation_id = None
        mock_entry.backtest_run_id = None
        mock_entry.research_run_id = None
        mock_entry.deployment_id = None
        mock_entry.hypothesis_rationale = "Test hypothesis"
        mock_entry.evidence_summary = "Test evidence"
        mock_entry.risks_assumptions = "Test risks"
        mock_entry.decision_next_steps = "Test next steps"
        mock_entry.expected_outcome = "Expected profit"
        mock_entry.actual_outcome = None
        mock_entry.recommendation = "Buy"
        mock_entry.evidence = {"key": "value"}
        mock_entry.outcome_review = None
        mock_entry.created_at = datetime.now()
        mock_entry.updated_at = datetime.now()

        mock_db = MagicMock()
        mock_db.get.return_value = mock_entry

        from app.routers.journal import get_entry
        from app.routers.journal import _to_response
        with patch('app.routers.journal._to_response') as mock_to_response:
            mock_to_response.return_value = MagicMock()
            result = get_entry(1, mock_db)
            
        mock_db.get.assert_called_once_with(JournalEntry, 1)

    def test_get_entry_not_found(self):
        """Test getting non-existent entry."""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        from app.routers.journal import get_entry
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_entry(999, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Entry not found" in str(exc_info.value.detail)

    def test_update_entry(self):
        """Test updating a journal entry."""
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.user_id = 1
        mock_entry.title = "Old Title"
        mock_entry.decision_type = "strategy_hypothesis"
        mock_entry.status = "draft"
        mock_entry.hypothesis_rationale = "Old rationale"
        
        mock_db = MagicMock()
        mock_db.get.return_value = mock_entry

        from app.routers.journal import update_entry
        body = JournalEntryUpdate(
            title="New Title",
            hypothesis_rationale="New rationale",
        )
        
        with patch('app.routers.journal._to_response') as mock_to_response:
            mock_to_response.return_value = MagicMock()
            result = update_entry(1, body, mock_db)
            
        assert mock_entry.title == "New Title"
        assert mock_entry.hypothesis_rationale == "New rationale"
        mock_db.commit.assert_called_once()

    def test_delete_entry(self):
        """Test deleting a journal entry."""
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.user_id = 1
        
        mock_db = MagicMock()
        mock_db.get.return_value = mock_entry

        from app.routers.journal import delete_entry
        result = delete_entry(1, mock_db)
        
        assert result == {"deleted": True, "id": 1}
        mock_db.delete.assert_called_once_with(mock_entry)
        mock_db.commit.assert_called_once()

    def test_legacy_list(self):
        """Test legacy list endpoint."""
        mock_entry = MagicMock()
        mock_entry.id = 1
        mock_entry.strategy_id = 1
        mock_entry.strategy_version = 1
        mock_entry.recommendation = "Test"
        mock_entry.evidence = {"key": "value"}
        mock_entry.outcome_review = None
        mock_entry.created_at = datetime.now()
        
        mock_db = MagicMock()
        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_entry]

        from app.routers.journal import list_legacy
        result = list_legacy(mock_db)
        
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_add_legacy(self):
        """Test legacy add endpoint."""
        mock_db = MagicMock()
        mock_strategy = MagicMock()
        mock_strategy.id = 1
        mock_strategy.version = 1
        mock_db.get.return_value = mock_strategy
        
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        from app.routers.journal import add_legacy
        from fastapi import HTTPException
        
        body = type('JournalIn', (), {'strategy_id': 1, 'recommendation': 'Test', 'evidence': {}})()
        
        with patch('app.routers.journal.create_entry') as mock_create:
            mock_create.return_value = MagicMock()
            result = add_legacy(body, mock_db)
            
        mock_create.assert_called_once()


class TestResearchRouter:
    """Tests for the Research router endpoints."""

    def test_list_runs_empty(self):
        """Test listing runs when none exist."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        from app.routers.research import list_runs
        result = list_runs(page=1, page_size=20, db=mock_db)

        assert result.total == 0
        assert result.items == []
        assert result.page == 1
        assert result.page_size == 20

    def test_list_runs_with_data(self):
        """Test listing runs with data."""
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.user_id = 1
        mock_run.strategy_id = 1
        mock_run.strategy_version = 1
        mock_run.conversation_id = None
        mock_run.backtest_run_id = None
        mock_run.deployment_id = None
        mock_run.strategy_spec_snapshot = None
        mock_run.backtest_metrics_snapshot = None
        mock_run.facts = {"rsi14": 30}
        mock_run.interpretations = {"market_analyst": "Test"}
        mock_run.label = "AI-GENERATED INTERPRETATION"
        mock_run.data_source = "MOCK"
        mock_run.data_quality = {}
        mock_run.is_simulated = True
        mock_run.created_at = datetime.now()
        mock_run.updated_at = datetime.now()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_run]

        from app.routers.research import list_runs
        result = list_runs(page=1, page_size=20, db=mock_db)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == 1
        assert result.items[0].is_simulated is True

    def test_get_run(self):
        """Test getting a single research run."""
        mock_run = MagicMock()
        mock_run.id = 1
        mock_run.user_id = 1
        mock_run.strategy_id = 1
        mock_run.strategy_version = 1
        mock_run.conversation_id = None
        mock_run.backtest_run_id = None
        mock_run.deployment_id = None
        mock_run.strategy_spec_snapshot = None
        mock_run.backtest_metrics_snapshot = None
        mock_run.facts = {"rsi14": 30}
        mock_run.interpretations = {"market_analyst": "Test"}
        mock_run.label = "AI-GENERATED INTERPRETATION"
        mock_run.data_source = "MOCK"
        mock_run.data_quality = {}
        mock_run.is_simulated = True
        mock_run.created_at = datetime.now()
        mock_run.updated_at = datetime.now()

        mock_db = MagicMock()
        mock_db.get.return_value = mock_run

        from app.routers.research import get_run
        from app.routers.research import _to_response
        with patch('app.routers.research._to_response') as mock_to_response:
            mock_to_response.return_value = MagicMock()
            result = get_run(1, mock_db)
            
        mock_db.get.assert_called_once_with(ResearchRun, 1)

    def test_get_run_not_found(self):
        """Test getting non-existent research run."""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        from app.routers.research import get_run
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_run(999, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Research run not found" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])