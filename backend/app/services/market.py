"""Market data: Yahoo Finance (free) with optional DB caching.

QuantNiti is India-only.  The supported universe and display names live in
``services.instruments``; this module only knows how to fetch and validate
OHLCV data.  Every response carries source + freshness + data-quality metadata.

Important honesty rules:
  * Yahoo Finance is a *delayed* source for NSE/BSE — it is never labelled LIVE.
  * For supported Indian instruments we never fall back to synthetic prices.
    If the provider is unavailable we return an empty frame with status
    ``UNAVAILABLE`` so the UI can show an explicit not-connected state.
  * The deterministic mock generator is retained only for legacy/unknown
    symbols used by older strategies and unit tests; it is always labelled
    SIMULATED.
"""
import os, zlib
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
import pandas as pd

from app.config import get_settings
from app.services import instruments as inst

# Cache TTL configuration (seconds) - loaded from settings
def _get_ttl_config() -> dict:
    """Get TTL configuration from settings."""
    settings = get_settings()
    return settings.market_data_ttl

# India-only default watchlist (canonical = provider ticker).
WATCHLIST = list(inst.DEFAULT_WATCHLIST)
FREQ = {"1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D", "1w": "1W"}
YF_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "4h": "60m", "1d": "1d", "1w": "1wk"}
RESAMPLE = {"4h": "4h", "1w": "W-FRI"}
BASE = {i["symbol"]: (25000 if i["symbol"] == "^NSEI" else 52000 if i["symbol"] == "^NSEBANK" else 100)
        for i in inst.INSTRUMENTS}

SYMBOL_NAMES = dict(inst.SYMBOL_NAMES)
EXCHANGE_TIMEZONES = {s: "Asia/Kolkata" for s in inst.SYMBOL_NAMES}
EXCHANGES = dict(inst.EXCHANGES)

# Name aliases used by older code/tests.
SYMBOL_NAMES.setdefault("^NSEBANK", "BANK NIFTY")


def _mock(symbol: str, tf: str, n: int) -> pd.DataFrame:
    """Deterministic mock data generator using seeded RNG per symbol/timeframe."""
    rng = np.random.default_rng(zlib.crc32(f"{symbol}{tf}".encode()))
    base = BASE.get(symbol, 100)
    vol_scale = 0.015 if symbol.startswith("^") else 0.011
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
    """Validate OHLC consistency. Returns (cleaned_df, issues_list).
    
    Rows with invalid OHLC values (zero, negative, NaN, or infinite) are removed.
    OHLC relationships (high >= max(open,close), low <= min(open,close), high >= low)
    are validated and rows violating these are removed.
    """
    issues = []
    df = df.copy()
    
    # Track original row count
    original_rows = len(df)
    
    # First, ensure high >= max(open, close) and low <= min(open, close)
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
    
    # Identify rows with invalid OHLC values
    # Valid OHLC must be: finite, strictly positive
    invalid_mask = pd.Series(False, index=df.index)
    
    for col in ["open", "high", "low", "close"]:
        # Check for NaN values
        if df[col].isna().any():
            issues.append(f"NaN {col} values found")
            invalid_mask |= df[col].isna()
        
        # Check for infinite values
        if np.isinf(df[col]).any():
            if (df[col] == np.inf).any():
                issues.append(f"Positive infinite {col} values found")
            if (df[col] == -np.inf).any():
                issues.append(f"Negative infinite {col} values found")
            invalid_mask |= np.isinf(df[col])
        
        # Check for non-positive values (zero or negative)
        if (df[col] <= 0).any():
            issues.append(f"Non-positive {col} values found")
            invalid_mask |= (df[col] <= 0)
    
    # Remove rows with invalid OHLC values
    if invalid_mask.any():
        removed_count = invalid_mask.sum()
        issues.append(f"Removed {removed_count} row(s) with invalid OHLC values")
        df = df[~invalid_mask].copy()
    
    # Validate OHLC relationships on remaining data
    # High must be >= max(open, close)
    invalid_high = df["high"] < df[["open", "close"]].max(axis=1)
    if invalid_high.any():
        removed_count = invalid_high.sum()
        issues.append(f"Removed {removed_count} row(s) where high < max(open, close)")
        df = df[~invalid_high].copy()
    
    # Low must be <= min(open, close)
    invalid_low = df["low"] > df[["open", "close"]].min(axis=1)
    if invalid_low.any():
        removed_count = invalid_low.sum()
        issues.append(f"Removed {removed_count} row(s) where low > min(open, close)")
        df = df[~invalid_low].copy()
    
    # High must be >= low
    invalid_hl = df["high"] < df["low"]
    if invalid_hl.any():
        removed_count = invalid_hl.sum()
        issues.append(f"Removed {removed_count} row(s) where high < low")
        df = df[~invalid_hl].copy()
    
    # Volume non-negative - remove rows with negative volume
    if "volume" in df.columns and (df["volume"] < 0).any():
        neg_vol = df["volume"] < 0
        removed_count = neg_vol.sum()
        issues.append(f"Removed {removed_count} row(s) with negative volume")
        df = df[~neg_vol].copy()
    
    # Report total rows removed
    total_removed = original_rows - len(df)
    if total_removed > 0:
        issues.append(f"Total rows removed: {total_removed} out of {original_rows}")
    
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


