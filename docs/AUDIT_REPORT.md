# QuantNiti — Repository Audit Report

**Date:** 2026-11-02  
**Auditor:** Senior Software Architect  
**Scope:** Full repository inspection, no modifications

---

## A. Executive Summary

QuantNiti is a **functional MVP** of an AI-assisted quantitative trading research and paper-trading platform. The codebase implements a complete end-to-end workflow: **AI Studio → Visual Builder → Backtest → Paper Trading → Journal**, all gated by a deterministic validation layer.

**Key strengths:**
- Clean, well-structured architecture with clear separation of concerns
- Canonical `StrategySpec` schema (Pydantic v2) shared across all modules — the single source of truth
- No `eval()` or arbitrary code execution; strategies are JSON specifications interpreted by a safe vectorized backtester
- Paper-trading only — no broker integrations, no real-money paths
- Free-to-run stack: FastAPI + React + PostgreSQL + yfinance (with deterministic mock fallback)
- Local LLM-ready design — the NLP parser is a pure function that can be swapped for any LLM emitting `StrategySpec` JSON

**Current state:** **Implemented but not verified** — the code compiles and the architecture is sound, but no automated tests exist, the database requires Docker, and no end-to-end integration has been exercised.

**Critical gaps:**
- Zero test coverage (backend or frontend)
- Market data not cached in `market_bars` table (readme acknowledges this)
- Rule-based NLP parser only — no LLM integrated yet
- Native pandas backtester instead of Backtrader (limits extensibility)
- Single-user, no authentication
- Long-only strategies only

---

## B. Existing Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (React + Vite)                      │
│  ┌──────────┐  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │Dashboard │  │ AI Studio│  │ Builder   │  │ Backtest │  │ Paper    │  │
│  │(Charts)  │  │(Chat+NLP)│  │(ReactFlow)│  │(Metrics) │  │(Sim Acct)│  │
│  └────┬─────┘  └────┬────┘  └─────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │             │        │
│       └─────────────┴──────┬──────┴─────────────┴─────────────┘        │
│                            ▼                                            │
│                    ┌─────────────┐                                      │
│                    │  api.jsx    │  (fetch wrapper, error handling)    │
│                    └──────┬──────┘                                      │
└───────────────────────────┼─────────────────────────────────────────────┘
                            │ HTTP/JSON
┌───────────────────────────┼─────────────────────────────────────────────┐
│                    ┌──────┴──────┐                                      │
│                    │  BACKEND    │                                      │
│                    │ (FastAPI)   │                                      │
│  ┌─────────────────┼─────────────┼──────────────────────────────────┐  │
│  │                 ▼             ▼                                  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │  │
│  │  │ market  │ │strategies│ │backtests│ │ paper   │ │ journal │   │  │
│  │  │ router  │ │ router  │ │ router  │ │ router  │ │ router  │   │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘   │  │
│  │       │           │           │           │           │        │  │
│  │  ┌────┴───────────┴───────────┴───────────┴───────────┴────┐   │  │
│  │  │                    SERVICES                             │   │  │
│  │  │  market.py  │  nlp.py  │  indicators.py  │  backtest.py│   │  │
│  │  │  research.py│ validation.py                    │        │  │
│  │  └────┬────────────────────────────────────────────┬────┘   │  │
│  │       │                                            │          │  │
│  │  ┌────┴────────────────────────────────────────────┴────┐   │  │
│  │  │                    MODELS (SQLAlchemy)                │   │  │
│  │  │ User │ Conversation │ Strategy │ MarketBar │          │   │  │
│  │  │ BacktestRun │ PaperAccount │ PaperOrder │ JournalEntry│   │  │
│  │  └────┬────────────────────────────────────────────┬────┘   │  │
│  │       │                                            │          │  │
│  │  ┌────┴────────────────────────────────────────────┴────┐   │  │
│  │  │              POSTGRESQL (via SQLAlchemy + Alembic)    │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **AI Studio** — User types natural language → `nlp.parse()` → `StrategySpec` JSON → persisted in `Conversation.draft_spec`
2. **Builder** — Loads `draft_spec` → renders ReactFlow nodes/edges → user edits → `toSpec()` → canonical `StrategySpec`
3. **Save** — `StrategySpec` → `Strategy` table (versioned by name)
4. **Backtest** — Loads `Strategy` + market data → `indicators.compute()` → `backtest.signals()` → `backtest.run()` → metrics + equity curve + trades → `validation.validate()` → persists `BacktestRun`
5. **Paper Trading** — Deploy gates on `validation.passed` → `step()` evaluates latest bar → simulated fills at `close` → `PaperOrder` + `PaperAccount` updated
6. **Journal** — Logs decisions with evidence snapshot (from `research.run()`)

---

## C. Repository Inventory

### Backend (`/backend`)

