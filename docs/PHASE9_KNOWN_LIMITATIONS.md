# Phase 9 Known Limitations

## Overview
This document catalogs known limitations, bugs, and areas for improvement identified during Phase 9 integration testing. These items do not block the current release but should be addressed in future phases.

---

## Critical Limitations (Should Fix Soon)

### 1. Yahoo Finance API Failures for Crypto Symbols
**Impact**: BTC-USD, ETH-USD fail with JSON decode errors; ^NSEI works correctly.
**Root Cause**: Yahoo Finance API changes or rate limiting for crypto endpoints.
**Workaround**: Deterministic mock generator provides consistent fallback data.
**Fix**: Implement more robust error handling, consider alternative data providers (Alpha Vantage, Polygon, CoinGecko), or add caching layer with longer TTL for crypto.

### 2. Scheduled Research - No Scheduler Service
**Impact**: Configuration endpoints exist (`GET/POST /api/strategies/research/schedule`) but no automatic execution.
**Root Cause**: No APScheduler, Celery Beat, or cron service deployed.
**Workaround**: UI clearly labeled as "configuration-only"; manual triggering via Studio/Research pages works.
**Fix**: Deploy APScheduler or Celery Beat with Redis/RabbitMQ for production.

### 3. Conversation Search Performance
**Impact**: Uses `messages::text ILIKE '%query%'` which does full table scan on JSONB.
**Root Cause**: No full-text search index on conversation messages.
**Fix**: Add pg_trgm extension with GIN index on `messages::text`, or implement PostgreSQL full-text search with `tsvector`/`tsquery`.

### 4. Strategy Research Snapshot Bug
**Impact**: When creating research with `strategy_id`, the `strategy_spec_snapshot` and `backtest_metrics_snapshot` fields are not populated despite the router logic attempting to fetch them.
**Root Cause**: Logic in `research.py` create_run fetches strategy but doesn't properly assign snapshots before creating ResearchRun.
**Fix**: Ensure snapshots are assigned before `db.add(run)` in research router.

---

## Significant Limitations (Plan for Next Phase)

### 5. Single User / No Authentication
**Impact**: All operations use hardcoded `user_id=1`. No multi-tenancy, no auth.
**Fix**: Implement JWT/OAuth authentication, user registration, API keys.

### 6. Journal List Endpoint Type Bug
**Impact**: `list_entries` function has `page_size` treated as Query object when called directly (not via FastAPI), causing `TypeError: unsupported operand type(s) for -: 'Query' and 'int'`.
**Root Cause**: FastAPI `Query` dependency not resolved in direct function calls.
**Workaround**: Works correctly when called via HTTP API; only affects direct Python calls.
**Fix**: Refactor to accept plain integers, or separate business logic from FastAPI dependencies.

### 7. PaperAccount Missing user_id FK
**Impact**: PaperAccount model lacks `user_id` column, preventing multi-user isolation.
**Fix**: Add `user_id` column with FK to users table, add migration.

### 8. Bundle Size Exceeds Recommendation
**Impact**: 788 kB JS (gzipped 222 kB) > 500 kB recommended limit.
**Fix**: Implement code-splitting with dynamic imports for heavy pages (Builder, Studio, Research), use `manualChunks` in Vite config.

### 9. Research Comparison Creates Persistent Records
**Impact**: Each comparison creates a new `ResearchRun` with label="COMPARISON", accumulating over time.
**Fix**: Add cleanup job, or store comparisons in separate table with TTL.

### 10. PDF Export Basic Implementation
**Impact**: ReportLab generates functional but unstyled PDFs; no charts, limited formatting.
**Fix**: Add equity curve charts, better table styling, cover page options, font embedding.

---

## Minor Limitations (Nice to Have)

### 11. Strategy Diff - Shallow Comparison
**Impact**: Only compares top-level spec fields; nested changes in indicators/rules/risk not deeply diffed.
**Fix**: Use deep-diff library (e.g., `deepdiff`) for nested object comparison.

### 12. No Trade Chart in Backtest Results
**Impact**: Equity curve returned as data but no visualization in API; frontend would need to chart it.
**Fix**: Add optional chart generation in backtest endpoint, or document expected frontend charting.

### 13. No Position Sizing Variations
**Impact**: Only fixed fractional position sizing (`max_position_pct`); no Kelly, volatility-targeting, or ATR-based sizing.
**Fix**: Add sizing strategies to RiskLimits schema and backtest/paper engines.

### 14. Limited Timeframe Support for Live Data
**Impact**: Yahoo Finance `yfinance` has restrictions on intraday data (1m only last 7 days, 5m/15m/1h only last 60 days).
**Fix**: Document limitations, implement data warehouse for historical intraday data.

### 15. No Exchange Calendar for Gap Detection
**Impact**: Daily gap detection skipped because no trading calendar; weekends/holidays flagged as gaps.
**Fix**: Integrate exchange calendar (e.g., `pandas_market_calendars`) for proper gap detection.

### 16. Deterministic Agents Not LLM
**Impact**: Research "agents" are rule-based templates, not LLM-powered. Labeled "AI-GENERATED INTERPRETATION · PAPER/SIMULATED".
**Fix**: Design plugin architecture for LLM integration (OpenAI, Anthropic, local models) with same facts interface.

### 17. No WebSocket/Real-time Updates
**Impact**: Paper trading, backtest progress, market data all require polling.
**Fix**: Add WebSocket server (Socket.io or native WebSockets) for real-time push.

### 18. No Audit Logging
**Impact**: No trail of who did what when (critical for financial apps).
**Fix**: Add audit log table with user_id, action, entity_type, entity_id, timestamp, diff.

### 19. No Rate Limiting on API
**Impact**: Public endpoints vulnerable to abuse.
**Fix**: Add rate limiting middleware (slowapi or similar).

### 20. No Database Connection Pooling Tuning
**Impact**: Default SQLAlchemy pool settings may not be optimal for production load.
**Fix**: Tune `pool_size`, `max_overflow`, `pool_timeout` based on load testing.

---

## Deferred to Future Phases

| Item | Phase | Reason |
|------|-------|--------|
| Multi-user auth | Phase 10 | Core requirement for production |
| Scheduler service | Phase 10 | Needed for scheduled research |
| Full-text search | Phase 10 | Performance at scale |
| WebSocket real-time | Phase 11 | UX improvement |
| LLM integration | Phase 11 | Core value proposition |
| Audit logging | Phase 10 | Compliance requirement |
| Rate limiting | Phase 10 | Security requirement |
| Code splitting | Phase 10 | Performance at scale |
| Exchange calendar | Phase 11 | Data quality improvement |
| Position sizing strategies | Phase 11 | Advanced features |
| Trade charting | Phase 11 | UX improvement |
| Audit logging | Phase 10 | Compliance |

---

## Summary

**Total Known Limitations**: 20  
**Critical**: 4  
**Significant**: 6  
**Minor**: 10  

**None are release-blocking for Phase 9**. All critical functionality works with explicit simulation labeling. The system is ready for Phase 10 hardening.