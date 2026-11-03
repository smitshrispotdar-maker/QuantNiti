"""Pytest configuration and fixtures for QuantNiti backend tests."""
import sys
import os
from pathlib import Path

# Set test environment BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Import the app for dependency overrides
from app.main import app
from app.services.auth import get_current_user_dep
from app.models import User, Base
from app.db import SessionLocal, engine


@pytest.fixture(autouse=True, scope="session")
def create_test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_auth():
    """Override the authentication dependency for tests."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.is_active = True
    mock_user.created_at = datetime.now()
    
    app.dependency_overrides[get_current_user_dep] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def sample_strategy_spec():
    """Create a valid StrategySpec for testing."""
    from app.schemas import StrategySpec, IndicatorSpec, Rule, RiskLimits
    
    return StrategySpec(
        name="Test Strategy",
        instruments=["BTC-USD"],
        timeframe="1d",
        indicators=[
            IndicatorSpec(id="ema_20", type="EMA", params={"period": 20}),
            IndicatorSpec(id="ema_50", type="EMA", params={"period": 50}),
        ],
        entry_rules=[
            Rule(left="ema_20", op="crosses_above", right="ema_50"),
        ],
        exit_rules=[
            Rule(left="ema_20", op="crosses_below", right="ema_50"),
        ],
        risk=RiskLimits(
            max_position_pct=25,
            stop_loss_pct=5,
            take_profit_pct=10,
            max_drawdown_pct=20,
        ),
    )


@pytest.fixture
def sample_market_data():
    """Create deterministic sample market data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    
    # Generate realistic price data with trend
    returns = np.random.normal(0.0005, 0.02, 200)
    close = 100 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "open": close * (1 + np.random.uniform(-0.005, 0.005, 200)),
        "high": close * (1 + np.random.uniform(0, 0.01, 200)),
        "low": close * (1 - np.random.uniform(0, 0.01, 200)),
        "close": close,
        "volume": np.random.uniform(1e6, 1e7, 200),
    }, index=dates)
    
    # Ensure OHLC consistency
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    
    return df


@pytest.fixture
def trending_up_data():
    """Create market data with clear upward trend for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = np.linspace(100, 150, 100)  # Steady uptrend
    
    df = pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(100, 1e6),
    }, index=dates)
    return df


@pytest.fixture
def trending_down_data():
    """Create market data with clear downward trend for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = np.linspace(150, 100, 100)  # Steady downtrend
    
    df = pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(100, 1e6),
    }, index=dates)
    return df


@pytest.fixture
def sideways_data():
    """Create market data moving sideways for testing."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    close = 100 + 5 * np.sin(np.linspace(0, 4*np.pi, 100))  # Oscillating
    
    df = pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "volume": np.full(100, 1e6),
    }, index=dates)
    return df


# Helper functions for tests
def assert_metrics_structure(metrics: dict):
    """Assert that metrics dict has expected structure."""
    expected_keys = {
        "total_return_pct", "max_drawdown_pct", "sharpe",
        "win_rate_pct", "profit_factor", "exposure_pct", "trades"
    }
    assert set(metrics.keys()) == expected_keys
    assert isinstance(metrics["trades"], int)
    assert metrics["trades"] >= 0


def assert_equity_curve_structure(curve: list):
    """Assert that equity curve has expected structure."""
    assert isinstance(curve, list)
    assert len(curve) > 0
    for point in curve:
        assert "ts" in point
        assert "equity" in point
        assert "drawdown" in point
        assert isinstance(point["equity"], (int, float))
        assert isinstance(point["drawdown"], (int, float))


def assert_trades_structure(trades: list):
    """Assert that trades list has expected structure."""
    assert isinstance(trades, list)
    for trade in trades:
        assert "entry" in trade
        assert "exit" in trade
        assert "pnl" in trade
        assert "ret" in trade
        assert "reason" in trade
        assert "ts" in trade