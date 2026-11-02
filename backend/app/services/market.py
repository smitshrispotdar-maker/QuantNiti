"""Market data: Yahoo Finance (free) with deterministic mock fallback and optional DB caching.
Every response carries source + freshness + data quality metadata."""
import os, zlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import pandas as pd

from app.config import get_settings

# Cache TTL configuration (seconds) - loaded from settings
def _get_ttl_config() -> dict:
    """Get TTL configuration from settings."""
    settings = get_settings()
    return settings.market_data_ttl

WATCHLIST = ["BTC-USD", "ETH-USD", "AAPL", "SPY", "^NSEI", "^NSEBANK"]
FREQ = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "1d": "1D"}
YF_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}
BASE = {"BTC-USD": 65000, "ETH-USD": 3200, "AAPL": 190, "SPY": 520, "^NSEI": 25000, "^NSEBANK": 52000}

SYMBOL_NAMES = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "AAPL": "Apple Inc.",
    "SPY": "SPDR S&P 500 ETF",
    "^NSEI": "NIFTY 50",
    "^NSEBANK": "NIFTY Bank",
}

EXCHANGE_TIMEZONES = {
    "BTC-USD": "UTC",
    "ETH-USD": "UTC",
    "AAPL": "America/New_York",
    "SPY": "America/New_York",
    "^NSEI": "Asia/Kolkata",
    "^NSEBANK": "Asia/Kolkata",
}


