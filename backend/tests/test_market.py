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
        # India-only default watchlist.
        for symbol in ["^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "^INDIAVIX",
                       "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
                       "ICICIBANK.NS", "SBIN.NS"]:
            assert symbol in WATCHLIST
        assert "BTC-USD" not in WATCHLIST
        assert "ETH-USD" not in WATCHLIST
        assert "AAPL" not in WATCHLIST
        assert "SPY" not in WATCHLIST
        assert len(WATCHLIST) == 10
    
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
    
    def test_live_data_true_unavailable_is_explicit(self, monkeypatch):
        """Supported Indian symbols must not fabricate data when the provider fails."""
        monkeypatch.setenv("USE_LIVE_DATA", "true")

        import yfinance as yf

        def fail(*args, **kwargs):
            raise RuntimeError("provider offline")

        monkeypatch.setattr(yf, "download", fail)
        df, meta = get_bars("^NSEI", "1d", 30)

        assert df.empty
        assert meta["source"] == "PROVIDER UNAVAILABLE"
        assert meta["status"] == "UNAVAILABLE"


class TestDataQuality:
    """Tests for data quality validation and metadata."""
    
    def test_ohlc_validation_fixes_inconsistencies(self):
        """Test that _validate_ohlc fixes common OHLC issues."""
        from app.services.market import _validate_ohlc
        import pandas as pd
        import numpy as np
        
        # Create DataFrame with OHLC issues
        df = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [99, 103, 101],   # high < close on row 0, high < open on row 2
            "low": [102, 100, 103],   # low > open on row 0, low > close on row 1
            "close": [101, 102, 100],
            "volume": [1000, 1000, 1000],
        })
        
        df_clean, issues = _validate_ohlc(df)
        
        # Issues should be reported
        assert len(issues) > 0
        
        # OHLC should now be consistent
        assert (df_clean["high"] >= df_clean[["open", "close"]].max(axis=1)).all()
        assert (df_clean["low"] <= df_clean[["open", "close"]].min(axis=1)).all()
        assert (df_clean["high"] >= df_clean["low"]).all()
    
    def test_ohlc_validation_positive_prices(self):
        """Test that _validate_ohlc removes rows with non-positive prices."""
        from app.services.market import _validate_ohlc
        import pandas as pd
        
        df = pd.DataFrame({
            "open": [100, -1, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "close": [100, 101, 102],
            "volume": [1000, 1000, 1000],
        })
        
        df_clean, issues = _validate_ohlc(df)
        
        assert any("Non-positive" in issue for issue in issues)
        assert any("Removed" in issue for issue in issues)
        assert len(df_clean) == 2  # One row removed
        assert (df_clean["open"] > 0).all()
    
    def test_gap_detection(self):
        """Test gap detection in time series for intraday timeframes."""
        from app.services.market import _detect_gaps_duplicates
        import pandas as pd
        
        # Create data with a gap (intraday timeframe)
        idx = pd.date_range("2024-01-01", periods=5, freq="h")
        idx = idx.delete(2)  # Remove middle hour
        df = pd.DataFrame({
            "open": [100, 101, 102, 103],
            "high": [101, 102, 103, 104],
            "low": [99, 100, 101, 102],
            "close": [100, 101, 102, 103],
            "volume": [1000, 1000, 1000, 1000],
        }, index=idx)
        
        gaps, duplicates = _detect_gaps_duplicates(df, "1h")
        
        assert len(gaps) > 0
        assert "missing" in gaps[0].lower()
    
    def test_duplicate_detection(self):
        """Test duplicate timestamp detection."""
        from app.services.market import _detect_gaps_duplicates
        import pandas as pd
        
        # Create data with duplicate timestamps
        idx = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"])
        df = pd.DataFrame({
            "open": [100, 101, 102, 103],
            "high": [101, 102, 103, 104],
            "low": [99, 100, 101, 102],
            "close": [100, 101, 102, 103],
            "volume": [1000, 1000, 1000, 1000],
        }, index=idx)
        
        gaps, duplicates = _detect_gaps_duplicates(df, "1d")
        
        assert len(duplicates) > 0
        assert "duplicate" in duplicates[0].lower()


class TestCacheBehavior:
    """Tests for cache write-through behavior."""
    
    def test_cache_write_through(self, monkeypatch):
        """Test that _upsert_market_bars writes to db."""
        from app.services.market import _upsert_market_bars
        from unittest.mock import MagicMock, patch
        import pandas as pd
        
        df = pd.DataFrame({
            "open": [100, 101],
            "high": [101, 102],
            "low": [99, 100],
            "close": [100, 101],
            "volume": [1000, 1000],
        }, index=pd.date_range("2024-01-01", periods=2, freq="D"))
        
        mock_db = MagicMock()
        # Mock the query chain: db.query(MarketBar).filter(...).first()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None  # Direct None, not a mock
        
        with patch("app.models.MarketBar") as mock_bar_class:
            mock_bar = MagicMock()
            mock_bar_class.return_value = mock_bar
            
            count = _upsert_market_bars(mock_db, df, "BTC-USD", "1d", "MOCK GENERATOR")
            
            assert count == 2
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
    
    def test_meta_includes_data_quality(self, monkeypatch):
        """Test that meta includes data_quality field with issues, gaps, duplicates."""
        from app.services.market import get_bars
        
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        df, meta = get_bars("BTC-USD", "1d", 30)
        
        assert "data_quality" in meta
        dq = meta["data_quality"]
        assert "issues" in dq
        assert "gaps" in dq
        assert "duplicates" in dq
        assert "bar_count" in dq
        assert "cached" in dq
        assert dq["bar_count"] == 30
        assert dq["cached"] is False


class TestNiftySymbols:
    """Tests for NIFTY 50 and other Indian index symbols."""
    
    def test_nifty_symbols_in_watchlist(self):
        from app.services.market import WATCHLIST, SYMBOL_NAMES, EXCHANGE_TIMEZONES
        
        assert "^NSEI" in WATCHLIST
        assert "^NSEBANK" in WATCHLIST
        assert SYMBOL_NAMES["^NSEI"] == "NIFTY 50"
        assert SYMBOL_NAMES["^NSEBANK"] == "BANK NIFTY"
        assert EXCHANGE_TIMEZONES["^NSEI"] == "Asia/Kolkata"
        assert EXCHANGE_TIMEZONES["^NSEBANK"] == "Asia/Kolkata"
    
    def test_nifty_mock_data(self, monkeypatch):
        """Test that NIFTY symbols generate mock data correctly."""
        from app.services.market import get_bars
        
        monkeypatch.setenv("USE_LIVE_DATA", "false")
        
        for symbol in ["^NSEI", "^NSEBANK"]:
            df, meta = get_bars(symbol, "1d", 30)
            assert len(df) == 30
            assert meta["symbol"] == symbol
            assert meta["source"] == "MOCK GENERATOR"
            assert meta["status"] == "SIMULATED"
            assert meta["name"] in ["NIFTY 50", "BANK NIFTY"]
            assert meta["exchange_timezone"] == "Asia/Kolkata"