def _resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Resample provider bars for timeframes Yahoo does not serve directly.

    ``4h`` is built from 60-minute bars and ``1w`` from daily bars.  We never
    invent rows: empty/incomplete buckets are dropped.
    """
    rule = RESAMPLE.get(tf)
    if not rule or df.empty:
        return df
    out = df.resample(rule).agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna(subset=["open", "high", "low", "close"])
    return out


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
        "name": SYMBOL_NAMES.get(symbol, inst.name_for(symbol)),
        "exchange": inst.exchange_for(symbol),
        "timeframe": tf,
        "source": source,
        "status": status,
        "last_bar": df.index[-1].isoformat() if len(df) > 0 else None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "label": "PAPER/SIMULATED" if status == "SIMULATED" else "MARKET DATA",
        "exchange_timezone": EXCHANGE_TIMEZONES.get(symbol, "Asia/Kolkata"),
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
        symbol: Trading symbol (e.g., '^NSEI', 'RELIANCE.NS')
        tf: Timeframe ('1m', '5m', '15m', '1h', '1d')
        n: Number of bars to return
        db: Optional SQLAlchemy session for caching
        use_cache: Whether to read from cache first
    
    Returns:
        (DataFrame with OHLCV + indicators, metadata dict)
    """
    # Resolve display names/aliases (nifty, reliance, ...) to canonical symbols.
    resolved = inst.resolve_symbol(symbol)
    raw_symbol = str(symbol)
    symbol = resolved or str(symbol).upper().replace("/", "-")
    catalogue_symbol = resolved is not None
    provider_ticker = inst.provider_symbol(symbol) if catalogue_symbol else symbol

    # Instruments the provider does not cover are reported honestly.
    if catalogue_symbol and not provider_ticker:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]), _meta(
            symbol, tf, pd.DataFrame(), "PROVIDER UNAVAILABLE", "UNAVAILABLE",
            issues=[inst.unavailable_reason(symbol) or "Provider coverage unavailable"],
        )
    
    use_live = os.getenv("USE_LIVE_DATA", "true") == "true"

    # Try cache first if db provided and use_cache enabled
    cached_bars = None
    if db is not None and use_cache:
        from app.models import MarketBar
        try:
            cached_bars = db.query(MarketBar).filter(
                MarketBar.symbol == symbol,
                MarketBar.timeframe == tf
            ).order_by(MarketBar.ts.desc()).limit(n).all()
            
            # Never serve cached simulated bars when live/provider data is
            # requested; that would blur the SIMULATED vs market-data boundary.
            if cached_bars and use_live and str(cached_bars[0].source).upper().startswith("MOCK"):
                cached_bars = None

            if cached_bars:
                cached_bars.reverse()  # chronological order
                df = pd.DataFrame([{
                    "open": b.open, "high": b.high, "low": b.low, 
                    "close": b.close, "volume": b.volume
                } for b in cached_bars], index=pd.to_datetime([b.ts for b in cached_bars]))
                
                # Check cache freshness
                is_fresh, cache_age = _is_cache_fresh(cached_bars, tf)
                cache_source = cached_bars[0].source
                is_mock_cache = str(cache_source).upper().startswith("MOCK")
                cache_status = "SIMULATED" if is_mock_cache else ("CACHED" if is_fresh else "STALE")
                
                if is_fresh:
                    # Fresh cache - return immediately
                    ttl_config = _get_ttl_config()
                    ttl_seconds = ttl_config.get(tf, 3600)
                    meta = _meta(
                        symbol, tf, df, cache_source, cache_status,
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
                    symbol, tf, df, cache_source, cache_status,
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
    
    if use_live:
        try:
            import yfinance as yf
            if tf == "1w":
                period = "10y"
            elif tf == "4h":
                period = "60d"
            elif tf == "1d":
                period = "5y"
            elif tf in ("5m", "15m", "30m", "1h"):
                period = "60d"
            else:
                period = "5d"
            df = yf.download(provider_ticker, period=period, interval=YF_INTERVAL[tf], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            df = df.rename(columns=str.lower)
            for col in ["open", "high", "low", "close", "volume"]:
                if col not in df.columns:
                    df[col] = np.nan
            df = df[["open", "high", "low", "close", "volume"]].dropna(subset=["open", "high", "low", "close"])
            df = _resample(df, tf)
            df = df.tail(n)

            if len(df) >= 2:
                df.index = pd.to_datetime(df.index)
                if getattr(df.index, "tz", None) is not None:
                    df.index = df.index.tz_localize(None)
                
                # Validate OHLC
                df, issues = _validate_ohlc(df)
                
                # Detect gaps/duplicates
                gaps, duplicates = _detect_gaps_duplicates(df, tf)
                
                # Write to cache (only real provider data)
                if db is not None:
                    _upsert_market_bars(db, df, symbol, tf, "YAHOO FINANCE")
                
                # Yahoo is a delayed source for NSE/BSE. Never claim LIVE.
                meta = _meta(symbol, tf, df, "YAHOO FINANCE", "DELAYED", issues, gaps, duplicates,
                             cached=False, cache_ttl_seconds=None, is_stale=False, cache_write_timestamp=None)
                return df, meta
        except Exception as e:
            live_error = str(e)
            pass
    
    # If we have stale cache and live failed, return stale data with warning
    if 'stale_cache_df' in locals() and stale_cache_df is not None:
        stale_cache_meta["data_quality"]["issues"] = stale_cache_meta["data_quality"].get("issues", []) + \
            [f"Live data unavailable ({live_error if live_error else 'unknown error'}); returning stale cached data"]
        return stale_cache_df, stale_cache_meta

    # Provider unavailable: do not fabricate prices for supported Indian symbols.
    if use_live and catalogue_symbol:
        reason = inst.unavailable_reason(symbol) or "Market-data provider unavailable or returned no data."
        if live_error:
            reason = f"{reason} ({live_error[:160]})"
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]), _meta(
            symbol, tf, pd.DataFrame(), "PROVIDER UNAVAILABLE", "UNAVAILABLE", issues=[reason],
        )

    # Explicit developer mode (USE_LIVE_DATA=false) or legacy/unknown symbols:
    # deterministic simulation, always labelled SIMULATED.
    df = _mock(symbol, tf, n)
    df, issues = _validate_ohlc(df)  # Mock should be valid, but validate anyway
    gaps, duplicates = _detect_gaps_duplicates(df, tf)
    
    # Write mock to cache if db provided
    if db is not None:
        _upsert_market_bars(db, df, symbol, tf, "MOCK GENERATOR")
    
    meta = _meta(symbol, tf, df, "MOCK GENERATOR", "SIMULATED", issues, gaps, duplicates, cached=False, cache_ttl_seconds=None, is_stale=False, cache_write_timestamp=None)
    return df, meta

