"""Tests for the market data service."""
import pytest
import pandas as pd
import numpy as np
import os

from app.services.market import get_bars, _mock, WATCHLIST, YF_INTERVAL, FREQ


class TestMockData:
    """Tests for the deterministic mock data generator."""
    
    def test_mock_returns_dataframe(self):
        df = _mock("BTC-USD", "1d", 100)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 100
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_mock_deterministic(self):
        """Same symbol/timeframe should always produce same data."""
        df1 = _mock("BTC-USD", "1d", 50)
        df2 = _mock("BTC-USD", "1d", 50)
        
        pd.testing.assert_frame_equal(df1, df2)
    
    def test_mock_different_symbols_different(self):
        """Different symbols should produce different data."""
        df1 = _mock("BTC-USD", "1d", 50)
        df2 = _mock("ETH-USD", "1d", 50)
        
        # At least the close prices should differ
        assert not df1["close"].equals(df2["close"])
    
    def test_mock_different_timeframes_different(self):
        """Different timeframes should produce different data."""
        df1 = _mock("BTC-USD", "1d", 50)
        df2 = _mock("BTC-USD", "1h", 50)
        
        # Index frequency should differ
        assert df1.index.freq != df2.index.freq
    
    def test_mock_ohlc_consistency(self):
        """OHLC should be consistent: high >= max(open, close) >= low."""
        df = _mock("BTC-USD", "1d", 100)
        
        assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
        assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
        assert (df["high"] >= df["low"]).all()
    
    def test_mock_positive_prices(self):
        df = _mock("BTC-USD", "1d", 100)
        
        assert (df["open"] > 0).all()
        assert (df["high"] > 0).all()
        assert (df["low"] > 0).all()
        assert (df["close"] > 0).all()
        assert (df["volume"] > 0).all()
    
    def test_mock_metadata(self, monkeypatch):
        # _mock doesn't return metadata, get_bars does
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        df, meta = get_bars("BTC-USD", "1d", 100)
        
        assert meta["symbol"] == "BTC-USD"
        assert meta["timeframe"] == "1d"
        assert meta["source"] == "MOCK GENERATOR"
        assert meta["status"] == "SIMULATED"
        assert "last_bar" in meta
        assert "fetched_at" in meta
        assert meta["label"] == "PAPER/SIMULATED"


class TestGetBars:
    """Tests for the main get_bars function."""
    
    def test_get_bars_mock_mode(self, monkeypatch):
        """Test get_bars with USE_LIVE_DATA=false."""
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, meta = get_bars("BTC-USD", "1d", 60)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 60
        assert meta["source"] == "MOCK GENERATOR"
        assert meta["status"] == "SIMULATED"
        assert meta["label"] == "PAPER/SIMULATED"
    
    def test_get_bars_case_insensitive_symbol(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df1, _ = get_bars("BTC-USD", "1d", 30)
        df2, _ = get_bars("btc-usd", "1d", 30)
        df3, _ = get_bars("Btc-Usd", "1d", 30)
        
        pd.testing.assert_frame_equal(df1, df2)
        pd.testing.assert_frame_equal(df1, df3)
    
    def test_get_bars_slash_normalization(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df1, _ = get_bars("BTC-USD", "1d", 30)
        df2, _ = get_bars("BTC/USD", "1d", 30)
        
        pd.testing.assert_frame_equal(df1, df2)
    
    def test_get_bars_all_timeframes(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        for tf in ["1m", "5m", "15m", "1h", "1d"]:
            df, meta = get_bars("BTC-USD", tf, 30)
            assert len(df) == 30
            assert meta["timeframe"] == tf
    
    def test_get_bars_unknown_symbol(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        # Should still generate mock data for unknown symbols
        df, meta = get_bars("UNKNOWN", "1d", 30)
        
        assert len(df) == 30
        assert meta["symbol"] == "UNKNOWN"
        assert meta["source"] == "MOCK GENERATOR"
    
    def test_get_bars_minimum_bars(self, monkeypatch):
        """Test that requested number of bars are returned for mock."""
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, _ = get_bars("BTC-USD", "1d", 10)  # Request 10
        
        # Mock returns exactly the requested number
        assert len(df) == 10


class TestWatchlist:
    """Tests for the watchlist constant."""
    
    def test_watchlist_contains_expected_symbols(self):
        assert "BTC-USD" in WATCHLIST
        assert "ETH-USD" in WATCHLIST
        assert "AAPL" in WATCHLIST
        assert "SPY" in WATCHLIST
        assert len(WATCHLIST) == 4
    
    def test_yf_interval_mapping(self):
        assert YF_INTERVAL["1m"] == "1m"
        assert YF_INTERVAL["5m"] == "5m"
        assert YF_INTERVAL["15m"] == "15m"
        assert YF_INTERVAL["1h"] == "60m"
        assert YF_INTERVAL["1d"] == "1d"
    
    def test_freq_mapping(self):
        assert FREQ["1m"] == "1min"
        assert FREQ["5m"] == "5min"
        assert FREQ["15m"] == "15min"
        assert FREQ["1h"] == "1h"
        assert FREQ["1d"] == "1D"


class TestMarketDataStructure:
    """Tests for market data structure consistency."""
    
    def test_dataframe_index_is_datetime(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, _ = get_bars("BTC-USD", "1d", 30)
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_dataframe_sorted_by_time(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, _ = get_bars("BTC-USD", "1d", 50)
        assert df.index.is_monotonic_increasing
    
    def test_no_duplicate_timestamps(self, monkeypatch):
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, _ = get_bars("BTC-USD", "1d", 100)
        assert not df.index.duplicated().any()
    
    def test_sufficient_bars_for_indicators(self, monkeypatch):
        """Test that returned data has enough bars for common indicators."""
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        # Request 100 bars, should be enough for SMA 50, EMA 50, RSI 14, etc.
        df, _ = get_bars("BTC-USD", "1d", 100)
        
        assert len(df) >= 100
        # Should have enough for 50-period indicators
        assert len(df) > 50


class TestLiveDataFallback:
    """Tests for live data fallback behavior (when yfinance unavailable)."""
    
    def test_live_data_env_var_respected(self, monkeypatch):
        """When USE_LIVE_DATA=false, should use mock even if yfinance works."""
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        df, meta = get_bars("BTC-USD", "1d", 30)
        
        assert meta["source"] == "MOCK GENERATOR"
        assert meta["status"] == "SIMULATED"
    
    def test_live_data_true_tries_yfinance(self, monkeypatch):
        """When USE_LIVE_DATA=true, should try yfinance first."""
        monkeypatch.setenv("USE_LIVE_DATA", "true")
        
        # We can't easily test yfinance without network, but we can verify
        # the function doesn't crash and returns something
        df, meta = get_bars("BTC-USD", "1d", 30)
        
        # Should return either YAHOO or MOCK (fallback)
        assert meta["source"] in ["YAHOO FINANCE", "MOCK GENERATOR"]
        assert meta["status"] in ["DELAYED", "SIMULATED"]
        assert meta["label"] == "PAPER/SIMULATED"