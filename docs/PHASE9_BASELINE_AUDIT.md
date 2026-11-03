# Phase 9 Baseline Audit

## Audit Date
2026-11-03

## Git Status

### Branch
`main`

### Working Tree
Clean (only pycache files and built frontend artifacts)

### Recent Commits
```
646ea84 feat: Phase 8.1 Complete - Strategy Version Diff, Research Comparison, Export (JSON/MD/PDF), Conversation Search, Scheduled Research UI, Lineage Integration
cf48440 fix: Phase 8.1 - Fix StrategyLineage JSX syntax, JournalEntryResponse schema, add audit doc
1becef7 Phase 8: Research Visualization, Version History & Export
a136ff6 Phase 7: Decision Journal, Research Integration & Strategy Lineage
56b83b9 Phase 6: Conversational AI Studio Integration
9ae2d71 Phase 5: Paper Trading Integration
026aabc Phase 4 Continuation: Strategy Validation, Backtest UI, Immutable Results
b151940 Phase 4: Strategy & Backtesting Integration
b9ba190 Phase 3D: Configurable Cache TTL and Staleness Management
333663b Phase 3C: Configurable Watchlist
```

### Reported Latest Commit
`cf48440` - **VERIFIED**: Exists in history (parent of current HEAD `646ea84`)

---

## Backend Architecture

### Core Services
| Service | File | Description |
|---------|------|-------------|
| Market Data | `app/services/market.py` | Yahoo Finance + deterministic mock fallback, cache with TTL, OHLC validation |
| Indicators | `app/services/indicators.py` | SMA, EMA, RSI, MACD, BBANDS |
| Backtest | `app/services/backtest.py` | Vectorized long-only backtester, next-bar-open fills, no look-ahead |
| Paper Trading | `app/services/paper.py` | Matches backtest execution model, idempotency, SL/TP, slippage, costs |
| Research | `app/services/research.py` | Deterministic multi-agent (Market, Quant, Risk, Strategy) |
| NLP Parser | `app/services/nlp.py` | Rule-based NL → StrategySpec, action detection (backtest/deploy/explain) |
| Validation | `app/services/validation.py` | Structural + enhanced (indicator params, data sufficiency, date ranges) |
| Lineage | `app/services/lineage.py` | Timeline builder from conversations → strategies → backtests → research → journal → deployments |

### API Routers
| Router | Prefix | Endpoints |
|--------|--------|-----------|
| Market | `/api/watchlist` | GET, POST, DELETE watchlist items |
| Strategies | `/api/strategies` | CRUD, versions, diff, chat, research compare, export, search, schedule |
| Backtests | `/api/backtests` | POST run, GET by ID |
| Paper | `/api/paper` | Accounts, deployments, orders, trades, control (pause/resume/stop/close) |
| Journal | `/api/journal` | CRUD with pagination/filtering, legacy compat, outcome review |
| Research | `/api/research` | CRUD, auto-analysis, from-chat, provenance tracking |
| Lineage | `/api/lineage` | GET timeline by strategy/conversation/entity |

### Database Models
- `User` - Single seeded local user (MVP)
- `Conversation` - Messages + draft_spec (JSONB)
- `Strategy` - Name, version, spec (JSONB), user_id
- `MarketBar` - OHLCV + source, unique(symbol, timeframe, ts)
- `BacktestRun` - Strategy spec snapshot, metrics, equity curve, trades, validation
- `PaperAccount` - Name, cash, status (RUNNING/PAUSED/STOPPED/KILLED)
- `PaperDeployment` - Immutable strategy_spec snapshot, execution config, status (ACTIVE/PAUSED/STOPPED/CLOSED)
- `PaperOrder` - Orders linked to deployment, fill_price, slippage, costs
- `PaperPosition` - Per-deployment positions, avg_entry_price, unrealized/realized P&L
- `PaperTrade` - Completed trades with P&L, reason (strategy_entry/exit, stop_loss, take_profit, manual)
- `JournalEntry` - Decision classification, FKs to all entities, content fields, timestamps
- `ResearchRun` - Strategy/backtest snapshots, facts, interpretations, provenance, is_simulated
- `WatchlistItem` - User symbols with unique(user_id, symbol)

---

## Frontend Architecture

### Pages (8 modules)
| Page | File | Description |
|------|------|-------------|
| Dashboard | `Dashboard.jsx` | Market overview, watchlist, data quality |
| Studio | `Studio.jsx` | Conversational AI, chat, backtest/deploy/explain actions, conversation search, export |
| Builder | `Builder.jsx` | Visual strategy builder (ReactFlow), version diff, export |
| Backtest | `Backtest.jsx` | Run backtests, view results |
| Paper | `Paper.jsx` | Paper trading dashboard, deployments, orders, trades |
| Journal | `Journal.jsx` | Decision journal CRUD, filters, pagination, outcome review, export |
| Research | `Research.jsx` | Research runs list/detail, comparison, scheduled research config, export |

### Components
| Component | File | Description |
|-----------|------|-------------|
| StrategyLineage | `components/lineage/StrategyLineage.jsx` | Timeline visualization with navigation links |
| StrategyVersionDiff | `components/strategies/StrategyVersionDiff.jsx` | Version comparison with color-coded changes |
| ResearchComparison | `components/research/ResearchComparison.jsx` | Multi-run comparison (facts, interpretations, risk, provenance) |
| ExportDialog | `components/export/ExportDialog.jsx` | Format selection (JSON/MD/PDF), data selection, download |

