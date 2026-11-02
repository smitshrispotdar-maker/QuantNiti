# Paper Trading Implementation - Phase 5

## Summary

Extended the QuantNiti platform with a complete paper trading system that integrates validated strategies, backtest infrastructure, and simulated execution with proper risk controls.

## Files Modified

### Backend

#### 1. `backend/app/models.py` - New Models
- **PaperDeployment**: Immutable deployment record with strategy_spec snapshot, execution config, status tracking, idempotency
- **PaperPosition**: Per-deployment position tracking with avg entry, unrealized/realized P&L, SL/TP prices
- **PaperTrade**: Completed trade records with entry/exit prices, P&L, fees, slippage, reason

#### 2. `backend/app/services/paper.py` - New Execution Service
Complete paper trading engine matching backtest execution model:
- **Signal evaluation** on closed bars (no look-ahead)
- **Next-bar-open execution** with slippage + transaction costs
- **Stop loss / take profit** checked intra-bar on HIGH/LOW
- **Position sizing** matching backtest (max_position_pct of cash)
- **Cash accounting** with fees and slippage
- **Idempotency** via last_processed_bar_ts
- **Data freshness validation** before execution

Key functions:
- `evaluate_strategy_step(db, deployment, force)` - Main step evaluation
- `place_manual_order(db, deployment_id, symbol, side, qty, reason)` - Manual orders
- `get_deployment_state(db, deployment)` - Complete state with metrics
- `close_deployment(db, deployment_id)` - Liquidation and closure

#### 3. `backend/app/routers/paper.py` - Enhanced API
**Legacy Endpoints (backwards compatible):**
- `POST /api/paper/accounts` - Create account
- `GET /api/paper/accounts` - List accounts with state
- `GET /api/paper/accounts/{aid}` - Account details + orders
- `POST /api/paper/accounts/{aid}/orders` - Manual orders
- `POST /api/paper/accounts/{aid}/control/{action}` - pause/resume/stop/kill
- `POST /api/paper/accounts/{aid}/deploy` - Legacy deploy (creates deployment)
- `POST /api/paper/accounts/{aid}/step` - Legacy step (uses active deployment)

**New Deployment Endpoints:**
- `POST /api/paper/accounts/{aid}/deployments` - Create deployment with full config
- `GET /api/paper/deployments/{did}` - Full deployment state
- `GET /api/paper/accounts/{aid}/deployments` - List account deployments
- `POST /api/paper/deployments/{did}/step` - Execute strategy step
- `POST /api/paper/deployments/{did}/control/{action}` - pause/resume/stop/close
- `POST /api/paper/deployments/{did}/orders` - Manual order within deployment
- `GET /api/paper/deployments/{did}/trades` - Trade history

#### 4. `backend/tests/test_paper.py` - Enhanced Tests (+6 new tests)
- `TestDeployValidation.test_deploy_requires_passing_backtest`
- `TestDeployValidation.test_deploy_fails_validation`
- `TestStepEvaluation.test_step_no_strategy_deployed` (updated)
- `TestStepEvaluation.test_step_generates_buy_signal` (updated)
- `TestStepEvaluation.test_step_generates_sell_signal` (updated)
- `TestStepEvaluation.test_step_hold_no_signal` (updated)

Total backend tests: **274 passed**

### Frontend

#### 5. `frontend/src/pages/Paper.jsx` - Complete Rewrite
**New Features:**
- **Deployment Management**: Create, view, pause/resume/stop/close deployments
- **Configuration Form**: Strategy selection, initial capital, tx costs, slippage
- **Tabbed Interface**: Overview, Trades, Settings
- **Portfolio Dashboard**: Cash, equity, P&L, metrics (DD, win rate, PF, trades)
- **Positions Table**: Qty, avg entry, current, unrealized/realized, SL/TP
- **Trade History**: Full trade log with P&L, fees, slippage, reason
- **Strategy Snapshot Viewer**: Immutable strategy spec at deployment
- **Manual Orders**: Symbol, side, qty with validation
- **Prominent "PAPER TRADING ONLY" Notice**
- **Loading/Error/Empty States**

Total frontend tests: **16 passed**, Build: **Success**

## Execution Model (Matches Backtest)

```
Signal Evaluation:    On CLOSED bars only (index -2 for last closed bar)
Order Fill Price:     NEXT bar OPEN (index -1 open)
Slippage:             BUY higher (×1+slippage_bps/10000), SELL lower (×1-slippage_bps/10000)
Transaction Cost:     Applied on BOTH entry and exit
Stop Loss:            Checked on current bar LOW ≤ stop_price
Take Profit:          Checked on current bar HIGH ≥ limit_price
Position Sizing:      max_position_pct of available cash / fill_price
```

## Risk Controls Implemented

1. **Deployment Validation**: Requires passing backtest (same version)
2. **Immutable Snapshot**: Strategy spec + execution config frozen at deploy
3. **Account Status Check**: Only RUNNING accounts can deploy/step
4. **Active Deployment Check**: One active deployment per account
5. **Data Freshness Check**: Rejects stale market data (>1hr default)
6. **Idempotency**: last_processed_bar_ts prevents duplicate step execution
7. **Cash Validation**: Insufficient cash blocks BUY orders
8. **Position Limits**: No short selling, max_position_pct enforced
9. **Status Gates**: pause/resume/stop/close only valid from correct states
10. **Kill Switch**: Irreversible KILLED state

## Portfolio Accounting

- **Cash**: Updated on every fill (cash -= buy_cost, cash += sell_proceeds)
- **Positions**: Tracked per deployment with avg_entry_price (FIFO)
- **Unrealized P&L**: qty × (current_price - avg_entry_price)
- **Realized P&L**: Accumulated on SELL fills (FIFO cost basis)
- **Equity**: cash + Σ(position_qty × current_price)
- **Total Return**: (equity - initial_cash) / initial_cash × 100
- **Max Drawdown**: Peak-to-trough from equity curve
- **Win Rate**: winning_trades / total_trades
- **Profit Factor**: gross_profit / gross_loss
- **Fees**: qty × |fill_price - raw_price| (approximation)
- **Slippage**: qty × |raw_price - slippage_price|

## Database Migrations

No migrations required for this implementation. Models are additive and compatible with existing schema.

## Test Results Summary

| Suite | Tests | Status |
|-------|-------|--------|
| Backend Unit | 274 | ✅ Passed |
| Frontend Unit | 16 | ✅ Passed |
| Frontend Build | - | ✅ Success |

## Limitations & Future Work

1. **Single Instrument**: One deployment = one symbol
2. **Long Only**: No short selling support
3. **No Walk-Forward**: Single deployment per strategy version
4. **No Parameter Optimization**: Manual config only
5. **Mock Data Only**: No live broker integration
6. **No WebSocket**: Polling-based step execution
7. **Single User**: No multi-tenancy/auth

## Next Recommended Phase

**Phase 6: Live Trading Preparation**
- Multi-user authentication & authorization
- Broker API abstraction layer
- Order routing & execution management
- Real-time market data (WebSocket)
- Compliance & audit logging
- Risk dashboard with alerts
- Strategy versioning & rollback