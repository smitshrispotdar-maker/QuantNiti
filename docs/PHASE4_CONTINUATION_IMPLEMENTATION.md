# Phase 4 Continuation Implementation

## Files Modified

### Backend

#### 1. `backend/app/services/validation.py`
**Enhanced validation gate with comprehensive checks:**

```python
# New constants
SUPPORTED_INSTRUMENTS = {...}
SUPPORTED_TIMEFRAMES = {...}
INDICATOR_PARAM_SPECS = {...}
INDICATOR_MIN_BARS = {...}
TIMEFRAME_MIN_BARS = {...}

# New validation functions
def _validate_indicator_params(indicator: IndicatorSpec) -> list[str]
def _validate_fast_slow_relationships(spec: StrategySpec) -> list[str]
def _validate_date_range(start_date, end_date) -> list[str]
def _check_data_availability(spec, bars_count) -> list[str]

# Enhanced validate() signature
def validate(spec, metrics=None, bars_count=None, start_date=None, end_date=None)
```

**Validation rules implemented:**
- Instrument/timeframe support matrix
- Indicator type and parameter range validation
- Unknown parameter detection
- Risk limit bounds (stop_loss ≤ 50%, take_profit ≤ 500%, max_dd ≤ 100%)
- Date range validation (ISO format, start < end)
- Data sufficiency checks (timeframe minimums + indicator initialization requirements)
- Multi-instrument rejection

#### 2. `backend/app/routers/backtests.py`
**Updated to use enhanced validation:**

```python
pre = validation.validate(
    spec,
    {"trades": 99, "max_drawdown_pct": 0},
    bars_count=body.bars,
    start_date=body.start_date,
    end_date=body.end_date
)
structural = [e for e in pre["errors"] 
              if "backtest" not in e.lower() 
              and "run a backtest" not in e.lower()]
```

#### 3. `backend/tests/test_validation.py` (+15 new tests)
**Enhanced validation test coverage:**
- `test_invalid_indicator_type_rejected` - Schema-level check
- `test_indicator_param_out_of_range_rejected` - Custom validation
- `test_indicator_unknown_param_rejected` - Unknown parameter detection
- `test_unsupported_instrument_rejected` - Instrument allowlist
- `test_unsupported_timeframe_rejected` - Schema-level check
- `test_invalid_stop_loss_range_rejected` - Schema-level check
- `test_invalid_take_profit_range_rejected` - Schema-level check
- `test_invalid_max_drawdown_range_rejected` - Schema-level check
- `test_invalid_date_range_rejected` - Custom validation
- `test_valid_date_range_accepted` - Happy path
- `test_insufficient_bars_for_timeframe_rejected` - Timeframe minimums
- `test_insufficient_bars_for_indicator_rejected` - Indicator initialization
- `test_sufficient_bars_for_indicator_accepted` - Happy path
- `test_macd_insufficient_bars_rejected` - MACD specific
- `test_multi_instrument_rejected` - Single-instrument constraint

#### 4. `backend/tests/test_backtest.py` (+10 new tests)
**Transaction cost & slippage tests:**
- `test_transaction_cost_zero_no_effect` - Zero cost baseline
- `test_transaction_cost_reduces_returns` - Cost impact
- `test_slippage_reduces_returns` - Slippage impact
- `test_cost_applied_on_both_buy_and_sell` - Round-trip cost
- `test_slippage_buy_higher_sell_lower` - Slippage direction
- `test_cost_and_slippage_combined` - Combined effect

**Snapshot immutability tests:**
- `test_backtest_run_stores_strategy_spec_snapshot` - Snapshot stored
- `test_snapshot_preserved_after_strategy_edit` - Version isolation

### Frontend

#### 5. `frontend/src/pages/Backtest.jsx` (NEW)
**Complete Backtest page implementation:**

```jsx
// Configuration state
const [initialCash, setInitialCash] = useState(100000)
const [transactionCostBps, setTransactionCostBps] = useState(0)
const [slippageBps, setSlippageBps] = useState(0)
const [startDate, setStartDate] = useState("")
const [endDate, setEndDate] = useState("")

// Form validation
const validateForm = () => {
  if (!sid) return "Please select a strategy"
  if (initialCash <= 0) return "Initial capital must be positive"
  if (transactionCostBps < 0 || transactionCostBps > 10000) 
    return "Transaction costs must be between 0 and 10000 bps"
  if (slippageBps < 0 || slippageBps > 10000) 
    return "Slippage must be between 0 and 10000 bps"
  if (startDate && endDate && new Date(startDate) >= new Date(endDate)) 
    return "Start date must be before end date"
  return null
}

// Submission with loading state
const run = async () => {
  const validationError = validateForm()
  if (validationError) { setErr(...); return }
  setLoading(true)
  try {
    const result = await api("/api/backtests", { method: "POST", body: {...} })
    setR(result)
  } catch (e) { setErr(e) }
  finally { setLoading(false) }
}
```