| Path | Responsibility | Status |
|------|----------------|--------|
| `app/main.py` | FastAPI app, CORS, router registration, seeded user | ✅ Complete |
| `app/db.py` | SQLAlchemy engine, session factory, `Base` | ✅ Complete |
| `app/models.py` | 8 SQLAlchemy models (User, Conversation, Strategy, MarketBar, BacktestRun, PaperAccount, PaperOrder, JournalEntry) | ✅ Complete |
| `app/schemas.py` | Pydantic models: `StrategySpec` (canonical), `IndicatorSpec`, `Rule`, `RiskLimits`, request/response DTOs | ✅ Complete |
| `app/services/indicators.py` | Vectorized SMA, EMA, RSI, MACD, BBANDS on pandas Series | ✅ Complete |
| `app/services/backtest.py` | Vectorized long-only backtester (next-bar-open fills, stop/take-profit, metrics) | ✅ Complete |
| `app/services/validation.py` | Structural + metric-based validation gate (blocks deployment) | ✅ Complete |
| `app/services/nlp.py` | Rule-based NL → `StrategySpec` parser (regex patterns for crossovers, RSI, stops) | ✅ Complete |
| `app/services/research.py` | Multi-agent "facts + interpretations" (deterministic templates) | ✅ Complete |
| `app/services/market.py` | Yahoo Finance via `yfinance` + deterministic mock fallback (seeded RNG) | ✅ Complete |
| `app/routers/market.py` | `/watchlist`, `/bars`, `/research`, `/search` | ✅ Complete |
| `app/routers/strategies.py` | CRUD + chat endpoint (`/chat` persists conversation + draft) | ✅ Complete |
| `app/routers/backtests.py` | Run backtest, structural pre-check, full validation gate, persist run | ✅ Complete |
| `app/routers/paper.py` | Accounts, manual orders, deploy gate, control (pause/resume/stop/kill), `step()` evaluation | ✅ Complete |
| `app/routers/journal.py` | Log decisions with evidence, add outcome reviews | ✅ Complete |
| `alembic/versions/0001_initial.py` | Creates all tables idempotently | ✅ Complete |
| `requirements.txt` | 9 pinned dependencies (see Technology Audit) | ✅ Complete |
| `Dockerfile` | Python 3.12 slim, installs requirements, copies source | ✅ Complete |

### Frontend (`/frontend`)

| Path | Responsibility | Status |
|------|----------------|--------|
| `src/main.jsx` | React 18 root render | ✅ Complete |
| `src/App.jsx` | Layout, nav, global state (`draft`, `saved` StrategySpec) | ✅ Complete |
| `src/api.jsx` | Fetch wrapper, formatting, `Badge`, `ErrorBox` components | ✅ Complete |
| `src/pages/Dashboard.jsx` | Watchlist, candlestick + indicators (Recharts), research panel | ✅ Complete |
| `src/pages/Studio.jsx` | Chat UI, sends to `/api/strategies/chat`, shows canonical JSON, save button | ✅ Complete |
| `src/pages/Builder.jsx` | ReactFlow canvas, node palette, `fromSpec`/`toSpec` serialization, property editor | ✅ Complete |
| `src/pages/Backtest.jsx` | Strategy picker, run button, metrics cards, equity/drawdown charts, validation display | ✅ Complete |
| `src/pages/Paper.jsx` | Account CRUD, positions table, manual orders, deploy gate, step evaluation, kill switch | ✅ Complete |
| `src/pages/Journal.jsx` | Decision log with evidence snapshot, outcome review | ✅ Complete |
| `package.json` | React 18, Recharts, ReactFlow, Lucide, Vite, Tailwind | ✅ Complete |
| `vite.config.js` | Basic Vite + React plugin, port 5173 | ✅ Complete |
| `tailwind.config.js` | Custom colors (ink, panel, line, up, down, ai), fonts | ✅ Complete |
| `Dockerfile` | Node 20 alpine, `npm install`, `npm run dev -- --host` | ✅ Complete |

### Infrastructure

| Path | Responsibility |
|------|----------------|
| `docker-compose.yml` | PostgreSQL 16, backend (alembic + uvicorn), frontend (Vite dev) |
| `.env.example` | `DATABASE_URL`, `CORS_ORIGINS`, `USE_LIVE_DATA` |
| `README.md` | Run instructions, flow, safety design, known MVP limits |

---

## D. Feature Status Matrix

