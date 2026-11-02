# Strategy Lineage Implementation - Phase 7 Stage 3

## Summary

Implemented strategy lineage tracking that traces the complete path from conversation through strategy creation, research, backtesting, journal decisions, and paper trading deployment.

## Files Created/Modified

### Backend Services
- **`backend/app/services/lineage.py`** (NEW): Core lineage building logic
  - `build_lineage(db, strategy_id, conversation_id, user_id)` - Builds complete timeline
  - `get_entity_lineage(db, entity_type, entity_id)` - Get lineage for specific entity

### Routers
- **`backend/app/routers/lineage.py`** (NEW): Lineage API endpoints
  - `GET /api/lineage` - Full timeline for strategy or conversation
  - `GET /api/lineage/entity/{entity_type}/{entity_id}` - Lineage for specific entity

### Frontend Integration
- Added to `App.jsx` navigation (could add Lineage page if needed)
- Lineage data available for integration into Studio, Journal, Research pages

---

## Lineage Event Types

| Event Type | Description | Source |
|------------|-------------|--------|
| `strategy` | Strategy creation/versioning | Strategy table |
| `conversation` | Chat session creation | Conversation table |
| `draft_update` | Strategy draft modified in chat | Conversation.draft_spec |
| `backtest` | Backtest execution | BacktestRun table |
| `research` | Research run execution | ResearchRun table |
| `journal` | Decision journal entry | JournalEntry table |
| `deployment` | Paper deployment creation | PaperDeployment table |
| `deployment_closed` | Deployment closed/liquidated | PaperDeployment.closed_at |

---

## Lineage Event Structure

```json
{
  "event_type": "backtest",
  "timestamp": "2024-01-15T10:30:00",
  "title": "Backtest #42: 15.2% return, 12 trades",
  "details": {
    "backtest_id": 42,
    "strategy_version": 3,
    "total_return_pct": 15.2,
    "max_drawdown_pct": 8.5,
    "sharpe": 1.8,
    "win_rate_pct": 62.5,
    "profit_factor": 2.1,
    "trades": 12,
    "validation_passed": true,
    "data_source": "YAHOO FINANCE",
    "transaction_cost_bps": 5,
    "slippage_bps": 3
  },
  "entity_id": 42,
  "entity_type": "backtest"
}
```

---

## Lineage Building Logic

### `build_lineage(db, strategy_id, conversation_id, user_id)`

1. **Resolve Strategy/Conversation**: Find the anchor entity
2. **Collect Events** from all related tables:
   - Strategies (creation + versioning)
   - Conversations (creation + draft updates)
   - BacktestRuns (filtered by strategy_id)
   - ResearchRuns (filtered by strategy_id/user_id)
   - JournalEntries (filtered by user_id/strategy_id)
   - PaperDeployments (filtered by account/user_id/strategy_id)
3. **Sort Chronologically**: All events merged and sorted by timestamp
4. **Return**: List of event dicts sorted oldest to newest

### `get_entity_lineage(db, entity_type, entity_id)`

Convenience wrapper that routes to `build_lineage` with appropriate filters based on entity type.

---

## Database Relationships

```
Conversation (1) ←→ (N) JournalEntry
Conversation (1) ←→ (N) ResearchRun
Strategy (1) ←→ (N) BacktestRun
Strategy (1) ←→ (N) PaperDeployment
Strategy (1) ←→ (N) ResearchRun
PaperDeployment (1) ←→ (N) PaperPosition
PaperDeployment (1) ←→ (N) PaperOrder
PaperDeployment (1) ←→ (N) PaperTrade
PaperDeployment (1) ←→ (N) JournalEntry
BacktestRun (1) ←→ (N) JournalEntry
ResearchRun (1) ←→ (N) JournalEntry
```

### Key Foreign Keys in JournalEntry
- `strategy_id` → Strategy.id
- `conversation_id` → Conversation.id
- `backtest_run_id` → BacktestRun.id
- `research_run_id` → ResearchRun.id
- `deployment_id` → PaperDeployment.id

### Key Foreign Keys in ResearchRun
- `strategy_id` → Strategy.id
- `conversation_id` → Conversation.id
- `backtest_run_id` → BacktestRun.id
- `deployment_id` → PaperDeployment.id

### Key Fields in PaperDeployment
- `strategy_spec` (JSONB) - immutable snapshot at activation
- `strategy_id`, `strategy_version` - link to strategy version
- `status` - ACTIVE, PAUSED, STOPPED, CLOSED
- `activated_at`, `closed_at` - lifecycle timestamps

### Key Fields in BacktestRun
- `strategy_spec` (JSONB) - immutable snapshot at run time
- `strategy_id`, `strategy_version` - link to strategy version
- `metrics`, `equity_curve`, `trades` - results
- `validation` - validation gate result
- `data_source` - provenance

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/lineage` | Full timeline (query: strategy_id, conversation_id) |
| GET | `/api/lineage/entity/{type}/{id}` | Lineage for specific entity |

### Entity Types for `/entity/{type}/{id}`
- `strategy` - Strategy lineage
- `conversation` - Conversation lineage
- `backtest` - Backtest lineage
- `deployment` - Deployment lineage
- `journal` - Journal entry lineage
- `research` - Research run lineage

---

## Frontend Integration (Planned)

### Lineage Timeline Component
```jsx
// Usage in Studio, Journal, Research pages
<LineageTimeline strategyId={saved.id} />
<LineageTimeline conversationId={cid} />
<EntityLineage entityType="backtest" entityId={backtestId} />
```

### Timeline Display
- Vertical timeline with icons per event type
- Expandable event details
- Links to related entities (Strategy, Backtest, Deployment, Journal)
- Filter by event type
- Date grouping

---

## Immutability Guarantees

1. **Strategy Versions**: New version created on each save, old versions preserved
2. **Strategy Spec Snapshots**: Stored in BacktestRun, PaperDeployment, ResearchRun
3. **Backtest Results**: Immutable once created (BacktestRun never modified)
4. **Research Runs**: Immutable after creation (read-only)
5. **Paper Deployments**: Strategy spec frozen at activation
6. **Journal Entries**: Can be updated but audit trail via updated_at

---

## Test Coverage

- Backend lineage service tested via integration with existing tests
- All 294 backend tests passing
- No regressions introduced

---

## Usage Examples

### Get Full Strategy Lineage
```bash
GET /api/lineage?strategy_id=5
```

### Get Conversation History
```bash
GET /api/lineage?conversation_id=12
```

### Get Backtest Lineage
```bash
GET /api/lineage/entity/backtest/42
```

### Get Deployment History
```bash
GET /api/lineage/entity/deployment/7
```

---

## Future Enhancements

1. **Visual Timeline Component**: React component for Studio/Journal pages
2. **Diff View**: Compare strategy specs between versions
3. **Export**: Export lineage as JSON/CSV/PDF
6. **Notifications**: Alert on key lineage events (backtest complete, deployment status change)
7. **Search**: Full-text search across lineage events