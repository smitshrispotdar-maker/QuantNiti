# Phase 10 Changelog

## Stage 1A: Research Snapshot Persistence Fix

### Date
2026-11-03

### Commit
`3793d56` (after Phase 10 Production Audit)

### Original Bug

The research `create_run` endpoint in `backend/app/routers/research.py` had a critical bug where computed strategy and backtest snapshots were not being persisted to the database.

**Root Cause:** In the `create_run` function (lines 137-153), the code correctly computed the strategy specification and backtest metrics snapshots by fetching from linked objects (lines 97-107). However, when creating the `ResearchRun` database record (lines 145-146), it incorrectly used the request body values (`body.strategy_spec_snapshot` and `body.backtest_metrics_snapshot`) instead of the computed variables (`strategy_spec` and `backtest_metrics`).

This caused:
1. Strategy specification snapshots to be `null` when not explicitly provided in the request body
2. Backtest metrics snapshots to be `null` when not explicitly provided in the request body
3. Research records to lose the actual strategy specification and backtest metrics associated with the research execution

### Fix Implemented

**File Modified:** `backend/app/routers/research.py`

**Change:** Lines 145-146 in the `create_run` function

**Before:**
```python
strategy_spec_snapshot=body.strategy_spec_snapshot,
backtest_metrics_snapshot=body.backtest_metrics_snapshot,
```

**After:**
```python
strategy_spec_snapshot=strategy_spec,
backtest_metrics_snapshot=backtest_metrics,
```

### Behavior Changes

**Before Fix:**
- Research runs created without explicit snapshots in the request body would have `null` snapshots
- Snapshots only persisted if explicitly provided in the request body
- Editing the original strategy could affect research snapshots (if snapshots were provided)

**After Fix:**
- Research runs automatically persist computed snapshots from linked strategy and backtest
- Strategy specification snapshot captures the strategy state at research execution time
- Backtest metrics snapshot captures the backtest results at research execution time
- Snapshots are immutable - editing the original strategy does not change existing research snapshots
- Missing strategy/backtest references are handled gracefully (snapshot remains `null` if not available)

### Testing

All existing tests pass:
- Backend: 294 passed, 1 skipped
- Frontend: 16 passed
- Production build: Successful

Manual verification confirmed:
1. ✅ Strategy snapshot correctly persisted when strategy_id provided
2. ✅ Backtest snapshot correctly persisted when backtest_run_id provided
3. ✅ Both snapshots persisted together when both references provided
4. ✅ Missing strategy handled correctly (snapshot remains null)
5. ✅ Missing backtest handled correctly (snapshot remains null)
6. ✅ Editing original strategy does not change existing snapshot (immutability)
7. ✅ Research retrieval returns persisted snapshots
8. ✅ Existing research functionality continues working

### Files Modified

- `backend/app/routers/research.py` - Fixed snapshot persistence in `create_run` function

### Remaining Limitations

1. **PaperAccount still lacks user_id column** - Still needs migration for proper ownership
2. **Hardcoded user_id=1** - Still present in 20+ locations across routers
3. **Research comparison creates persistent ResearchRun** - Should use separate table
4. **No authentication system** - Still using hardcoded user_id=1
4. **Strategy/Backtest snapshots not populated in `create_from_chat`** - Similar bug exists in the chat-triggered research creation endpoint

### Next Steps (Stage 1B)

1. Fix similar bug in `create_from_chat` endpoint
2. Add user_id column to PaperAccount model (new migration)
4. Begin implementing authentication system to replace hardcoded user_id=1
5. Add database indexes for foreign key columns