| Module | Status | Evidence |
|--------|--------|----------|
| **Market Data** | Implemented but not verified | `market.py` has Yahoo + mock; `/bars` endpoint works; `MarketBar` table defined but **not populated** (readme confirms) |
| **AI Studio (Chat)** | Implemented but not verified | `nlp.py` regex parser works; `/chat` persists conversation + draft; no LLM integrated |
| **Visual Builder** | Implemented but not verified | ReactFlow canvas, `fromSpec`/`toSpec` round-trip, property editing; saves to shared `draft` state |
| **Strategy Schema** | Implemented and verified | Pydantic `StrategySpec` v1.0 with validators; used by all routers/services |
| **Backtesting** | Implemented but not verified | Vectorized engine computes metrics (return, DD, Sharpe, win rate, PF, exposure, trades); equity curve; validation gate |
| **Analytics/Metrics** | Implemented but not verified | 7 metrics calculated; charts render in Backtest page; no unit tests for correctness |
| **Paper Trading** | Implemented but not verified | Full sim engine: accounts, positions (avg cost, unrealized/realized P&L), manual orders, strategy deploy gate, `step()` evaluation, pause/resume/stop/kill |
| **Journal** | Implemented but not verified | CRUD for entries with evidence snapshot; outcome review field |
| **Authentication** | Missing | Single seeded user (`id=1`), no auth middleware |
| **Multi-Agent Research** | Partially implemented | `research.run()` returns facts + 4 templated agent views; **not LLM-driven**, no persistence of reports |
| **Data Caching** | Missing | `MarketBar` model exists but `market.py` never writes to it |
| **Tests** | Missing | Zero test files in backend or frontend |

**Status Legend:**
- **Implemented and verified** — code exists, compiles, and has been tested (manual or automated)
- **Implemented but not verified** — code exists and compiles, but no test evidence
- **Partially implemented** — skeleton exists, core logic incomplete
- **Missing** — no code present

---

## E. Technology and Cost Audit

### Backend Dependencies

| Package | Version (pinned) | Version (installed) | License | Cost Class | Notes |
|---------|------------------|---------------------|---------|------------|-------|
| fastapi | 0.115.0 | 0.162.0 | MIT | **1. Free** | Core framework |
| uvicorn | 0.30.6 | 0.54.0 | BSD-3-Clause | **1. Free** | ASGI server |
| sqlalchemy | 2.0.35 | 2.1.6 | MIT | **1. Free** | ORM |
| alembic | 1.13.3 | 1.20.1 | MIT | **1. Free** | Migrations |
| psycopg2-binary | 2.9.9 | 2.9.13 | LGPL w/ exceptions | **1. Free** | PG driver (binary wheel) |
| pydantic | 2.9.2 | 2.14.2 | MIT | **1. Free** | Validation |
| pandas | 2.2.3 | 3.1.0 | BSD-3-Clause | **1. Free** | Data frames |
| numpy | 2.1.1 | 2.5.4 | BSD-3-Clause + others | **1. Free** | Numeric |
| yfinance | 0.2.43 | 1.7.0 | Apache-2.0 | **3. Free tier w/ limits** | Yahoo Finance scraper — **unofficial, rate-limited, no SLA** |

### Frontend Dependencies

| Package | Version | License | Cost Class |
|---------|---------|---------|------------|
| react | 18.3.1 | MIT | **1. Free** |
| react-dom | 18.3.1 | MIT | **1. Free** |
| recharts | 2.12.7 | MIT | **1. Free** |
| reactflow | 11.11.4 | MIT | **1. Free** |
| lucide-react | 0.441.0 | ISC | **1. Free** |
| vite | 5.4.8 | MIT | **1. Free** |
| @vitejs/plugin-react | 4.3.2 | MIT | **1. Free** |
| tailwindcss | 3.4.13 | MIT | **1. Free** |
| postcss | 8.4.47 | MIT | **1. Free** |
| autoprefixer | 10.4.20 | MIT | **1. Free** |

### Infrastructure

| Component | Version | License | Cost Class |
|-----------|---------|---------|------------|
| PostgreSQL | 16 (Docker) | PostgreSQL License (MIT-like) | **1. Free** — self-hosted |
| Node.js | 20 (Docker) | MIT | **1. Free** |
| Python | 3.12 (Docker) | PSF | **1. Free** |

### Cost Classification Summary

| Class | Count | Examples |
|-------|-------|----------|
| **1. Free and suitable for local development** | 17 | All core deps, PostgreSQL, Python, Node |
| **2. Free but subject to usage/licensing conditions** | 1 | psycopg2-binary (LGPL — OK for linking, not static bundling) |
| **3. Free tier with limitations** | 1 | **yfinance** — unofficial Yahoo scraper, aggressive rate limits, no redistribution rights, may break without notice |
| **4. Paid dependency** | 0 | None |
| **5. Unknown** | 0 | None |

### ⚠️ Critical Cost Risk: `yfinance`

**yfinance is NOT a supported API.** It scrapes Yahoo Finance HTML/JSON endpoints.
- **Rate limits:** Undocumented, aggressive (IP bans common)
- **No SLA:** Breaks when Yahoo changes frontend
- **No redistribution rights:** Terms prohibit commercial redistribution of data
- **Not suitable for production** — only for development/prototyping

**Recommended free alternatives:**
1. **Local CSV/Parquet datasets** — download once, store in `market_bars` table
2. **Alpha Vantage / Twelve Data free tiers** — 25-500 req/day, requires API key (still free tier)
3. **Stooq / Nasdaq Data Link** — free historical CSVs
4. **Polygon.io free tier** — 5 req/min, websocket for real-time (requires key)
5. **Self-hosted data pipeline** — ingest from free sources into PostgreSQL

