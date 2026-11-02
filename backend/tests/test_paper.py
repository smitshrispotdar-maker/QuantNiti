"""Tests for the paper trading service (routers/paper.py functions)."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits
from app.services import market, backtest


class TestPaperAccountState:
    """Tests for the _state function that computes account state from orders."""
    
    def test_state_empty_account(self):
        """Test state computation for account with no orders."""
        # Create mock account
        account = MagicMock()
        account.id = 1
        account.name = "Test"
        account.cash = 100_000
        account.starting_cash = 100_000
        account.status = "RUNNING"
        account.strategy_id = None
        account.created_at = datetime.now()
        
        # Mock DB query for orders (empty)
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.order_by.return_value = []
        
        from app.routers.paper import _state
        
        result = _state(mock_db, account)
        
        assert result["id"] == 1
        assert result["name"] == "Test"
        assert result["status"] == "RUNNING"
        assert result["cash"] == 100_000
        assert result["equity"] == 100_000
        assert result["starting_cash"] == 100_000
        assert result["pnl"] == 0
        assert result["positions"] == []
        assert result["label"] == "PAPER/SIMULATED"
    
    def test_state_with_buy_order(self):
        """Test state with a single buy order."""
        account = MagicMock()
        account.id = 1
        account.name = "Test"
        account.cash = 95_000  # After buying 0.5 @ 10,000 = 5,000 cost
        account.starting_cash = 100_000
        account.status = "RUNNING"
        account.strategy_id = None
        account.created_at = datetime.now()
        
        # Mock order
        mock_order = MagicMock()
        mock_order.symbol = "BTC-USD"
        mock_order.side = "BUY"
        mock_order.qty = 0.5
        mock_order.fill_price = 10_000
        mock_order.reason = "manual"
        mock_order.label = "PAPER/SIMULATED"
        mock_order.ts = datetime.now()
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.order_by.return_value = [mock_order]
        
        # Mock market.get_bars for current price
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [11_000]  # Current price higher
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _state
            result = _state(mock_db, account)
        
        assert len(result["positions"]) == 1
        pos = result["positions"][0]
        assert pos["symbol"] == "BTC-USD"
        assert pos["qty"] == 0.5
        assert pos["avg_price"] == 10_000
        assert pos["last"] == 11_000
        assert pos["unrealized"] == 500  # 0.5 * (11000 - 10000)
        assert pos["realized"] == 0
        # Equity = cash + position_value = 95,000 + 0.5 * 11,000 = 100,500
        assert result["equity"] == 100_500
    
    def test_state_with_buy_and_sell(self):
        """Test state with buy then partial sell (realized P&L)."""
        account = MagicMock()
        account.id = 1
        account.cash = 97_500  # After buy 0.5@10k, sell 0.2@11k
        account.starting_cash = 100_000
        account.status = "RUNNING"
        account.name = "Test"
        account.strategy_id = None
        account.created_at = datetime.now()
        
        # Mock orders: buy 0.5 @ 10000, sell 0.2 @ 11000
        mock_buy = MagicMock()
        mock_buy.symbol = "BTC-USD"
        mock_buy.side = "BUY"
        mock_buy.qty = 0.5
        mock_buy.fill_price = 10_000
        
        mock_sell = MagicMock()
        mock_sell.symbol = "BTC-USD"
        mock_sell.side = "SELL"
        mock_sell.qty = 0.2
        mock_sell.fill_price = 11_000
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.order_by.return_value = [mock_buy, mock_sell]
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [11_500]
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _state
            result = _state(mock_db, account)
        
        assert len(result["positions"]) == 1
        pos = result["positions"][0]
        assert pos["qty"] == 0.3  # 0.5 - 0.2
        assert pos["avg_price"] == 10_000  # FIFO: remaining from first buy
        assert pos["last"] == 11_500
        assert pos["unrealized"] == 0.3 * (11_500 - 10_000)
        # Realized: 0.2 * (11000 - 10000) = 200
        assert pos["realized"] == 200
    
    def test_state_multiple_symbols(self):
        """Test state with positions in multiple symbols."""
        account = MagicMock()
        account.id = 1
        account.cash = 80_000
        account.starting_cash = 100_000
        account.status = "RUNNING"
        account.name = "Test"
        account.strategy_id = None
        account.created_at = datetime.now()
        
        mock_orders = []
        for sym, qty, price in [("BTC-USD", 0.5, 20_000), ("ETH-USD", 2.0, 1_500)]:
            mock_order = MagicMock()
            mock_order.symbol = sym
            mock_order.side = "BUY"
            mock_order.qty = qty
            mock_order.fill_price = price
            mock_orders.append(mock_order)
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.order_by.return_value = mock_orders
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            # Return different prices for different symbols
            def side_effect(symbol, *args, **kwargs):
                mock_df = MagicMock()
                if symbol == "BTC-USD":
                    mock_df.close.iloc = [22_000]
                else:
                    mock_df.close.iloc = [1_800]
                return mock_df, {}
            mock_get_bars.side_effect = side_effect
            
            from app.routers.paper import _state
            result = _state(mock_db, account)
        
        assert len(result["positions"]) == 2
        symbols = {p["symbol"] for p in result["positions"]}
        assert symbols == {"BTC-USD", "ETH-USD"}


class TestFillFunction:
    """Tests for the _fill function that executes simulated orders."""
    
    def test_fill_buy_sufficient_cash(self):
        account = MagicMock()
        account.id = 1
        account.cash = 100_000
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value = []  # No existing orders
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [50_000]
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _fill
            order = _fill(mock_db, account, "BTC-USD", "BUY", 1.0, "test")
        
        assert order is not None
        assert order.symbol == "BTC-USD"
        assert order.side == "BUY"
        assert order.qty == 1.0
        assert order.fill_price == 50_000
        assert account.cash == 50_000  # 100k - 50k
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_fill_buy_insufficient_cash(self):
        account = MagicMock()
        account.id = 1
        account.cash = 10_000
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [50_000]
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _fill
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                _fill(mock_db, account, "BTC-USD", "BUY", 1.0, "test")
            
            assert exc_info.value.status_code == 422
            assert "Insufficient simulated cash" in str(exc_info.value.detail)
    
    def test_fill_sell_without_position(self):
        account = MagicMock()
        account.id = 1
        account.cash = 100_000
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value = []  # No holdings
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [50_000]
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _fill
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                _fill(mock_db, account, "BTC-USD", "SELL", 1.0, "test")
            
            assert exc_info.value.status_code == 422
            assert "Cannot sell more than held" in str(exc_info.value.detail)
    
    def test_fill_sell_with_position(self):
        account = MagicMock()
        account.id = 1
        account.cash = 50_000
        account.status = "RUNNING"
        
        # Mock existing buy order
        mock_buy = MagicMock()
        mock_buy.side = "BUY"
        mock_buy.qty = 2.0
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value = [mock_buy]
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            mock_df = MagicMock()
            mock_df.close.iloc = [55_000]
            mock_get_bars.return_value = (mock_df, {})
            
            from app.routers.paper import _fill
            order = _fill(mock_db, account, "BTC-USD", "SELL", 1.0, "test")
        
        assert order.side == "SELL"
        assert order.qty == 1.0
        assert order.fill_price == 55_000
        assert account.cash == 105_000  # 50k + 55k
    
    def test_fill_account_not_running(self):
        account = MagicMock()
        account.status = "PAUSED"
        
        mock_db = MagicMock()
        
        from app.routers.paper import _fill
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            _fill(mock_db, account, "BTC-USD", "BUY", 1.0, "test")
        
        assert exc_info.value.status_code == 409
        assert "orders blocked" in str(exc_info.value.detail)


class TestDeployValidation:
    """Tests for strategy deployment validation."""
    
    def test_deploy_requires_passing_backtest(self):
        """Test that deploy validates backtest results."""
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = None
        
        strategy = MagicMock()
        strategy.id = 5
        strategy.spec = {
            "schema_version": "1.0",
            "name": "Test",
            "instruments": ["BTC-USD"],
            "timeframe": "1d",
            "indicators": [],
            "entry_rules": [],
            "exit_rules": [],
            "risk": {"max_position_pct": 25, "stop_loss_pct": 5, "take_profit_pct": None, "max_drawdown_pct": 25},
        }
        
        mock_db = MagicMock()
        mock_db.get.return_value = strategy  # get Strategy
        mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = None  # No backtest run
        
        from app.routers.paper import deploy
        from fastapi import HTTPException
        from app.schemas import DeployIn
        
        with pytest.raises(HTTPException) as exc_info:
            deploy(1, DeployIn(strategy_id=5), mock_db)
        
        assert exc_info.value.status_code == 422
        assert "Run a backtest before deployment" in str(exc_info.value.detail)
    
    def test_deploy_fails_validation(self):
        """Test deploy fails when backtest validation fails."""
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = None
        
        strategy = MagicMock()
        strategy.id = 5
        strategy.spec = {
            "schema_version": "1.0",
            "name": "Test",
            "instruments": ["BTC-USD"],
            "timeframe": "1d",
            "indicators": [],
            "entry_rules": [],
            "exit_rules": [],
            "risk": {"max_position_pct": 25, "stop_loss_pct": 5, "take_profit_pct": None, "max_drawdown_pct": 10},
        }
        
        # Mock backtest run with failing metrics (drawdown > limit)
        mock_run = MagicMock()
        mock_run.metrics = {"trades": 10, "max_drawdown_pct": 20}
        
        mock_db = MagicMock()
        mock_db.get.return_value = strategy
        mock_db.query.return_value.filter_by.return_value.order_by.return_value.first.return_value = mock_run
        
        from app.routers.paper import deploy
        from fastapi import HTTPException
        from app.schemas import DeployIn
        
        with pytest.raises(HTTPException) as exc_info:
            deploy(1, DeployIn(strategy_id=5), mock_db)
        
        assert exc_info.value.status_code == 422
        assert "exceeds your limit" in str(exc_info.value.detail)


class TestStepEvaluation:
    """Tests for the step function that evaluates strategy on latest bar."""
    
    def test_step_no_strategy_deployed(self):
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = None
        
        mock_db = MagicMock()
        mock_db.get.return_value = account  # _acct returns this account
        
        from app.routers.paper import step
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            step(1, mock_db)
        
        assert exc_info.value.status_code == 409
        assert "No strategy deployed" in str(exc_info.value.detail)
    
    def test_step_generates_buy_signal(self):
        """Test step generates BUY when entry signal fires."""
        import pandas as pd
        from app.routers.paper import step
        
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = 5
        account.cash = 100_000
        
        strategy = MagicMock()
        strategy.spec = {
            "schema_version": "1.0",
            "name": "Test",
            "instruments": ["BTC-USD"],
            "timeframe": "1d",
            "indicators": [],
            "entry_rules": [{"left": "price", "op": ">", "right": 50000}],
            "exit_rules": [],
            "risk": {"max_position_pct": 50, "stop_loss_pct": 5, "take_profit_pct": None, "max_drawdown_pct": 25},
        }
        
        mock_db = MagicMock()
        # First call to get is for _acct (account), second for Strategy
        mock_db.get.side_effect = [account, strategy]
        mock_db.query.return_value.filter_by.return_value = []  # No existing orders
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            with patch("app.routers.paper.backtest.compute") as mock_compute:
                with patch("app.routers.paper.backtest.signals") as mock_signals:
                    # Setup mocks - use price that divides evenly to avoid rounding issues
                    # qty = 100000 * 50 / 100 / 50000 = 1.0 exactly
                    # cost = 1.0 * 50000 = 50000 <= 100000
                    mock_df = MagicMock()
                    mock_df.close.iloc = [50_000]  # Price > 50000 (entry threshold)
                    mock_get_bars.return_value = (mock_df, {})
                    mock_compute.return_value = mock_df
                    mock_signals.return_value = (pd.Series([True]), pd.Series([False]))
                    
                    result = step(1, mock_db)
        
        assert result["action"] == "BUY"
    
    def test_step_generates_sell_signal(self):
        """Test step generates SELL when exit signal fires."""
        import pandas as pd
        from app.routers.paper import step
        
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = 5
        account.cash = 50_000
        
        strategy = MagicMock()
        strategy.spec = {
            "schema_version": "1.0",
            "name": "Test",
            "instruments": ["BTC-USD"],
            "timeframe": "1d",
            "indicators": [],
            "entry_rules": [],
            "exit_rules": [{"left": "price", "op": "<", "right": 50000}],
            "risk": {"max_position_pct": 100, "stop_loss_pct": 5, "take_profit_pct": None, "max_drawdown_pct": 25},
        }
        
        # Mock existing position (1 BTC bought at 55000)
        mock_buy = MagicMock()
        mock_buy.side = "BUY"
        mock_buy.qty = 1.0
        
        mock_db = MagicMock()
        # First call to get is for _acct (account), second for Strategy
        mock_db.get.side_effect = [account, strategy]
        mock_db.query.return_value.filter_by.return_value = [mock_buy]
        
        with patch("app.routers.paper.market.get_bars") as mock_get_bars:
            with patch("app.routers.paper.backtest.compute") as mock_compute:
                with patch("app.routers.paper.backtest.signals") as mock_signals:
                    mock_df = MagicMock()
                    mock_df.close.iloc = [45_000]  # Price < 50000
                    mock_get_bars.return_value = (mock_df, {})
                    mock_compute.return_value = mock_df
                    mock_signals.return_value = (pd.Series([False]), pd.Series([True]))
                    
                    result = step(1, mock_db)
        
        assert result["action"] == "SELL"
    
    def test_step_hold_no_signal(self):
        """Test step returns HOLD when no signal."""
        import pandas as pd
        from app.routers.paper import step
        
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        account.strategy_id = 5
        
        strategy = MagicMock()
        strategy.spec = {
            "schema_version": "1.0",
            "instruments": ["BTC-USD"],
            "timeframe": "1d",
            "indicators": [],
            "entry_rules": [],
            "exit_rules": [],
            "risk": {},
        }
        
        mock_db = MagicMock()
        # First call to get is for _acct (account), second for Strategy
        mock_db.get.side_effect = [account, strategy]
        mock_db.query.return_value.filter_by.return_value = []
        
        with patch("app.routers.paper.backtest.signals") as mock_signals:
            with patch("app.routers.paper.market.get_bars") as mock_get_bars:
                with patch("app.routers.paper.backtest.compute") as mock_compute:
                    mock_df = MagicMock()
                    mock_df.close.iloc = [50_000]
                    mock_get_bars.return_value = (mock_df, {})
                    mock_compute.return_value = mock_df
                    mock_signals.return_value = (pd.Series([False]), pd.Series([False]))
                    
                    result = step(1, mock_db)
        
        assert result["action"] == "HOLD"


class TestControlActions:
    """Tests for account control actions (pause, resume, stop, kill)."""
    
    def test_control_pause(self):
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        
        result = control(1, "pause", mock_db)
        
        assert account.status == "PAUSED"
        assert result["status"] == "PAUSED"
    
    def test_control_resume(self):
        account = MagicMock()
        account.id = 1
        account.status = "PAUSED"
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        
        result = control(1, "resume", mock_db)
        
        assert account.status == "RUNNING"
        assert result["status"] == "RUNNING"
    
    def test_control_stop(self):
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        
        result = control(1, "stop", mock_db)
        
        assert account.status == "STOPPED"
        assert result["status"] == "STOPPED"
    
    def test_control_kill(self):
        account = MagicMock()
        account.id = 1
        account.status = "RUNNING"
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        
        result = control(1, "kill", mock_db)
        
        assert account.status == "KILLED"
        assert result["status"] == "KILLED"
    
    def test_control_kill_irreversible(self):
        """Once killed, cannot resume/pause/stop."""
        account = MagicMock()
        account.id = 1
        account.status = "KILLED"
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            control(1, "resume", mock_db)
        
        assert exc_info.value.status_code == 409
        assert "Kill switch engaged" in str(exc_info.value.detail)
    
    def test_control_invalid_action(self):
        account = MagicMock()
        account.id = 1
        
        mock_db = MagicMock()
        mock_db.get.return_value = account
        
        from app.routers.paper import control
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            control(1, "invalid", mock_db)
        
        assert exc_info.value.status_code == 400


# Need pandas for step tests
import pandas as pd