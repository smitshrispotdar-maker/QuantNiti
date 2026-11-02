# QuantNiti — Strategy & Backtesting Audit Report

**Date:** 2024  
**Auditor:** Phase 4 Implementation

---

## 1. Current Architecture Overview

### 1.1 Strategy Specification (Canonical Schema)
**File:** `backend/app/schemas.py` — `StrategySpec` v1.0

The project already has a well-defined `StrategySpec` v1.0 schema in `backend/app/schemas.py`:

```python
class StrategySpec(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    name: str = "Untitled strategy"
    instruments: list[str] = []
    timeframe: Literal["1m", "5m", "15m", "1h", "1d"] = "1d"
    indicators: list[IndicatorSpec] = []
    entry_rules: list[Rule] = []
    exit_rules: list[Rule] = []
    risk: RiskLimits = RiskLimits()
```

**Supported Indicator Types:** SMA, EMA, RSI, MACD, BBANDS  
**Supported Operators:** `>`, `<`, `crosses_above`, `crosses_below`  
**Rule Structure:** left (indicator/price), operator, right (indicator/price/number)  
**Risk Limits:** max_position_pct, stop_loss_pct, take_profit_pct, max_drawdown_pct  

**Status:** ✅ **Canonical schema exists and is well-defined.** Used by chat studio, visual builder, backtester, and paper engine.

---

### 1.2 Strategy Persistence

**Model:** `backend/app/models.py` — `Strategy` table
- Fields: id, user_id, name, version, spec (JSONB), created_at
- Versioning: New version created when saving with same name
- Single user (id=1) — no auth in MVP

### 1.3 Strategy API Routes (`backend/app/routers/strategies.py`)
- `GET /api/strategies` — List all strategies
- `POST /api/strategies` — Save strategy (creates new version if name exists)
- `GET /api/strategies/{sid}` — Get strategy by ID
- `POST /api/strategies/chat` — AI chat for strategy creation (rule-based parser)
- `GET /api/strategies/chat/{cid}` — Get conversation history

### 1.4 Visual Strategy Builder (Frontend)
**File:** `frontend/src/pages/Builder.jsx`

**Current State:**
- ReactFlow-based visual editor with node palette (Market Data, Indicator, Condition, Entry, Exit, Risk)
- Nodes: Market Data, Indicator, Condition, Entry, Exit, Risk
- Edges: Conditions wired to Entry/Exit nodes
- Bidirectional sync: `toSpec()` (canvas → StrategySpec), `fromSpec()` (spec → canvas)
- Node property editing panel
- Live JSON preview
- "Sync to strategy" button saves via `POST /api/strategies`

**Status:** ✅ Functional visual builder with bidirectional sync to canonical schema

---

### 1.5 Backtesting Engine

**Service:** `backend/app/services/backtest.py`

**Engine Type:** Deterministic vectorized long-only backtester
- Vectorized signal computation (no look-ahead: uses `.shift()` for crosses)
- Bar-by-bar simulation loop
- Fills at next bar open (no look-ahead)
- Stop-loss / take-profit checked on current bar close
- Position sizing: % of current cash (max_position_pct)
- Long-only, no shorting, no leverage

**Metrics Computed:**
- Total return %, Max drawdown %, Sharpe ratio
- Win rate %, Profit factor, Exposure %, Trade count
- Equity curve with drawdown

**Execution Model:** 
- Entry at next bar open
- Exit at next bar open (or stop-loss/take-profit on current bar close)
- FIFO position accounting

### 1.6 Backtesting API (`backend/app/routers/backtests.py`)

```python
POST /api/backtests  # Run backtest
GET /api/backtests/{rid}  # Get backtest results
```

**Current Flow:**
1. Load strategy by ID
2. Structural validation (no metrics) → fail fast
2. Fetch market data via `market.get_bars()`
3. Run backtest engine
4. Full validation with metrics → gate
5. Persist `BacktestRun` with metrics, equity curve, trades, validation result
6. Return results

### 1.6 Validation Gate (`backend/app/services/validation.py`)

**Structural Checks:**
- Instruments required
- Entry rules required
- Exit rules OR stop-loss required
- Rule references must reference valid indicators/price
- Position size > 50% → warning

**Metric-Based Checks (require metrics from backtest):**
- Minimum 5 trades
- Max drawdown ≤ risk.max_drawdown_pct

**Gate Result:** `{passed, errors[], warnings[]}`

**Used by:** Backtest API (pre-check + post-backtest), Paper trading deploy gate

---

### 1.6 Visual Strategy Builder (Frontend)

**Component:** `frontend/src/pages/Builder.jsx`

**Features:**
- Node palette (Market Data, Indicator, Condition, Entry, Exit, Risk)
- Drag-and-drop canvas with ReactFlow
- Node property editor panel
- Live JSON preview of canonical StrategySpec
- "Sync to strategy" → POST /api/strategies
- Loads draft from AI Studio chat

**Bidirectional Sync:**
- `fromSpec()` — StrategySpec → nodes/edges (load chat draft)
- `toSpec()` — Canvas → StrategySpec (on "Sync to strategy")

### 1.7 Backtest Frontend (`frontend/src/pages/Backtest.jsx`)

**Features:**
- Strategy selector (loads from `/api/strategies`)
- Run backtest button → POST `/api/backtests`
- Metrics display (return, DD, Sharpe, win rate, profit factor, exposure, trades)
- Validation gate display (pass/fail, errors, warnings)
- Equity curve chart (Recharts)
- Drawdown chart