### Shared
- `api.jsx` - API client with base URL, error handling, helpers (fmt, Badge, ErrorBox)
- `App.jsx` - Navigation, shared state (draft, saved strategy)

---

## Database Configuration

### Connection
- **Docker**: `postgresql+psycopg2://quant:quant@db:5432/quantniti`
- **Local Dev**: Requires `.env` with `DATABASE_URL=postgresql+psycopg2://quant:quant@localhost:5432/quantniti`

### Migrations
| Migration | Description | Status |
|-----------|-------------|--------|
| 0001_initial | Creates all tables via `Base.metadata.create_all()` | Applied |
| 0002_watchlist_items | Watchlist items table | Applied |
| 0003_phase7_journal_research | JournalEntry enhancements, ResearchRun table | Applied (head) |

### Current State
- All 14 tables exist in database
- Alembic at head: `0003_phase7_journal_research`
- Single seeded user: `local@quantniti` (id=1)

---

## Test Results (Baseline)

### Backend Tests
```
Total: 295 (294 passed, 1 skipped)
- test_backtest.py: 34 passed
- test_import_market_data.py: 19 passed, 1 skipped
- test_indicators.py: 21 passed
- test_journal_research.py: 14 passed
- test_market.py: 25 passed
- test_nlp.py: 31 passed
- test_paper.py: 17 passed
- test_research.py: 13 passed
- test_schemas.py: 27 passed
- test_validation.py: 24 passed

Duration: ~2.5s
Warnings: 6 (5 pandas deprecation, 1 pytest mark)
```

### Frontend Tests
```
Test Files: 2 passed (2)
Tests: 16 passed (16)
- DataQualityPanel.test.jsx: 8
- pages.test.jsx: 8 (all 8 pages render without crashing)

Duration: ~1.6s
Warnings: React act() warnings (expected for async components), reactflow colorMode prop
```

### Production Build
```
✅ SUCCESS
- dist/index.html: 0.44 kB
- dist/assets/index-*.css: 22.29 kB (gzipped: 5.09 kB)
- dist/assets/index-*.js: 787.77 kB (gzipped: 221.52 kB)
- Build time: ~2.2s
- Warning: Chunk > 500 kB (consider code-splitting)
```

---

## Docker Compose Services

```yaml
services:
  db:
    image: postgres:16-alpine
    environment: { POSTGRES_USER: quant, POSTGRES_PASSWORD: quant, POSTGRES_DB: quantniti }
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: { test: ["CMD-SHELL","pg_isready -U quant -d quantniti"], interval: 3s, retries: 20 }
  backend:
    build: ./backend
    env_file: .env
    depends_on: { db: { condition: service_healthy } }
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"
    ports: ["8000:8000"]
  frontend:
    build: ./frontend
    environment: { VITE_API_URL: "http://localhost:8000" }
    depends_on: [backend]
    ports: ["5173:5173"]
volumes: { pgdata: {} }
```

---

## Key Integration Points (For Phase 9 Validation)

### 1. Market Data → Backtest
- `market.get_bars()` → `backtest.run()`
- Cache behavior: TTL-based, stale fallback, mock fallback
- OHLC validation and gap detection

### 2. Strategy Builder → Backtest
- Builder saves strategy → `/api/strategies` POST
- Backtest loads strategy spec snapshot → `/api/backtests` POST
- Version history via `/api/strategies/{sid}/versions`

### 3. Backtest → Research
- Research run links to backtest_run_id
- Auto-fetches strategy_spec_snapshot and backtest_metrics_snapshot
- Runs deterministic analysis on market data

### 4. Research → Journal
- JournalEntry links to research_run_id
- FK validation ensures referential integrity
- Outcome review field for post-hoc analysis

### 5. Journal/Research/Backtest → Lineage
- `lineage.build_lineage()` aggregates events from all tables
- Event types: conversation, strategy, draft_update, backtest, research, journal, deployment, deployment_closed
- Navigation links to related records

### 6. Strategy → Paper Deployment
- Deployment requires passing backtest for same strategy version
- Immutable strategy_spec snapshot at activation
- Execution model matches backtest (next-bar-open, slippage, costs, SL/TP)

### 7. Studio → All Actions
- Chat parses NL → StrategySpec
- Action detection: backtest, deploy, explain
- Explicit approval required for deployment
- Search conversations via `/api/strategies/conversations/search`

---

## Known Issues / Limitations (Baseline)

1. **Alembic Revision Chain**: Fixed 0003 down_revision from `0002_watchlist_items` to `0002`
2. **Database Migration**: Initial tables created via `Base.metadata.create_all()` then stamped
3. **Chunk Size**: Frontend bundle > 500 kB (consider code-splitting for Phase 10+)
4. **React act() Warnings**: Test warnings for async state updates (non-blocking)
5. **Single User**: MVP uses hardcoded user_id=1 (no auth)
6. **Live Data**: Requires `USE_LIVE_DATA=true` and network access; falls back to mock
7. **Scheduled Research**: Config endpoints exist but no scheduler service (documented)
8. **PDF Export**: Basic reportlab implementation; could add charts, styling
9. **Conversation Search**: Uses `messages::text ILIKE` (may be slow at scale)
10. **No Real Broker**: Paper trading only, explicitly labeled

---

## Readiness for Phase 9

✅ **All baseline checks pass:**
- Git history verified
- Backend tests: 294 passed, 1 skipped
- Frontend tests: 16 passed
- Production build: SUCCESS
- Database: All tables exist, alembic at head
- Docker: Services defined, db healthy
- Architecture: Documented and understood

**Ready to proceed with Phase 9 integration testing.**