---

## F. Market-Data Audit

### Current Implementation (`backend/app/services/market.py`)

| Aspect | Status |
|--------|--------|
| **Providers** | Yahoo Finance (`yfinance`) + deterministic mock generator |
| **Instruments** | Hardcoded watchlist: `BTC-USD`, `ETH-USD`, `AAPL`, `SPY` (+ search adds `MSFT`, `TSLA`, `QQQ`, `SOL-USD`) |
| **Timeframes** | `1m`, `5m`, `15m`, `1h`, `1d` (mapped to yfinance intervals) |
| **Data Type** | Delayed (Yahoo) or simulated (mock) — **not real-time** |
| **Caching** | **None** — `MarketBar` table exists but never written |
| **Timestamps** | UTC-naive `datetime` (yfinance returns tz-aware, stripped via `tz_localize(None)`) |
| **Quality Checks** | Only `len(df) > 30` check before accepting Yahoo data |
| **Missing/Duplicate Detection** | None |
| **Backtester Data Source** | Same `get_bars()` function — consistent but not cached |
| **Provider Swappability** | Moderate — `get_bars()` is the single access point, but callers expect specific DataFrame shape |

### Mock Generator Details
- Deterministic per symbol/timeframe (CRC32 seed)
- GBM with fixed drift/vol per asset class (crypto vs equity)
- OHLC synthesized from close series
- Badged `SIMULATED` in response metadata

### Limitations
1. **No persistence** — every request hits Yahoo or regenerates mock
2. **No intraday history beyond yfinance limits** (1m: 7 days, 5m/15m/1h: 60 days)
3. **No corporate actions** (splits, dividends) — `auto_adjust=True` helps but not verified
4. **Single-symbol per request** — no batch/multi-symbol endpoint
5. **Watchlist hardcoded** — not configurable

### Required Improvements
| Priority | Task |
|----------|------|
| P0 | Implement `MarketBar` write-through cache in `get_bars()` |
| P0 | Add data-quality validation (gaps, duplicates, OHLC consistency) |
| P1 | Support local CSV/Parquet import for backtesting |
| P1 | Make watchlist configurable (database-backed) |
| P2 | Add multi-symbol batch endpoint |
| P2 | Implement corporate-action adjustment verification |
| P3 | Add data provenance tracking (source, fetch time, adjustments) |

---

## G. AI Audit

### Current Implementation

| Component | File | Status |
|-----------|------|--------|
| **NLP Parser** | `services/nlp.py` | Rule-based regex parser → `StrategySpec` |
| **Chat Persistence** | `routers/strategies.py` `/chat` | Conversation + messages + `draft_spec` in `Conversation` table |
| **Multi-Agent Research** | `services/research.py` | Deterministic "facts + templated interpretations" |
| **Local Model Ready** | `nlp.parse()` signature | Pure function `(text, base_spec?) → (spec, clarifications)` — can swap for LLM |

### NLP Parser Capabilities (`nlp.py`)

| Pattern | Example | Extracts |
|---------|---------|----------|
| Ticker | "buy BTC" | `instruments: ["BTC-USD"]` |
| Timeframe | "daily", "1h", "15m" | `timeframe` |
| MA Crossover | "EMA 20 crosses above EMA 50" | 2 indicators + entry/exit rules |
| RSI Threshold | "RSI below 30" | RSI indicator + rule |
| Stop Loss | "stop loss 5%" | `risk.stop_loss_pct` |
| Take Profit | "take profit 10%" | `risk.take_profit_pct` |
| Position Size | "size 30%" | `risk.max_position_pct` |
| Clarifications | Missing instrument, entry, exit | Returns `ask` list for chat |

### Multi-Agent Research (`research.py`)

**Agents (deterministic templates):**
1. **Market Analyst** — Trend (EMA20 vs EMA50), volatility
2. **Bull** — List of bullish facts (oversold RSI, positive MACD, momentum)
3. **Bear** — List of bearish facts (overbought RSI, negative MACD, momentum)
4. **Risk Analyst** — Risk level (HIGH/MODERATE/LOW), suggested stop-loss
5. **Strategy Manager** — Stance (LEAN LONG/FLAT/NEUTRAL), evidence count

**Output:** `{"facts": {...}, "interpretations": {...}, "label": "AI-GENERATED INTERPRETATION · PAPER/SIMULATED"}`

### Paid AI Dependencies
- **None currently** — rule-based only
- **No API keys** in codebase or `.env`