**UI Components:**
- Strategy selector dropdown
- Configuration panel (4-column grid):
  - Initial Capital, Transaction Cost (bps), Slippage (bps), Bars
  - Start Date, End Date (date pickers)
- Loading state on button
- ErrorBox for validation/execution errors

**Results Display:**
- Strategy info banner (name, version, timeframe, data source/status)
- Configuration summary (capital, costs, slippage, date range, data source)
- Validation gate status (passed/failed with errors/warnings)
- 7-metric grid (return, drawdown, Sharpe, win rate, profit factor, exposure, trades)
- Collapsible strategy spec snapshot (JSON)
- Equity curve + drawdown area charts
- Trade log table (time, side, entry, exit, PnL, return, reason)

#### 6. `frontend/src/__tests__/pages.test.jsx` (UPDATED)
**Added Backtest page tests:**
- Renders without crashing
- Verifies all configuration UI elements present
- Checks for "Run backtest" buttons (multiple allowed)

## Cost & Slippage Formulas

### Basis Points Definition
- 1 bp = 0.01% = 0.0001 multiplier
- 100 bps = 1% = 0.01 multiplier

### Buy Execution Price
```
next_open = bars[i+1].open
buy_price = next_open * (1 + slippage_bps/10000) * (1 + transaction_cost_bps/10000)
```

### Sell Execution Price
```
sell_price = next_open * (1 - slippage_bps/10000) * (1 - transaction_cost_bps/10000)
```

### PnL Calculation
```
qty = (cash * max_position_pct / 100) / buy_price
cash -= qty * buy_price  // on entry
cash += qty * sell_price // on exit
pnl = qty * (sell_price - buy_price)
ret = sell_price / buy_price - 1
```

### Verified Properties
1. **Zero cost identity**: `cost=0, slip=0` → same as no-cost path
2. **Cost monotonicity**: Higher costs → lower returns (when trades > 0)
3. **Round-trip application**: Cost applied once on buy, once on sell
4. **Slippage direction**: Buy higher, sell lower
5. **Commutative combination**: cost + slip = combined effect

## Snapshot Immutability Implementation

### Storage Location
- `BacktestRun.strategy_spec` (JSONB column) - complete StrategySpec at run time
- `BacktestRun.strategy_version` - integer version from Strategy table
- `BacktestRun.transaction_cost_bps`, `slippage_bps`, `initial_cash`, `start_date`, `end_date` - run configuration

### Router Logic (backend/app/routers/backtests.py:26-40)
```python
r = BacktestRun(
    strategy_id=s.id,
    strategy_version=s.version,
    strategy_spec=s.spec,  # SNAPSHOT - immutable copy
    initial_cash=body.initial_cash,
    transaction_cost_bps=body.transaction_cost_bps,
    slippage_bps=body.slippage_bps,
    start_date=body.start_date,
    end_date=body.end_date,
    metrics=metrics,
    equity_curve=curve,
    trades=trades,
    validation=gate,
    data_source=meta["source"]
)
```

### Version Isolation
- Strategy edits increment `Strategy.version`
- New backtests get new `strategy_version` reference
- Old `BacktestRun.strategy_spec` unchanged
- GET `/api/backtests/{rid}` returns snapshot from `r.strategy_spec`

## Test Results Summary

### Backend (274 tests)
```
tests/test_validation.py          41 passed
tests/test_backtest.py            33 passed
tests/test_schemas.py             12 passed
tests/test_indicators.py          25 passed
tests/test_market.py              27 passed
tests/test_paper.py               22 passed
tests/test_nlp.py                 18 passed
tests/test_research.py            15 passed
tests/test_import_market_data.py  81 passed (1 skipped)
Total: 274 passed, 1 skipped
```

### Frontend (16 tests)
```
src/__tests__/DataQualityPanel.test.jsx  8 passed
src/__tests__/pages.test.jsx             8 passed
Total: 16 passed
```

### Production Build
```
✓ built in 2.63s
dist/index.html                   0.44 kB
dist/assets/index-*.css           18.40 kB
dist/assets/index-*.js            709.74 kB
```

## Verification Checklist

- [x] Enhanced validation: indicator params, timeframe support, data availability
- [x] Frontend Backtest page: date pickers, cost/slippage inputs, loading states
- [x] Transaction cost calculations verified with deterministic tests
- [x] Slippage calculations verified (buy higher, sell lower)
- [x] Strategy snapshot immutability enforced and tested
- [x] All backend tests pass (274)
- [x] All frontend tests pass (16)
- [x] Production build succeeds
- [x] No database migrations required
- [x] Documentation created