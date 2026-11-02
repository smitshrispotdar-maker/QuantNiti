# Phase 7 Audit - Decision Journal, Multi-Agent Research Integration & Strategy Lineage

## Current State Summary (Phase 6 Complete - Commit 56b83b9)

### Existing Models
- **JournalEntry** (basic): strategy_id, strategy_version, recommendation, evidence (JSONB), outcome_review, created_at
- **Conversation**: messages (JSONB), draft_spec (JSONB) - stores backtest_refs, deployment_refs
- **Strategy**: versioning, spec (JSONB)
- **BacktestRun**: strategy_spec snapshot, metrics, equity_curve, trades, validation
- **PaperDeployment**: strategy_spec snapshot, execution config, status, positions, orders, trades
- **PaperPosition**, **PaperOrder**, **PaperTrade** - execution tracking

### Existing Services
- **nlp.py**: Rule-based parser with action detection (backtest, deploy, explain)
- **backtest.py**: Vectorized backtest engine with costs/slippage
- **paper.py**: Paper trading execution matching backtest model
- **market.py**: Market data with caching/staleness
- **research.py**: Deterministic multi-agent research (market_analyst, risk_analyst, etc.)
- **validation.py**: Validation gate
- **indicators.py**: Technical indicators

### Existing Routers
- **strategies.py**: Strategy CRUD, conversation management, chat with action detection
- **journal.py**: Basic journal CRUD (list, add, review)
- **paper.py**: Paper trading endpoints with deployment lifecycle
- **backtests.py**: Backtest endpoints
- **market.py**: Market data endpoints

### Frontend Pages
- **Studio.jsx**: Chat studio with conversation sidebar, action buttons (backtest, deploy, explain, save)
- **Backtest.jsx**: Configuration, results display
- **Paper.jsx**: Deployment management, positions, orders, trades
- **Journal.jsx**: Basic entry list, create, review
- **Dashboard.jsx**, **Builder.jsx**

### Current Test Status
- Backend: 280 tests passing
- Frontend: 16 tests passing
- Build: Success

---

## Missing Capabilities for Phase 7

### 1. Decision Journal Enhancement
**Current JournalEntry model lacks:**
- decision_type (strategy_hypothesis, research_finding, backtest_review, risk_review, strategy_approval, strategy_rejection, strategy_modification, paper_trading_review, general_note)
- status (draft, under_review, approved, rejected, superseded, completed)
- title
- hypothesis_rationale
- evidence_summary
- risks_assumptions
- decision_next_steps
- expected_outcome
- actual_outcome
- conversation_id, backtest_run_id, research_run_id, deployment_id links
- updated_at timestamp

**Current journal router lacks:**
- Pagination
- Filtering by strategy, status, decision_type, related IDs
- Update endpoint for editable fields
- Proper ownership validation (hardcoded user_id=1)

### 2. Multi-Agent Research Integration
**Current research.py exists but:**
- Not integrated with backtest/deployment references
- No persistence of research runs
- No research run tracking with provenance
- Not linked to conversations/backtests/deployments
- No API endpoints for triggering research from chat
- No research results display in frontend

### 3. Strategy Lineage
**Current gaps:**
- No explicit lineage tracking between conversations → strategies → backtests → deployments → journal entries
- Conversation stores backtest_refs and deployment_refs but no research_refs
- No lineage API or frontend view
- Journal entries don't link to backtest runs or research runs
- No lineage UI/timeline

### 4. Frontend Integration
- **Journal.jsx**: Basic UI only - missing decision_type, status, hypothesis, risks, etc.
- No research results display in Studio/Journal
- No lineage/timeline view
- No research trigger from Studio

---

## Database & Migration Risks
- **Current migrations**: 0001_initial.py, 0002_watchlist_items.py
- Need new migration for enhanced JournalEntry model
- Need new models: ResearchRun, DecisionJournal (or extend JournalEntry)
- No breaking changes to existing models if additive
- Must verify database isolation before running migrations

---

## Proposed Implementation Plan

### Stage 0: Audit Complete ✓

### Stage 1: Decision Journal Enhancement
1. Extend JournalEntry model with all required fields
2. Create Alembic migration
3. Extend JournalIn/JournalOut schemas
4. Enhance journal router with pagination, filtering, update
5. Add tests for journal CRUD, filtering, validation

### Stage 2: Research Integration
1. Create ResearchRun model for persistence
2. Extend research.py to accept context (strategy, backtest, deployment)
3. Add research router with CRUD + trigger from chat
3. Link research runs to conversations/backtests/deployments
4. Add tests for research persistence and retrieval

### Stage 3: Strategy Lineage
1. Add foreign keys/relationships for lineage tracking
2. Create lineage service to build timeline
4. Add lineage router
5. Create lineage frontend component

### Stage 4: Frontend Integration
1. Enhanced Journal page with full form
2. Research results display in Studio/Journal
3. Lineage timeline component
4. Research trigger from Studio chat

### Stage 5: Testing
- Backend tests for all new endpoints
- Frontend tests for new components
- Integration tests for cross-feature workflows

### Stage 6: Documentation
- PHASE7_AUDIT.md (this file)
- DECISION_JOURNAL_IMPLEMENTATION.md
- RESEARCH_INTEGRATION.md
- STRATEGY_LINEAGE.md

---

## Test Baseline
- Backend: 280 tests passing (280 passed, 1 skipped)
- Frontend: 16 tests passing
- Build: Success