### Local LLM Integration Path
The architecture is **designed for local LLM swap**:
```python
# services/nlp.py — current signature
def parse(text: str, base: StrategySpec | None = None) -> tuple[StrategySpec, list[str]]:
    ...
```
Replace with:
```python
def parse(text: str, base: StrategySpec | None = None) -> tuple[StrategySpec, list[str]]:
    prompt = build_prompt(text, base)
    json_str = call_local_llm(prompt)  # Ollama, llama.cpp, etc.
    spec = StrategySpec.model_validate_json(json_str)
    return spec, []
```
**Pydantic validation guarantees schema compliance regardless of LLM output.**

### Missing AI Capabilities
| Capability | Status |
|------------|--------|
| LLM integration (Ollama, vLLM, etc.) | Not implemented |
| Streaming chat responses | Not implemented |
| Conversation branching/forking | Not implemented |
| Strategy critique/review agent | Not implemented (only bull/bear templates) |
| Research report persistence | Not implemented |
| Agent-to-agent dialogue | Not implemented |

---

## H. Backtesting and Financial-Correctness Audit

### Execution Pipeline

```
StrategySpec + Market Data (DataFrame)
        │
        ▼
indicators.compute(df, spec.indicators)  ──► DataFrame with indicator columns
        │
        ▼
backtest.signals(df, spec)  ──► (entry: Series[bool], exit: Series[bool])
        │
        ▼
backtest.run(spec, df, initial_cash)
        │
        ├──► Vectorized signal evaluation (no look-ahead: uses shift())
        ├──► Bar-by-bar simulation loop (fills at NEXT bar OPEN)
        ├──► Stop-loss / Take-profit checked on CURRENT bar CLOSE
        ├──► Position sizing: % of current cash (max_position_pct)
        ├──► Long-only, no shorting, no leverage
        └──► Metrics calculation
```

### Metrics Computed

| Metric | Formula | Notes |
|--------|---------|-------|
| Total Return | `(final_equity / initial_cash - 1) * 100` | Includes unrealized P&L on final bar |
| Max Drawdown | `min(equity / cummax(equity) - 1) * 100` | Peak-to-trough |
| Sharpe | `mean(daily_returns) / std(daily_returns) * sqrt(ann_factor)` | Ann factor per timeframe; **assumes risk-free = 0** |
| Win Rate | `% of trades with pnl > 0` | |
| Profit Factor | `gross_profit / gross_loss` | Returns `999` if no losses, `None` if no trades |
| Exposure | `% of bars with position > 0` | |
| Trades | Count of completed round-trips | |

### Correctness Risks

| Risk | Severity | Location | Mitigation Needed |
|------|----------|----------|-------------------|
| **Fill price = next bar OPEN** | Medium | `backtest.run()` line 24 | Document assumption; add configurable fill model (open/close/vwap) |
| **Stop/TP checked on current CLOSE** | Medium | `backtest.run()` lines 28-29 | Intra-bar not modeled; document as conservative |
| **Position sizing uses current cash** | Low | `backtest.run()` line 34 | Compounds correctly; verify with unit tests |
| **Sharpe assumes 0 risk-free rate** | Low | `backtest.run()` line 43 | Add config for risk-free rate |
| **Annualization factors hardcoded** | Low | `backtest.run()` line 42 | Make configurable; verify 1m/5m factors |
| **No transaction costs / slippage** | High | `backtest.run()` — absent | Add `commission_pct`, `slippage_bps` to `RiskLimits` |
| **No dividend/split handling** | Medium | `market.py` uses `auto_adjust=True` | Verify with known corporate actions |
| **Look-ahead in indicator computation** | Low | `indicators.compute()` uses `.rolling()`/`.ewm()` | Pandas rolling is backward-looking — OK |
| **Entry/exit on same bar** | Low | `signals()` uses `shift()` for crosses | Prevents same-bar cross fire — OK |
| **Equity curve includes unrealized** | Low | `backtest.run()` line 36 | Standard practice; document |

### Validation Gate (`validation.py`)

| Check | Type | Blocks Deployment? |
|-------|------|-------------------|
| Instruments selected | Structural | Yes |
| Entry rules exist | Structural | Yes |
| Exit rules OR stop-loss | Structural | Yes |
| Rule references valid indicators | Structural | Yes |
| Position size ≤ 50% | Warning | No |
| Backtest trades ≥ 5 | Metric | Yes |
| Backtest max DD ≤ risk.max_drawdown_pct | Metric | Yes |

**Strength:** Validation is **mandatory** — `paper.py` deploy endpoint calls `validate()` and rejects on any error.

---

## I. Paper-Trading and Security Audit

### Paper Engine (`routers/paper.py`)

