# Paper Trading Audit - Phase 5

## Existing Implementation Summary

### Backend Models (`backend/app/models.py`)
- **PaperAccount**: id, name, starting_cash, cash, status (RUNNING/PAUSED/STOPPED/KILLED), strategy_id (FK), created_at
- **PaperOrder**: id, account_id, symbol, side, qty, fill_price, reason, label, ts
- **BacktestRun**: Already has strategy_spec snapshot, transaction_cost_bps, slippage_bps, initial_cash, start_date, end_date

### Backend Router (`backend/app/routers/paper.py`)
**Endpoints:**
- `GET /api/paper/accounts` - List accounts with computed state
- `POST /api/paper/accounts` - Create account
- `GET /api/paper/accounts/{aid}` - Get account state + recent orders
- `POST /api/paper/accounts/{aid}/orders` - Manual order placement
- `POST /api/paper/accounts/{aid}/control/{action}` - pause/resume/stop/kill
- `POST /api/paper/accounts/{aid}/deploy` - Deploy strategy (validates backtest passes)
- `POST /api/paper/accounts/{aid}/step` - Evaluate strategy on latest bar, place order if signal

**Core Functions:**
- `_state(db, account)` - Computes positions, unrealized/realized P&L, equity from order history
- `_fill(db, account, symbol, side, qty, reason)` - Simulates order fill at latest close price
- `deploy()` - Validates strategy has passing backtest, stores strategy_id on account
- `step()` - Evaluates strategy signals on latest bar, auto-places BUY/SELL

### Frontend (`frontend/src/pages/Paper.jsx`)
- Account creation/selection sidebar
- Strategy deployment dropdown + Deploy button
- Manual order form (symbol, side, qty)
- Step evaluation button
- Control buttons (pause/resume/stop/kill)
- Portfolio summary (cash, equity, P&L, status)
- Positions table (qty, avg price, last, unrealized, realized)
- Order history with labels

### Tests (`backend/tests/test_paper.py`) - 15 tests
- Account state computation (empty, buy, buy+sell, multi-symbol)
- Fill function (buy/sell, insufficient cash, no shorting, account status)
- Deploy validation (requires passing backtest, fails validation)
- Step evaluation (no strategy, buy signal, sell signal, hold)
- Control actions (pause, resume, stop, kill, kill irreversible, invalid action)

## Gaps for Phase 5 Completion

### 1. Missing Persistent Deployment Model
- No `PaperDeployment` table capturing immutable activation configuration
- Current `deploy` only stores `strategy_id` on account - no snapshot
- Strategy edits would affect existing deployments
- Missing: transaction_cost_bps, slippage_bps, initial_cash, risk limits, activation timestamp per deployment

### 2. Execution Model Mismatch with Backtest
- **Backtest**: Fills at next bar OPEN with slippage + transaction costs
- **Paper**: Fills at latest bar CLOSE with NO costs/slippage
- **Stop loss / take profit**: Backtest handles intra-bar; Paper doesn't
- **Look-ahead**: Paper uses current close (known price) vs next open (future price)

### 3. Missing Risk Controls
- No data freshness check before execution
- No idempotency for step endpoint (duplicate calls = duplicate orders)
- No stale-data handling policy
- No verification that incoming bar hasn't been processed

### 4. Missing Portfolio Analytics
- No max drawdown tracking
- No win rate, profit factor for paper trades
- No exposure tracking
- No trade history with entry/exit details

### 5. Frontend Gaps
- No display of execution assumptions (costs, slippage)
- No deployment history view
- No execution warnings/stale data indicators
- No trade log with P&L details
- Missing "PAPER TRADING ONLY" prominent notice

## Recommended Implementation Plan

1. **Add PaperDeployment model** with strategy_spec snapshot + all execution config
2. **Update deploy endpoint** to create deployment record with snapshot
3. **Create paper execution service** matching backtest logic (next-open, costs, slippage, SL/TP)
4. **Add idempotency keys** to step endpoint
5. **Add data freshness validation** before execution
6. **Extend position tracking** with entry prices, SL/TP levels
7. **Add portfolio metrics** computation
8. **Enhance frontend** with deployment management, execution settings, trade log
9. **Add comprehensive tests** for all new functionality
10. **Create documentation**