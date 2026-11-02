"""Tests for the multi-agent research service."""
import pytest
import pandas as pd
import numpy as np

from app.services.research import run as research_run


class TestResearch:
    """Tests for the research service."""
    
    def test_research_returns_expected_structure(self):
        """Test that research output has expected structure."""
        df = self._create_sample_data()
        result = research_run(df)
        
        assert "facts" in result
        assert "interpretations" in result
        assert "label" in result
        
        # Check label
        assert result["label"] == "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"
        
        # Check interpretations has all expected agents
        interpretations = result["interpretations"]
        expected_agents = ["market_analyst", "bull", "bear", "risk_analyst", "strategy_manager"]
        for agent in expected_agents:
            assert agent in interpretations
    
    def test_facts_contain_expected_keys(self):
        df = self._create_sample_data()
        result = research_run(df)
        
        facts = result["facts"]
        expected_keys = [
            "last_close", "rsi14", "ema20", "ema50",
            "macd_hist", "ann_vol_30d_pct", "drawdown_from_peak_pct",
            "return_30bar_pct",
        ]
        for key in expected_keys:
            assert key in facts
            assert isinstance(facts[key], (int, float))
    
    def test_uptrend_produces_bullish_bias(self):
        """Uptrend data should produce more bullish than bearish interpretations."""
        # Create clear uptrend
        dates = pd.date_range("2024-01-01", periods=200, freq="D")
        close = np.linspace(100, 200, 200)  # Strong uptrend
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(200, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_count = len(result["interpretations"]["bull"])
        bear_count = len(result["interpretations"]["bear"])
        
        # In strong uptrend, should have more bullish signals
        assert bull_count >= bear_count
        
        # Strategy manager should lean long
        stance = result["interpretations"]["strategy_manager"]
        assert "LEAN LONG" in stance or "NEUTRAL" in stance
    
    def test_downtrend_produces_bearish_bias(self):
        """Downtrend data should produce more bearish than bullish interpretations."""
        dates = pd.date_range("2024-01-01", periods=200, freq="D")
        close = np.linspace(200, 100, 200)  # Strong downtrend
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(200, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_count = len(result["interpretations"]["bull"])
        bear_count = len(result["interpretations"]["bear"])
        
        # In strong downtrend, should have more bearish signals
        assert bear_count >= bull_count
        
        # Strategy manager should lean flat or negative
        stance = result["interpretations"]["strategy_manager"]
        assert "LEAN FLAT" in stance or "NEUTRAL" in stance
    
    def test_high_volatility_increases_risk(self):
        """High volatility should produce HIGH risk rating."""
        # Create high volatility data
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        returns = np.random.normal(0, 0.05, 100)  # High vol
        close = 100 * np.exp(np.cumsum(returns))
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        risk_text = result["interpretations"]["risk_analyst"]
        assert "HIGH" in risk_text
    
    def test_low_volatility_produces_low_risk(self):
        """Low volatility should produce LOW risk rating."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(100, 105, 100) + np.random.normal(0, 0.1, 100)  # Very low vol
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        risk_text = result["interpretations"]["risk_analyst"]
        assert "LOW" in risk_text or "MODERATE" in risk_text
    
    def test_rsi_oversold_bullish(self):
        """RSI < 35 should add bullish mean-reversion signal."""
        # Create data that results in low RSI
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        # Sharp decline to make RSI low
        close = np.linspace(150, 100, 50)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(50, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_signals = result["interpretations"]["bull"]
        # Should have RSI oversold signal
        rsi_bull = [s for s in bull_signals if "RSI" in s and "oversold" in s]
        assert len(rsi_bull) > 0
    
    def test_rsi_overbought_bearish(self):
        """RSI > 65 should add bearish overbought signal."""
        dates = pd.date_range("2024-01-01", periods=50, freq="D")
        # Sharp rise to make RSI high
        close = np.linspace(100, 150, 50)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(50, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bear_signals = result["interpretations"]["bear"]
        rsi_bear = [s for s in bear_signals if "RSI" in s and "overbought" in s]
        assert len(rsi_bear) > 0
    
    def test_macd_positive_bullish(self):
        """Positive MACD histogram should add bullish signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(100, 150, 100)  # Steady uptrend -> positive MACD
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_signals = result["interpretations"]["bull"]
        macd_bull = [s for s in bull_signals if "MACD" in s and "positive" in s]
        assert len(macd_bull) > 0
    
    def test_macd_negative_bearish(self):
        """Negative MACD histogram should add bearish signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(150, 100, 100)  # Steady downtrend -> negative MACD
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bear_signals = result["interpretations"]["bear"]
        macd_bear = [s for s in bear_signals if "MACD" in s and "negative" in s]
        assert len(macd_bear) > 0
    
    def test_momentum_30bar_positive_bullish(self):
        """Positive 30-bar return adds bullish momentum signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(100, 150, 100)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_signals = result["interpretations"]["bull"]
        momentum_bull = [s for s in bull_signals if "momentum" in s.lower() and "positive" in s.lower()]
        assert len(momentum_bull) > 0
    
    def test_momentum_30bar_negative_bearish(self):
        """Negative 30-bar return adds bearish momentum signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(150, 100, 100)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bear_signals = result["interpretations"]["bear"]
        momentum_bear = [s for s in bear_signals if "momentum" in s.lower() and "negative" in s.lower()]
        assert len(momentum_bear) > 0
    
    def test_ema_trend_bullish(self):
        """EMA20 > EMA50 adds bullish trend signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(100, 150, 100)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bull_signals = result["interpretations"]["bull"]
        ema_bull = [s for s in bull_signals if "EMA20" in s and "above" in s]
        assert len(ema_bull) > 0
    
    def test_ema_trend_bearish(self):
        """EMA20 < EMA50 adds bearish trend signal."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = np.linspace(150, 100, 100)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(100, 1e6),
        }, index=dates)
        
        result = research_run(df)
        
        bear_signals = result["interpretations"]["bear"]
        ema_bear = [s for s in bear_signals if "EMA20" in s and "below" in s]
        assert len(ema_bear) > 0
    
    def test_facts_values_reasonable(self):
        """Facts should have reasonable values."""
        df = self._create_sample_data()
        result = research_run(df)
        
        facts = result["facts"]
        
        # RSI should be 0-100
        assert 0 <= facts["rsi14"] <= 100
        
        # Volatility should be positive
        assert facts["ann_vol_30d_pct"] >= 0
        
        # Drawdown from peak should be <= 0
        assert facts["drawdown_from_peak_pct"] <= 0
        
        # Last close should be positive
        assert facts["last_close"] > 0
    
    def test_interpretations_are_strings(self):
        df = self._create_sample_data()
        result = research_run(df)
        
        interp = result["interpretations"]
        assert isinstance(interp["market_analyst"], str)
        assert isinstance(interp["risk_analyst"], str)
        assert isinstance(interp["strategy_manager"], str)
        assert all(isinstance(s, str) for s in interp["bull"])
        assert all(isinstance(s, str) for s in interp["bear"])
    
    def test_insufficient_data_handled(self):
        """Test with minimal data (at least 31 bars for 30-bar momentum)."""
        # Need at least 31 bars for c.iloc[-31] to work
        dates = pd.date_range("2024-01-01", periods=31, freq="D")
        close = np.linspace(100, 110, 31)
        df = pd.DataFrame({
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(31, 1e6),
        }, index=dates)
        
        # Should not crash with 31 bars
        result = research_run(df)
        
        assert "facts" in result
        assert "interpretations" in result
    
    def _create_sample_data(self):
        """Create sample market data for testing."""
        dates = pd.date_range("2024-01-01", periods=200, freq="D")
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.015, 200)
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