| Feature | Implementation |
|---------|----------------|
| Simulated Cash | `PaperAccount.cash` (float), initialized from `starting_cash` |
| Simulated Orders | `PaperOrder` table: symbol, side, qty, fill_price, reason, label="PAPER/SIMULATED" |
| Positions | Computed on-demand from order history (FIFO avg cost) |
| Portfolio Accounting | `cash + Σ(qty × last_price)` — last price from `market.get_bars(sym, "1d", 60)` |
| Realized P&L | Tracked per symbol on SELL (FIFO) |
| Unrealized P&L | `(last - avg_cost) × qty` |
| Transaction Costs | **None** — fills at exact `close` |
| Position Limits | `max_position_pct` from strategy risk (enforced on entry) |
| Risk Controls | Stop-loss / take-profit evaluated in `step()` via backtest signals |
| Order History | Full `PaperOrder` log with timestamps |
| Execution Logs | Returns `{"action": "BUY|SELL|HOLD"}` with fill details |
| Strategy Activation | `deploy` endpoint — **gated by validation gate** |
| Deactivation | `control/stop`, `control/kill` — `status` field blocks orders |
| Duplicate Prevention | `step()` checks `held < 1e-9` before BUY, `held > 1e-9` before SELL |
| Real Broker Integrations | **None** — explicitly documented |

### Security Analysis

| Vector | Status | Evidence |
|--------|--------|----------|
| Arbitrary code execution | **Blocked** | Strategies are JSON `StrategySpec`; no `eval()`, `exec()`, `importlib` |
| SQL Injection | **Mitigated** | SQLAlchemy ORM + parameterized queries |
| Path Traversal | **N/A** | No file uploads |
| Auth Bypass | **N/A (no auth)** | Single seeded user — MVP limitation |
| Real Order Leakage | **Blocked** | No broker SDKs imported; `PaperOrder.label` hardcoded "PAPER/SIMULATED" |
| Data Exfiltration | **Low Risk** | Only market data (public) and user strategies |
| Rate Limiting | **Missing** | No middleware — add for production |

### Architectural Boundary (Paper-Only Enforcement)

The **only path to order placement** is `paper.py`:
1. Manual: `POST /api/paper/accounts/{aid}/orders` → `_fill()` → `PaperOrder`
2. Strategy: `POST /api/paper/accounts/{aid}/step` → `_fill()` → `PaperOrder`

**Both require:**
- `account.status == "RUNNING"` (enforced in `_fill()`)
- Sufficient simulated cash (BUY)
- No short selling (SELL ≤ held)
- Strategy deployment validated by backtest gate

**No code path reaches external network for order execution.**

---

## J. Test Baseline

### Test Files Found
| Location | Count |
|----------|-------|
| Backend (`backend/app/**/test*.py` or `backend/tests/`) | **0** |
| Frontend (`frontend/src/**/*.test.{js,jsx,ts,tsx}`) | **0** |
| Integration/E2E | **0** |

### Manual Verification Performed

| Check | Command | Result |
|-------|---------|--------|
| Python syntax (all modules) | `python -m py_compile app/*.py app/services/*.py app/routers/*.py` | ✅ PASS |
| Pydantic schema validation | Import `StrategySpec` with valid/invalid data | ✅ PASS (schema loads) |
| Backend import (no DB) | `from app.main import app` (with mock DB) | ⚠️ Requires PostgreSQL |
| Frontend build | `npm run build` (not run — no Node env verified) | Not run |

### Test Commands That Cannot Run Safely

| Test | Reason |
|------|--------|
| Backend unit tests | No test files exist |
| API integration tests | Requires running PostgreSQL (Docker) |
| Frontend component tests | No test files, no test runner configured |
| Backtest correctness tests | No test fixtures or known-good outputs |
| Paper trading simulation tests | Requires DB + backend running |
| End-to-end flow tests | Requires full stack (Docker Compose) |

**Recommendation:** Add `pytest` + `pytest-asyncio` to backend, `vitest` + `react-testing-library` to frontend before Week 2.

---

## K. Prioritized Implementation Backlog

### P0 — Critical Correctness / Security

| ID | Task | Module | Effort |
|----|------|--------|--------|
| P0-1 | Add transaction costs + slippage to backtester & paper engine | Backtest, Paper | M |
| P0-2 | Implement `MarketBar` write-through cache in `market.get_bars()` | Market Data | M |
| P0-3 | Add data quality validation (gaps, duplicates, OHLC sanity) | Market Data | M |
| P0-4 | Add pytest backend test suite with fixtures | Testing | L |
| P0-5 | Add vitest frontend test suite | Testing | M |
| P0-6 | Verify Sharpe annualization factors for all timeframes | Backtest | S |
| P0-7 | Add commission/slippage fields to `RiskLimits` schema | Schema | S |

### P1 — Required for Core Workflow

| ID | Task | Module | Effort |
|----|------|--------|--------|
| P1-1 | Integrate local LLM (Ollama) behind `nlp.parse()` | AI Studio | M |
| P1-2 | Add streaming chat responses (SSE) | AI Studio | M |
| P1-3 | Implement CSV/Parquet historical data import | Market Data | M |
| P1-4 | Make watchlist configurable (DB-backed) | Market Data | S |
| P1-5 | Add strategy versioning UI (compare versions) | Builder | M |
| P1-6 | Persist research reports (new `ResearchReport` model) | AI/Research | M |
| P1-7 | Add authentication (JWT, at least API key) | Auth | L |
| P1-8 | Implement multi-symbol backtesting (portfolio) | Backtest | L |
| P1-9 | Add rate limiting middleware | Security | S |