# ---------------------------------------------------------------------------
# Quote / movers / capability helpers (India-only)
# ---------------------------------------------------------------------------
_QUOTE_CACHE: Dict[str, Dict[str, Any]] = {}
_MOVERS_CACHE: Dict[str, Any] = {"ts": 0.0, "payload": None}
_CACHE_LOCK = threading.Lock()


def _cached(key: str, ttl: int = 30) -> Optional[Any]:
    now = datetime.utcnow().timestamp()
    with _CACHE_LOCK:
        hit = _QUOTE_CACHE.get(key)
    if hit and now - hit["ts"] < ttl:
        return hit["value"]
    return None


def _store(key: str, value: Any) -> Any:
    with _CACHE_LOCK:
        _QUOTE_CACHE[key] = {"ts": datetime.utcnow().timestamp(), "value": value}
    return value


def quote(symbol: str, db: Optional[Any] = None) -> Dict[str, Any]:
    """Return a quote overview for an Indian instrument.

    Uses the last two daily bars so absolute/percentage change, OHLC, previous
    close and volume all come from the same provider response.
    """
    symbol = inst.resolve_symbol(symbol) or symbol
    cached = _cached(f"quote:{symbol}", 20)
    if cached is not None:
        return cached
    df, meta = get_bars(symbol, "1d", 5, db=db, use_cache=False)
    return _store(f"quote:{symbol}", inst.quote_summary(symbol, df, meta))


