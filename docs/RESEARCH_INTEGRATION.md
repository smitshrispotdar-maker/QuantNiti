# Research Integration Implementation - Phase 7 Stage 2

## Summary

Integrated deterministic multi-agent research with persistence, conversation linking, and evidence provenance tracking.

## Files Modified/Created

### Backend Models
- **`backend/app/models.py`**: Added `ResearchRun` model (see DECISION_JOURNAL_IMPLEMENTATION.md)

### Backend Services
- **`backend/app/services/research.py`**: Existing deterministic research service reused
  - Computes facts from market data (RSI, EMA, MACD, volatility, drawdown, momentum)
  - Generates templated agent interpretations (market_analyst, bull/bear signals, risk_analyst, strategy_manager)
  - Returns structured facts + interpretations with "AI-GENERATED INTERPRETATION · PAPER/SIMULATED" label

### Routers
- **`backend/app/routers/research.py`** (NEW): Complete research run lifecycle
  - `POST /api/research` - Create run with automatic market data fetch and analysis
  - `GET /api/research` - Paginated list with filtering (strategy_id, conversation_id, backtest_run_id, deployment_id)
  - `GET /api/research/{rid}` - Get run details
  - `POST /api/research/from-chat` - Trigger from conversation using draft strategy

### Research Execution Flow
1. User triggers research via chat ("run research", "analyze") or Research page
2. System resolves strategy spec (from body, conversation draft, or linked backtest/deployment)
3. Fetches market data via existing `market.get_bars()` with quality metadata
4. Runs deterministic `research.run(df)` on market data
5. Stores complete result with provenance (data_source, data_quality, is_simulated flag)
4. Links to conversation/backtest/deployment if provided
5. Adds reference to conversation draft_spec for traceability

### Provenance Tracking
Every research run captures:
- `data_source`: "MOCK GENERATOR", "YAHOO FINANCE", "CACHED", "STALE"
- `data_quality`: issues, gaps, duplicates, bar_count, cached, cache_age_seconds, is_stale
- `is_simulated`: Boolean flag (true when using mock data)
- `label`: "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"
- Full `strategy_spec_snapshot` and `backtest_metrics_snapshot` for reproducibility

### Evidence Provenance
- Facts are computed from actual market data (never fabricated)
- Interpretations are templated from facts (deterministic)
- Simulated data clearly labeled
- Missing data results in degraded analysis with warnings
- No external API calls or paid data sources required

---

## Frontend Integration

### Research Page (`frontend/src/pages/Research.jsx`)
- Run list with filters (strategy, conversation, backtest, deployment)
- Create new research form with all link options
- Detailed run view with:
  - Facts grid (RSI, EMA, MACD, volatility, drawdown, momentum)
  - Interpretations by agent (market_analyst, bull/bear signals, risk_analyst, strategy_manager)
  - Provenance panel (data source, simulated flag, timestamps)
  - Full strategy spec and data quality JSON viewers
- Pagination and filtering

### Studio Integration
- "Research" action button in Studio (triggered by "run research", "analyze" in chat)
- Research refs stored in conversation `draft_spec.research_refs`
- Research results appear in chat history

---

## Test Results
- Backend: 294 tests passing (including 14 new journal/research tests)
- Frontend: 16 tests passing
- Production build: Success

---

## Evidence & Provenance Principles

1. **No Fabrication**: Facts computed only from actual market data returned by `market.get_bars()`
2. **No Hallucination**: Interpretations are deterministic templates applied to facts
3. **Provenance Transparency**: Every run includes data_source, data_quality, is_simulated
4. **Reproducibility**: Full strategy spec and market data snapshots stored
5. **Clear Labeling**: "AI-GENERATED INTERPRETATION · PAPER/SIMULATED" on all outputs
6. **No Paid APIs**: Uses free Yahoo Finance with deterministic mock fallback
6. **Graceful Degradation**: Works with mock data when live data unavailable, clearly labeled

---

## Integration Points

### With Chat (Studio)
- `nlp.detect_action()` detects "explain", "analyze", "research" keywords
- Chat endpoint calls research service and stores reference in conversation

### With Backtest
- Research can be linked to backtest_run_id
- Backtest metrics snapshot stored for context

### With Paper Trading
- Research can be linked to deployment_id
- Deployment config snapshot stored

### With Decision Journal
- Journal entries can link to research_run_id
- Research findings can be saved as journal entries

---

## Limitations & Future Work

### Current Limitations
- Research runs are read-only after creation (no update endpoint)
- No comparison view between multiple research runs
- No scheduled/automated research runs
- No export to PDF/Markdown

### Planned Enhancements
- Research run comparison view
- Scheduled research for active deployments
- Export to Markdown/PDF
- LLM-enhanced interpretations (optional, with local model support)
- Research result sharing/linking