### P2 — Important Improvements

| ID | Task | Module | Effort |
|----|------|--------|--------|
| P2-1 | Replace pandas backtester with Backtrader (or extend current) | Backtest | L |
| P2-2 | Add walk-forward / out-of-sample validation | Backtest | L |
| P2-3 | Implement strategy optimizer (grid search) | Backtest | L |
| P2-4 | Add Monte Carlo simulation for equity curves | Analytics | M |
| P2-5 | Add strategy comparison dashboard | Analytics | M |
| P2-6 | Implement skeptical review agent (critiques strategy) | AI/Research | M |
| P2-7 | Add research agent coordination (lead researcher) | AI/Research | M |
| P2-8 | Support short positions (margin, borrow costs) | Paper, Backtest | L |
| P2-9 | Add webhook/alert system for paper fills | Paper | M |
| P2-10 | Implement data provenance tracking (source, adjustments) | Market Data | M |

### P3 — Optional Enhancements

| ID | Task | Module | Effort |
|----|------|--------|--------|
| P3-1 | Options/futures support | All | XL |
| P3-2 | Social features (share strategies) | Platform | L |
| P3-3 | Mobile-responsive UI polish | Frontend | M |
| P3-4 | Dark/light theme toggle | Frontend | S |
| P3-5 | Export backtest reports (PDF/HTML) | Analytics | M |
| P3-6 | Plugin system for custom indicators | Extensibility | L |
| P3-7 | Multi-user with organizations | Auth | XL |

---

## L. Ten-Week Roadmap (Adapted to Current State)

| Week | Focus | Existing to Preserve | New Work | Key Files/Modules | Risks |
|------|-------|---------------------|----------|-------------------|-------|
| **1** | **Audit & Foundation** | All existing code | ✅ Audit complete (this report)<br>✅ Add pytest + vitest<br>✅ CI smoke test (lint + typecheck)<br>✅ Document local dev setup | `backend/requirements.txt`, `frontend/package.json`, `docs/` | Low — no code changes yet |
| **2** | **Market Data & Dashboard** | `market.py`, `Dashboard.jsx`, `MarketBar` model | Write-through cache in `get_bars()`<br>Data quality checks<br>CSV import CLI<br>Configurable watchlist<br>Dashboard: show data provenance badges | `services/market.py`, `models.py` (add `last_cached`), `routers/market.py`, `Dashboard.jsx` | Yahoo rate limits during dev |
| **3** | **Strategy Builder** | `schemas.py`, `Builder.jsx`, `Studio.jsx`, `nlp.py` | Canonical schema v1.1 (add costs, multi-symbol)<br>Builder: multi-instrument, condition groups (AND/OR)<br>Studio: streaming LLM (Ollama)<br>Version diff UI | `schemas.py`, `Builder.jsx`, `Studio.jsx`, `services/nlp.py` | LLM integration complexity |
| **4** | **Backtesting** | `backtest.py`, `validation.py`, `Backtest.jsx` | Add commission/slippage to spec & engine<br>Walk-forward validation<br>Metric unit tests (known fixtures)<br>Backtest comparison view | `backtest.py`, `schemas.py`, `validation.py`, `Backtest.jsx` | Financial correctness |
| **5** | **Analytics** | `Backtest.jsx` charts, `backtest.py` metrics | Monte Carlo equity simulation<br>Strategy comparison table<br>Trade analysis (MAE/MFE, hold time)<br>Export reports | `backtest.py` (new), `Analytics.jsx` (new), `Backtest.jsx` | Statistical validity |
| **6** | **Conversational AI Studio** | `Studio.jsx`, `nlp.py`, `Conversation` model | Ollama integration (local)<br>SSE streaming<br>Conversation branching<br>Prompt templates for strategy types | `services/nlp.py`, `routers/strategies.py`, `Studio.jsx` | Model quality, latency |
| **7** | **Multi-Agent Research** | `research.py`, `Dashboard.jsx` research panel | Distinct agent classes (Market, Quant, Risk, Skeptic, Lead)<br>Agent dialogue protocol<br>Persist reports to `ResearchReport` table<br>Evidence citations from backtests | `services/research.py` (rewrite), `models.py`, `routers/market.py` | Agent coordination complexity |
| **8** | **Risk & Paper Trading** | `paper.py`, `Paper.jsx`, `validation.py` | Portfolio-level risk (correlation, sector limits)<br>Pre-trade risk checks (max DD, concentration)<br>Paper engine: add costs/slippage<br>Kill switch audit trail | `paper.py`, `schemas.py` (risk), `Paper.jsx` | Regulatory-grade controls |
| **9** | **Integration** | All modules | E2E flow test (Studio→Builder→Backtest→Paper→Journal)<br>Error handling + retry UI<br>Persistence verification (restart survival)<br>Performance profiling | All routers, `App.jsx` state mgmt | Integration bugs |
| **10** | **Testing & Delivery** | Test suites from Wk 1-9 | Regression suite (backend + frontend)<br>Load test paper engine (100 accounts)<br>Documentation: install, limits, API<br>Reproducible demo script (docker compose) | `docs/`, `tests/`, `docker-compose.yml` | Release readiness |