def quotes_batch(symbols: List[str], db: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
    """Quote several Indian instruments with a single delayed provider request.

    Falls back to an explicit ``UNAVAILABLE`` quote per instrument when the
    provider is unreachable. Cached quotes are reused for 20 seconds so
    dashboard polling stays light.
    """
    canonical: List[str] = []
    for symbol in symbols:
        resolved = inst.resolve_symbol(symbol) or symbol
        if resolved not in canonical:
            canonical.append(resolved)

    out: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []
    for symbol in canonical:
        cached = _cached(f"quote:{symbol}", 20)
        if cached is not None:
            out[symbol] = cached
        else:
            missing.append(symbol)

    covered = [s for s in missing if inst.provider_symbol(s)]
    for symbol in missing:
        if not inst.provider_symbol(symbol):
            df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            meta = _meta(
                symbol, "1d", df, "PROVIDER UNAVAILABLE", "UNAVAILABLE",
                issues=[inst.unavailable_reason(symbol) or "Provider coverage unavailable"],
            )
            out[symbol] = _store(f"quote:{symbol}", inst.quote_summary(symbol, df, meta))

    if not covered:
        return out

    try:
        data = _batch_download(covered)
        for symbol in covered:
            ticker = inst.provider_symbol(symbol)
            series = {
                "open": _series_from_batch(data, ticker, "Open"),
                "high": _series_from_batch(data, ticker, "High"),
                "low": _series_from_batch(data, ticker, "Low"),
                "close": _series_from_batch(data, ticker, "Close"),
                "volume": _series_from_batch(data, ticker, "Volume"),
            }
            close = series["close"]
            if close is None or len(close) == 0:
                df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
                meta = _meta(
                    symbol, "1d", df, "YAHOO FINANCE", "UNAVAILABLE",
                    issues=["The configured provider returned no data for this instrument."],
                )
            else:
                df = pd.DataFrame({k: v for k, v in series.items() if v is not None})
                df = df.dropna(subset=["close"]).sort_index()
                if df.empty:
                    meta = _meta(
                        symbol, "1d", df, "YAHOO FINANCE", "UNAVAILABLE",
                        issues=["The configured provider returned no usable close prices."],
                    )
                else:
                    meta = _meta(symbol, "1d", df, "YAHOO FINANCE", "DELAYED")
            out[symbol] = _store(f"quote:{symbol}", inst.quote_summary(symbol, df, meta))
    except Exception as e:
        reason = f"Provider request failed ({str(e)[:160]})."
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        for symbol in covered:
            meta = _meta(symbol, "1d", df, "YAHOO FINANCE", "UNAVAILABLE", issues=[reason])
            out[symbol] = _store(f"quote:{symbol}", inst.quote_summary(symbol, df, meta))
    return out


def _batch_download(symbols: List[str], period: str = "5d", interval: str = "1d"):
    """Download several provider tickers in one Yahoo request."""
    import yfinance as yf
    tickers = [inst.provider_symbol(s) or s for s in symbols]
    data = yf.download(
        tickers=" ".join(tickers), period=period, interval=interval,
        group_by="ticker", auto_adjust=True, progress=False, threads=True,
    )
    return data


def _series_from_batch(data, ticker: str, col: str):
    if data is None or getattr(data, "empty", True):
        return None
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if ticker not in data.columns.get_level_values(0):
                return None
            s = data[ticker][col]
        else:
            s = data[col]
        s = s.dropna()
        return s if len(s) else None
    except Exception:
        return None


def movers(db: Optional[Any] = None, limit: int = 5) -> Dict[str, Any]:
    """Top gainers / losers / volume from real provider data.

    The whole movers universe is fetched in one batched request and cached for
    60 seconds.  If the provider is unavailable we return ``available: false``
    instead of inventing movers.
    """
    now = datetime.utcnow().timestamp()
    with _CACHE_LOCK:
        cached = _MOVERS_CACHE.get("payload")
        if cached is not None and now - _MOVERS_CACHE.get("ts", 0) < 60:
            return cached

    symbols = [s for s in inst.MOVERS_UNIVERSE if inst.provider_symbol(s)]
    try:
        data = _batch_download(symbols)
        rows = []
        for sym in symbols:
            close = _series_from_batch(data, inst.provider_symbol(sym), "Close")
            volume = _series_from_batch(data, inst.provider_symbol(sym), "Volume")
            if close is None or len(close) < 2:
                continue
            last, prev = float(close.iloc[-1]), float(close.iloc[-2])
            if not prev:
                continue
            rows.append({
                "symbol": sym,
                "name": inst.name_for(sym),
                "exchange": inst.exchange_for(sym),
                "price": round(last, 2),
                "change": round(last - prev, 2),
                "change_pct": round((last / prev - 1) * 100, 2),
                "volume": float(volume.iloc[-1]) if volume is not None and len(volume) else None,
                "status": "DELAYED",
                "provider": "YAHOO FINANCE",
            })
        if not rows:
            raise RuntimeError("Provider returned no usable movers data")
        payload = {
            "available": True,
            "provider": "YAHOO FINANCE",
            "status": "DELAYED",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "note": "Yahoo Finance NSE data is delayed. Movers are computed from the latest provider bars.",
            "gainers": sorted([r for r in rows if r["change_pct"] > 0], key=lambda r: r["change_pct"], reverse=True)[:limit],
            "losers": sorted([r for r in rows if r["change_pct"] < 0], key=lambda r: r["change_pct"])[:limit],
            "volume": sorted([r for r in rows if r["volume"]], key=lambda r: r["volume"], reverse=True)[:limit],
        }
        with _CACHE_LOCK:
            _MOVERS_CACHE["ts"] = now
            _MOVERS_CACHE["payload"] = payload
        return payload
    except Exception as e:
        return {
            "available": False,
            "provider": "YAHOO FINANCE",
            "status": "UNAVAILABLE",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "reason": f"Market movers are unavailable from the configured provider ({str(e)[:160]}).",
            "gainers": [], "losers": [], "volume": [],
        }


def indices(db: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Snapshot of the key Indian indices (real provider data only)."""
    catalogue = [item for item in inst.INSTRUMENTS if item["kind"] == "index"]
    quotes = quotes_batch([item["symbol"] for item in catalogue], db=db)
    out = []
    for item in catalogue:
        q = quotes.get(item["symbol"])
        if not q:
            out.append({
                "symbol": item["symbol"], "name": item["name"], "exchange": item["exchange"],
                "price": None, "change": None, "change_pct": None, "volume": None,
                "status": "UNAVAILABLE", "provider": None,
                "reason": inst.unavailable_reason(item["symbol"]),
            })
            continue
        out.append({k: q.get(k) for k in (
            "symbol", "name", "exchange", "price", "change", "change_pct",
            "volume", "status", "provider", "fetched_at", "last_bar", "reason",
        )})
    return out


def capabilities() -> Dict[str, Any]:
    """Honest description of what the configured provider can and cannot do."""
    return {
        "provider": "Yahoo Finance (yfinance)",
        "markets": ["NSE", "BSE"],
        "instrument_scope": "Indian indices and NSE/BSE listed stocks",
        "realtime": False,
        "delayed": True,
        "trade_prints": False,
        "market_depth": False,
        "websocket_provider_stream": False,
        "notes": [
            "Yahoo Finance does not provide licensed real-time NSE/BSE data.",
            "Quotes are delayed and labelled DELAYED — never LIVE.",
            "Exchange trade prints and order-book depth are not available from this provider.",
            "QuantNiti uses a server-side WebSocket snapshot stream (polling) for convenience; it is not an exchange feed.",
        ],
    }


def trade_tape(symbol: str) -> Dict[str, Any]:
    """The configured provider has no exchange trade-print feed.

    Returning an explicit unavailable payload is intentional — we never
    fabricate market transactions.
    """
    return {
        "available": False,
        "symbol": inst.resolve_symbol(symbol) or symbol,
        "provider": "YAHOO FINANCE",
        "reason": "The configured provider does not supply exchange trade prints for NSE/BSE.",
        "items": [],
    }
