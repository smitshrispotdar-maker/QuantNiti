# Phase 8 Audit: Research Visualization, Version History & Export

## Current Implementation Status

### Backend (Phase 7 Complete - Commit a136ff6)

#### Existing Models
- **JournalEntry** - Enhanced with decision_type, status, hypothesis/rationale/evidence/risks/outcomes, FKs to conversation/backtest/research/deployment
- **ResearchRun** - Provenance tracking (data_source, data_quality, is_simulated), strategy/backtest snapshots
- **Strategy** - Versioning, spec snapshots
- **BacktestRun** - Full results with metrics, equity_curve, trades, validation, strategy_spec snapshot
- **PaperDeployment** - Full deployment lifecycle with strategy_spec snapshot
- **Conversation** - Messages, draft_spec with backtest_refs, deployment_refs, research_refs

#### Existing Services
- **nlp.py** - Rule-based parser with action detection (backtest, deploy, explain)
- **backtest.py** - Vectorized backtest engine with costs/slippage
- **paper.py** - Paper trading execution matching backtest model
- **market.py** - Market data with caching/staleness
- **research.py** - Deterministic multi-agent research (facts + templated interpretations)
- **validation.py** - Validation gate
- **lineage.py** - Lineage builder with 8 event types

#### Existing API Endpoints
- **Journal**: GET/POST /api/journal, GET/PATCH/DELETE /api/journal/{jid}, POST /api/journal/{jid}/review
- **Research**: GET/POST /api/research, GET /api/research/{rid}, POST /api/research/from-chat
- **Lineage**: GET /api/lineage, GET /api/lineage/entity/{type}/{id}
- **Strategies**: CRUD + chat with action detection (backtest, deploy, explain)

#### Tests
- Backend: 294 tests passing (294 passed, 1 skipped)
- Frontend: 16 tests passing (16 passed)
- Build: Success

### Frontend (Phase 7 Complete)

#### Existing Pages
- **Journal.jsx** - Full CRUD with filters, pagination, decision types, status badges, inline outcome review
- **Research.jsx** - Run list with filters, create form, detail view with facts/interpretations/provenance
- **Studio.jsx** - Chat with conversation sidebar, action buttons (Run Backtest, Deploy to Paper, Explain, Save)
- **Backtest.jsx** - Configuration, results display
- **Paper.jsx** - Deployment management, positions, orders, trades
- **Studio.jsx** - Conversation sidebar with load/delete/rename

#### API Helpers
- `api.jsx` - Centralized API client with error handling

---

## Missing Capabilities for Phase 8

### 1. Strategy Lineage Visualization (Frontend)
- **Missing**: `StrategyLineage.jsx` component
- **Missing**: Integration into Strategy details, Journal, Research, Studio pages
- **API exists**: `/api/lineage` and `/api/lineage/entity/{type}/{id}`

### 2. Strategy Version Diff
- **Missing**: Comparison interface for two strategy versions
- **Missing**: Diff UI for indicators, entry/exit rules, risk settings
- **Data available**: Strategy versions with spec snapshots in Strategy table

### 3. Research Run Comparison
- **Missing**: Comparison view for two+ research runs
- **Data available**: ResearchRun model with facts, interpretations, provenance

### 4. Export Functionality
- **Missing**: Export for Journal, Research Runs, Strategy Lineage
- **Formats needed**: JSON, Markdown, PDF
- **Missing**: Export authorization, provenance metadata

### 5. Conversation Search
- **Missing**: Search by title, message content, strategy names, date
- **Data available**: Conversation messages, draft_spec

### 6. Scheduled Research Audit
- **Missing**: Background task infrastructure assessment
- **Missing**: Periodic research design document

---

## Database & Migration Status
- Current migration: `0003_phase7_journal_research.py` (applied)
- Models: JournalEntry (extended), ResearchRun (new)
- No breaking changes to existing models
- Need new migration for any new tables/columns

---

## Test Baseline
- Backend: 294 passed, 1 skipped
- Frontend: 16 passed
- Build: Success

---

## Proposed Implementation Plan

### Stage 1: Lineage Visualization Component
1. Create `frontend/src/components/lineage/StrategyLineage.jsx`
2. Integrate into Studio, Journal, Research pages
3. Add navigation links from lineage events to entity pages

### Stage 2: Strategy Version Diff
1. Create diff utility for StrategySpec comparison
2. Create `StrategyVersionDiff` component
3. Add version selector to Strategy details

### Stage 3: Research Comparison
1. Create comparison view for 2+ ResearchRun objects
2. Highlight factual vs interpretive differences
3. Show provenance differences

### Stage 4: Export
1. Create export utilities (JSON, Markdown, PDF)
2. Add export buttons to Journal, Research, Lineage pages
3. Implement PDF generation (use jsPDF or similar)

### Stage 6: Conversation Search
1. Add search endpoint to strategies router
2. Add search UI to Studio sidebar
3. Support title, message content, strategy name search

### Stage 7: Scheduled Research Audit
- Document current scheduler state
- Design future scheduler architecture
- Document safety requirements

---

## Remaining Limitations (from Phase 7)
1. Single User: Hardcoded user_id=1
2. No LLM: Rule-based parser only
3. No Conversation Search: Not yet implemented
4. No Export: Not yet implemented
5. No Lineage UI: Not yet implemented
5. No Streaming: All responses returned at once
6. No Model Selection: No UI for local/remote models