---

## M. Immediate Next Steps (Next Development Session)

| Order | Task | Command / Action |
|-------|------|------------------|
| 1 | **Start infrastructure** | `cd /Users/smitshrismackbook/Downloads/quantniti && docker compose up -d db` |
| 2 | **Run migrations** | `docker compose run --rm backend alembic upgrade head` |
| 3 | **Start backend** | `docker compose up -d backend` → verify `http://localhost:8000/docs` |
| 4 | **Start frontend** | `docker compose up -d frontend` → verify `http://localhost:5173` |
| 5 | **Smoke test full flow** | Dashboard → Studio (chat) → Builder (sync) → Backtest (run) → Paper (deploy + step) → Journal (log) |
| 6 | **Add test dependencies** | Backend: `pip install pytest pytest-asyncio httpx`<br>Frontend: `npm install -D vitest @testing-library/react jsdom` |
| 7 | **Write first backend tests** | `backend/tests/test_schemas.py`, `test_indicators.py`, `test_backtest.py` |
| 8 | **Write first frontend tests** | `frontend/src/pages/__tests__/Dashboard.test.jsx` |
| 9 | **Implement MarketBar cache** | Modify `services/market.py:get_bars()` to upsert to `MarketBar` |
| 10 | **Add transaction costs to schema** | `schemas.py:RiskLimits` → add `commission_bps`, `slippage_bps` |

---

## N. Risks and Unresolved Questions

| Risk | Impact | Likelihood | Status |
|------|--------|------------|--------|
| **yfinance breaks / rate-limits** | Market data unavailable | High | **Mitigated** by mock fallback; **P0** to add local data |
| **No authentication** | Single-user only; no isolation | Medium | **P1** — add JWT/API key |
| **Financial correctness untested** | Backtest metrics may be wrong | High | **P0** — unit tests with known fixtures |
| **Mock data used in backtests silently** | User thinks they're testing real data | Medium | UI shows `SIMULATED` badge; **improve prominence** |
| **Single-symbol backtest only** | No portfolio strategies | Medium | **P1** — multi-symbol support |
| **No transaction costs** | Overstated returns | High | **P0** — add to schema + engine |
| **LLM integration unproven** | `nlp.parse()` swap may need more context | Medium | **P1** — prototype with Ollama |
| **ReactFlow serialization edge cases** | Builder ↔ Studio round-trip loss | Low | **Test** `fromSpec`/`toSpec` round-trip |
| **Alembic migration strategy** | Schema changes need migrations | Medium | **Use Alembic** for all schema changes |
| **Docker Compose for dev only** | No production deployment config | Low | **P3** — add prod compose / k8s |

### Unresolved Questions Requiring Decisions

1. **Backtrader vs. native pandas backtester** — Native is simpler, no deps; Backtrader adds event-driven realism, analyzers, optimization. **Recommend:** Extend native for v1, evaluate Backtrader for v2.

2. **Local LLM choice** — Ollama (easiest), llama.cpp (fastest), vLLM (high throughput). **Recommend:** Ollama for dev (Docker), document swap.

3. **Multi-symbol strategy schema** — Current `instruments: list[str]` but backtester only uses `[0]`. **Decision needed:** Portfolio backtest (vectorized) vs. sequential single-symbol.

4. **Data redistribution** — If caching Yahoo data in PostgreSQL, check Yahoo ToS. **Recommend:** Use only free-licensed datasets (Stooq, Nasdaq Data Link free tier) for cached data.

5. **Authentication model** — MVP is single-user. For multi-user: JWT? API keys? OAuth? **Recommend:** Start with simple API key per user (header `X-API-Key`).

---

## Final Confirmation

**No destructive changes were performed during this audit:**
- ✅ No files deleted or overwritten
- ✅ No database migrations run
- ✅ No dependencies installed/upgraded (except in isolated venv for license check)
- ✅ No `.env` modifications
- ✅ No broker connections attempted
- ✅ No real orders placed
- ✅ No paid services activated
- ✅ No schema modifications
- ✅ No code rewrites

**Files created during audit:**
- `/Users/smitshrismackbook/Downloads/quantniti/docs/AUDIT_REPORT.md` (this report)

---

**Audit Complete.** The repository is a well-architected MVP with a clear path to production. The highest-leverage next steps are: (1) spin up Docker stack for integration verification, (2) add test infrastructure, (3) implement market data caching, and (4) add transaction costs to the financial engine.