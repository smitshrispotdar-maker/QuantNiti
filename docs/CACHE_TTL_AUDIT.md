# QuantNiti — Cache TTL Audit Report

**Date:** 2024  
**Auditor:** Phase 3D Implementation

---

## 1. Current Cache Implementation Summary

### 1.1 Market Data Service (`backend/app/services/market.py`)

The `get_bars()` function is the primary entry point for market data retrieval. It implements a multi-tier fallback strategy:

1. **Cache First** (if `db` provided and `use_cache=True`):
   - Queries `MarketBar` table for cached bars
   - Returns cached data with `status: "CACHED"` and `cache_age_seconds` computed from the most recent bar's timestamp
   - **Cache age calculation**: `datetime.utcnow() - cached_bars[-1].ts` (uses the newest bar's timestamp)

2. **Live Data** (if `USE_LIVE_DATA=true`):
   - Fetches from Yahoo Finance via `yfinance`
   - Validates OHLC, detects gaps/duplicates
   - Writes to cache via `_upsert_market_bars()`
   - Returns with `status: "DELAYED"`, `cached: false`

3. **Mock Fallback** (always available):
   - Deterministic mock data generator
   - Returns `status: "SIMULATED"`, `cached: false`

### 1.2 MarketBar Model (Database Cache)

```python
class MarketBar(Base):
    __tablename__ = "market_bars"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "ts"),)
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    ts = Column(DateTime)  # Bar timestamp (when the bar occurred)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    source = Column(String)  # e.g., "YAHOO FINANCE", "MOCK GENERATOR"
```

**Key observations:**
- The `ts` column stores the **bar timestamp** (when the market data bar occurred), not the cache write timestamp
- No separate `cached_at` or `retrieved_at` column exists
- Cache age is currently computed from the newest bar's timestamp (`cached_bars[-1].ts`), which is the **bar timestamp**, not the cache write time

### 1.3 Current Cache Behavior

**Cache Read Path (`get_bars` with `db` and `use_cache=True`):**
1. Queries `MarketBar` table for symbol/timeframe
2. Returns most recent `n` bars in chronological order
3. Computes `cache_age_seconds` as `datetime.utcnow() - cached_bars[-1].ts`
4. Returns `status: "CACHED"`, `cached: true`, `cache_age_seconds`

**Cache Write Path (`_upsert_market_bars`):**
- Upserts bars with their original timestamps
- No separate `cached_at` timestamp recorded
- Uses bar's original timestamp (`ts`) as the primary key component

### 1.4 Current TTL Configuration

**No explicit TTL configuration exists.** The cache is effectively infinite - cached data is always returned if available, with no freshness check.

### 1.5 Current Gap Detection

In `_detect_gaps_duplicates()`:
- For intraday timeframes (1m, 5m, 15m, 1h): Uses expected frequency to detect gaps
- For daily (1d): **Skipped** (gap detection is disabled for 1d timeframe - see Phase 3B changes)

### 1.6 Frontend Data Quality Panel

The `DataQualityPanel` component in `Dashboard.jsx` displays:
- Cache status (HIT/MISS)
- Cache age (formatted from `cache_age_seconds`)
- Bar count, timeframe, last bar timestamp, fetched timestamp
- Quality warnings (OHLC issues, gaps, duplicates)
- Cache status badge (HIT/MISS)

### 1.7 Response Schema (Pydantic Models)

Key models in `schemas.py`:
- `DataQuality`: issues, gaps, duplicates, bar_count, cached, cache_age_seconds
- `MarketMeta`: includes `status` (LIVE/DELAYED/CACHED/SIMULATED), `source`, `fetched_at`, `data_quality` (DataQuality)
- `MarketBarsResponse`: meta + bars

---

## 2. Current Issues Identified

### 2.1 No Cache TTL Configuration
- No TTL configuration exists
- Cache is effectively infinite
- No mechanism to force refresh of stale data

### 2.2 Cache Age Calculation Issue
**Critical Issue**: `cache_age_seconds` is calculated from the **bar timestamp** (`cached_bars[-1].ts`), not the cache write time. This means:
- If cached data is from yesterday but was cached today, it shows as "24 hours old" instead of "fresh"
- The bar timestamp represents when the market data occurred, not when it was cached

### 2.3 No Cache Expiration Logic
- Cached data is always returned if available, regardless of age
- No mechanism to trigger provider refresh when cache is stale

### 2.4 No Stale Data Handling
- When provider fails, cached data is returned but marked as "CACHED" without staleness indication
- No distinction between fresh cache and stale cache

### 2.5 Missing Cache Metadata
- No `cache_ttl_seconds` in response
- No `is_stale` flag
- No `cache_write_timestamp` stored

---

## 3. Required Changes Summary

### 3.1 Configuration (No DB Migration)
- Add TTL configuration via environment variables
- Centralized TTL configuration class

### 3.2 Service Layer Changes
- Store cache write timestamp (add `cached_at` to MarketBar or track separately)
- Implement TTL check in `get_bars()`
- Return stale data with explicit status when provider fails
- Add TTL to response metadata

### 3.3 Schema Updates
- Extend `DataQuality` with `cache_ttl_seconds`, `is_stale`, `cache_write_timestamp`
- Update `MarketMeta` with `cache_ttl_seconds`, `is_stale`

### 3.4 Frontend Updates
- Display cache TTL in DataQualityPanel
- Show stale warning when applicable
- Distinguish cache age from bar age

### 3.5 Tests
- Unit tests for TTL logic
- Integration tests for cache refresh behavior
- Frontend tests for stale data display