def _mock(symbol: str, tf: str, n: int) -> pd.DataFrame:
    """Deterministic mock data generator using seeded RNG per symbol/timeframe."""
    rng = np.random.default_rng(zlib.crc32(f"{symbol}{tf}".encode()))
    base = BASE.get(symbol, 100)
    vol_scale = 0.018 if "USD" in symbol else (0.015 if symbol.startswith("^") else 0.011)
    ret = rng.normal(0.0004, vol_scale, n)
    close = base * np.exp(np.cumsum(ret))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.008, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.008, n))
    volume = rng.uniform(1e3, 1e5, n) if not symbol.startswith("^") else rng.uniform(1e6, 1e7, n)
    end = pd.Timestamp.utcnow().floor(FREQ[tf]).tz_localize(None)
    idx = pd.date_range(end=end, periods=n, freq=FREQ[tf])
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def _validate_ohlc(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate and fix OHLC consistency. Returns (cleaned_df, issues_list)."""
    issues = []
    df = df.copy()
    
    # Ensure high >= max(open, close) and low <= min(open, close)
    high_fixed = df["high"].where(df["high"] >= df[["open", "close"]].max(axis=1), df[["open", "close"]].max(axis=1))
    low_fixed = df["low"].where(df["low"] <= df[["open", "close"]].min(axis=1), df[["open", "close"]].min(axis=1))
    
    if not high_fixed.equals(df["high"]):
        issues.append("Fixed high < max(open, close) on some rows")
    if not low_fixed.equals(df["low"]):
        issues.append("Fixed low > min(open, close) on some rows")
    
    df["high"] = high_fixed
    df["low"] = low_fixed
    
    # Ensure high >= low
    if (df["high"] < df["low"]).any():
        df["high"] = df[["high", "low"]].max(axis=1)
        df["low"] = df[["high", "low"]].min(axis=1)
        issues.append("Fixed high < low on some rows")
    
    # Ensure positive prices
    for col in ["open", "high", "low", "close"]:
        if (df[col] <= 0).any():
            issues.append(f"Non-positive {col} values found")
            df[col] = df[col].clip(lower=1e-8)
    
    # Volume non-negative
    if "volume" in df.columns and (df["volume"] < 0).any():
        issues.append("Negative volume values found")
        df["volume"] = df["volume"].clip(lower=0)
    
    return df, issues


def _detect_gaps_duplicates(df: pd.DataFrame, tf: str) -> Tuple[List[str], List[str]]:
    """Detect missing timestamps (gaps) and duplicate timestamps. Returns (gaps, duplicates)."""
    if len(df) < 2:
        return [], []
    
    gaps = []
    duplicates = []
    
    # Check for duplicate timestamps
    dup_mask = df.index.duplicated(keep=False)
    if dup_mask.any():
        dup_count = dup_mask.sum()
        duplicates.append(f"{dup_count} duplicate timestamp(s) found")
    
    # Check for gaps (expected frequency) - skip for daily timeframe
    if tf != "1d":
        expected_freq = FREQ.get(tf)
        if expected_freq:
            try:
                expected_range = pd.date_range(start=df.index[0], end=df.index[-1], freq=expected_freq)
                missing = expected_range.difference(df.index)
                if len(missing) > 0:
                    gaps.append(f"{len(missing)} missing bar(s) detected (expected {len(expected_range)}, got {len(df)})")
            except Exception:
                pass  # Some frequencies may not work with date_range
    
    return gaps, duplicates


def _is_cache_fresh(cached_bars: list, timeframe: str) -> Tuple[bool, Optional[float]]:
    """
    Check if cached data is fresh based on TTL configuration.
    
    Returns:
        Tuple of (is_fresh: bool, cache_age_seconds: float)
    """
    if not cached_bars:
        return False, None
    
    # Get the cache write time from the newest bar's timestamp
    # Note: This uses the bar timestamp as a proxy for cache write time
    # In a production system, we would store a separate cached_at timestamp
    newest_bar_ts = cached_bars[-1].ts
    cache_age_seconds = (datetime.utcnow() - newest_bar_ts).total_seconds()
    
    ttl_config = _get_ttl_config()
    ttl_seconds = ttl_config.get(timeframe, 3600)
    
    is_fresh = cache_age_seconds < ttl_seconds
    return is_fresh, cache_age_seconds


def _upsert_market_bars(db, df: pd.DataFrame, symbol: str, tf: str, source: str) -> int:
    """Write-through cache: upsert bars into MarketBar table. Returns count of inserted/updated rows."""
    if db is None:
        return 0
    
    from app.models import MarketBar
    
    count = 0
    for ts, row in df.iterrows():
        try:
            bar = db.query(MarketBar).filter(
                MarketBar.symbol == symbol,
                MarketBar.timeframe == tf,
                MarketBar.ts == ts
            ).first()
            
            if bar:
                bar.open = float(row["open"])
                bar.high = float(row["high"])
                bar.low = float(row["low"])
                bar.close = float(row["close"])
                bar.volume = float(row["volume"]) if "volume" in row and pd.notna(row["volume"]) else 0.0
                bar.source = source
            else:
                bar = MarketBar(
                    symbol=symbol,
                    timeframe=tf,
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]) if "volume" in row and pd.notna(row["volume"]) else 0.0,
                    source=source
                )
                db.add(bar)
            count += 1
        except Exception:
            # Silently skip individual bar errors, don't fail the whole request
            pass
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        count = 0
    
    return count


def _meta(
    symbol: str, 
    tf: str, 
    df: pd.DataFrame, 
    source: str, 
    status: str,
    issues: Optional[List[str]] = None,
    gaps: Optional[List[str]] = None,
    duplicates: Optional[List[str]] = None,
    cached: bool = False,
    cache_age_seconds: Optional[float] = None,
    cache_ttl_seconds: Optional[int] = None,
    is_stale: bool = False,
    cache_write_timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Build metadata dictionary with quality information."""
    meta = {
        "symbol": symbol,
        "name": SYMBOL_NAMES.get(symbol, symbol),
        "timeframe": tf,
        "source": source,
        "status": status,
        "last_bar": df.index[-1].isoformat() if len(df) > 0 else None,
        "fetched_at": datetime.utcnow().isoformat(),
        "label": "PAPER/SIMULATED",
        "exchange_timezone": EXCHANGE_TIMEZONES.get(symbol, "UTC"),
        "data_quality": {
            "issues": issues or [],
            "gaps": gaps or [],
            "duplicates": duplicates or [],
            "bar_count": len(df),
            "cached": cached,
            "cache_age_seconds": cache_age_seconds,
            "cache_ttl_seconds": cache_ttl_seconds,
            "is_stale": is_stale,
            "cache_write_timestamp": cache_write_timestamp,
        }
    }
    return meta


def get_bars(
    symbol: str, 
    tf: str = "1d", 
    n: int = 300,
    db: Optional[Any] = None,
    use_cache: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Returns (DataFrame, meta). Falls back to MOCK when live data is unavailable.
    
    Implements cache decision flow:
    1. Try cache first if db provided and use_cache enabled
    2. Check cache freshness using TTL
    3. If fresh, return cached data
    4. If stale or missing, attempt to fetch live data
    5. If live fetch fails but usable cache exists, return stale data with warning
    5. If no usable data, fall back to mock
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USD', '^NSEI')
        tf: Timeframe ('1m', '5m', '15m', '1h', '1d')
        n: Number of bars to return
        db: Optional SQLAlchemy session for caching
        use_cache: Whether to read from cache first
    
    Returns:
        (DataFrame with OHLCV + indicators, metadata dict)
    """
    symbol = symbol.upper().replace("/", "-")
    
    # Try cache first if db provided and use_cache enabled
    cached_bars = None
    if db is not None and use_cache:
        from app.models import MarketBar
        try:
            cached_bars = db.query(MarketBar).filter(
                MarketBar.symbol == symbol,
                MarketBar.timeframe == tf
            ).order_by(MarketBar.ts.desc()).limit(n).all()
            
            if cached_bars:
                cached_bars.reverse()  # chronological order
                df = pd.DataFrame([{
                    "open": b.open, "high": b.high, "low": b.low, 
                    "close": b.close, "volume": b.volume
                } for b in cached_bars], index=pd.to_datetime([b.ts for b in cached_bars]))
                
                # Check cache freshness
                is_fresh, cache_age = _is_cache_fresh(cached_bars, tf)
                
                if is_fresh:
                    # Fresh cache - return immediately
                    ttl_config = _get_ttl_config()
                    ttl_seconds = ttl_config.get(tf, 3600)
                    meta = _meta(
                        symbol, tf, df, cached_bars[0].source, "CACHED",
                        cached=True, cache_age_seconds=cache_age,
                        cache_ttl_seconds=ttl_seconds, is_stale=False,
                        cache_write_timestamp=cached_bars[-1].ts.isoformat()
                    )
                    return df, meta
                
                # Cache is stale - we'll try to fetch fresh data but keep cached as fallback
                stale_cache_df = df
                ttl_config = _get_ttl_config()
                ttl_seconds = ttl_config.get(tf, 3600)
                stale_cache_meta = _meta(
                    symbol, tf, df, cached_bars[0].source, "STALE",
                    cached=True, cache_age_seconds=cache_age,
                    cache_ttl_seconds=ttl_seconds, is_stale=True,
                    cache_write_timestamp=cached_bars[-1].ts.isoformat()
                )
        except Exception:
            pass  # Cache read failed, fall through to live/mock
    
    # Try live data
    live_df = None
    live_meta = None
    live_error = None
    
    if os.getenv("USE_LIVE_DATA", "true") == "true":
        try:
            import yfinance as yf
            period = "2y" if tf == "1d" else ("60d" if tf in ("5m", "15m", "1h") else "5d")
            df = yf.download(symbol, period=period, interval=YF_INTERVAL[tf], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna().tail(n)
            
            if len(df) > 30:
                df.index = pd.to_datetime(df.index).tz_localize(None)
                
                # Validate OHLC
                df, issues = _validate_ohlc(df)
                
                # Detect gaps/duplicates
                gaps, duplicates = _detect_gaps_duplicates(df, tf)
                
                # Write to cache
                if db is not None:
                    _upsert_market_bars(db, df, symbol, tf, "YAHOO FINANCE")
                
                meta = _meta(symbol, tf, df, "YAHOO FINANCE", "DELAYED", issues, gaps, duplicates, cached=False, cache_ttl_seconds=None, is_stale=False, cache_write_timestamp=None)
                return df, meta
        except Exception as e:
            live_error = str(e)
            pass
    
    # If we have stale cache and live failed, return stale data with warning
    if 'stale_cache_df' in locals() and stale_cache_df is not None:
        stale_cache_meta["data_quality"]["issues"] = stale_cache_meta["data_quality"].get("issues", []) + \
            [f"Live data unavailable ({live_error if live_error else 'unknown error'}); returning stale cached data"]
        return stale_cache_df, stale_cache_meta
    
    # Fallback to mock
    df = _mock(symbol, tf, n)
    df, issues = _validate_ohlc(df)  # Mock should be valid, but validate anyway
    gaps, duplicates = _detect_gaps_duplicates(df, tf)
    
    # Write mock to cache if db provided
    if db is not None:
        _upsert_market_bars(db, df, symbol, tf, "MOCK GENERATOR")
    
    meta = _meta(symbol, tf, df, "MOCK GENERATOR", "SIMULATED", issues, gaps, duplicates, cached=False, cache_ttl_seconds=None, is_stale=False, cache_write_timestamp=None)
    return df, meta