### 1.8 Backtesting Service (`backend/app/services/backtest.py`)

**Engine Details:**
- Vectorized signals via pandas (no look-ahead: uses `.shift()` for crosses)
- Bar-by-bar simulation loop
- Entry at next bar open
- Exit at next bar open (or stop/target on current close)
- Stop-loss/take-profit checked on current bar close
- Position sizing: % of current cash
- Long-only, no shorting

**Metrics:**
- Total return, Max DD, Sharpe, Win rate, Profit factor, Exposure, Trades
- Equity curve with drawdown
- Trade log with entry/exit price, PnL, return, reason, timestamp

---

## 2. Current Test Coverage

### Backend Tests (`backend/tests/`)
| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_schemas.py` | 35 | StrategySpec, IndicatorSpec, Rule, RiskLimits, DTOs |
| `test_indicators.py` | 23 | SMA, EMA, RSI, MACD, BBANDS, compute() |
| `test_backtest.py` | 54 | eval_rule, signals, run(), edge cases |
| `test_nlp.py` | 29 | Rule-based parser for chat |
| `test_validation.py` | 44 | Structural + metric validation |
| `test_market.py` | 30 | Mock data, get_bars, watchlist |
| `test_research.py` | 14 | Multi-agent research |
| `test_paper.py` | 10 | Paper trading engine |
| `test_validation.py` | 44 | Validation gate |
| `test_import_market_data.py` | 31 | CSV import CLI |

**Total: 251 tests passing (1 skipped)**

### Frontend Tests
- `DataQualityPanel.test.jsx`: 8 tests
- `pages.test.jsx`: 8 tests (component rendering)
- Total: 16 tests passing

---

## 3. Gap Analysis

### 3.1 What Already Works Well ✅
1. **Canonical StrategySpec v1.0** — Single source of truth across all modules
2. **Visual Builder** — Functional ReactFlow-based editor with bidirectional sync
3. **AI Chat Studio** — Rule-based parser generates StrategySpec from natural language
4. **Validation Gate** — Structural + metric-based validation gate
4. **Backtest Engine** — Deterministic, vectorized, no look-ahead
5. **Backtest API** — Structural pre-check → data fetch → backtest → validation → persist
6. **Visual Builder** — Full ReactFlow editor with sync to canonical spec
6. **Backtest UI** — Strategy picker, run, metrics, charts, validation display
7. **Schema Versioning** — Strategy versioning on save (same name = new version)
8. **Backtest Persistence** — Full BacktestRun record with metrics, trades, equity curve

### 3.2 Gaps Identified ❌

| Gap | Severity | Description |
|-----|----------|-------------|
| **Backtest API missing config options** | High | No support for custom date range, transaction costs, slippage, initial cash per-run |
| **Strategy validation incomplete** | High | Missing: indicator parameter validation, timeframe-instrument compatibility, holding period, data availability check |
| **Backtest API missing config** | High | `BacktestIn` only has `strategy_id`, `bars`, `initial_cash` — no date range, costs, slippage |
| **Strategy version immutability** | Medium | BacktestRun stores `strategy_version` but no immutability enforcement |
| **Frontend Backtest page** | Medium | No date range picker, no cost/slippage inputs, no loading/error states for backtest submission |
| **Strategy validation gaps** | Medium | No validation of: indicator parameters, timeframe support, instrument support, max holding period, data availability |
| **Backtest result schema** | Medium | Missing transaction costs, slippage in persisted results |
| **Strategy version immutability** | Medium | Strategy spec mutable — backtest should reference immutable version |
| **Frontend Backtest UX** | Medium | No loading states during backtest, no progress, no error detail beyond validation |
| **Data availability check** | High | No verification that sufficient historical data exists for strategy/timeframe |
| **Transaction costs/slippage** | High | Not modeled in backtest engine or API |

---

## 4. Recommendations

### Phase 4 Priority Actions

1. **Extend BacktestIn schema** — Add date range, initial_cash (already there), transaction_cost_bps, slippage_bps
2. **Enhance StrategySpec validation** — Add indicator param validation, timeframe checks, instrument support
3. **Extend BacktestIn/BacktestRun** — Add transaction_cost_bps, slippage_bps, date range
4. **Update backtest engine** — Add transaction costs, slippage to execution model
5. **Update BacktestRun model** — Store config used (costs, slippage, date range)
6. **Update frontend Backtest page** — Add date picker, cost/slippage inputs, loading states
7. **Strategy version immutability** — Store strategy spec snapshot in BacktestRun
8. **Add data availability check** — Verify sufficient data before backtest

---

## 5. Audit Summary

**Current State:** Functional MVP with solid foundation. Canonical StrategySpec v1.0 is the single source of truth across chat, builder, backtester, and paper engine. Validation gate exists but needs enhancement. Backtest engine works but lacks transaction costs, slippage, and configurable date ranges.

**Priority for Phase 4:**
1. Extend BacktestIn/BacktestRun schemas with date range, costs, slippage
2. Enhance validation with data availability, indicator params, instrument support
3. Update backtest engine for transaction costs/slippage
4. Frontend: date range picker, cost inputs, loading states
9. Strategy version immutability in backtest results
10. Comprehensive test coverage for new features

**Estimated Effort:** Medium — Builds on solid existing foundation