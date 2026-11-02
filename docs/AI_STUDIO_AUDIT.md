# AI Studio Audit - Phase 6

## Existing Implementation Summary

### Backend Models (`backend/app/models.py`)
- **Conversation**: `id`, `user_id`, `messages` (JSONB), `draft_spec` (JSONB), `updated_at`
- **Strategy**: `id`, `user_id`, `name`, `version`, `spec` (JSONB), `created_at`
- **BacktestRun**: Full backtest results with strategy_spec snapshot
- **PaperDeployment**: Full paper trading deployments with strategy_spec snapshot

### NLP Service (`backend/app/services/nlp.py`)
- **Rule-based parser**: Converts natural language → StrategySpec
- **Supported patterns**:
  - Instruments: BTC, ETH, AAPL, SPY (with aliases)
  - Timeframes: 1m, 5m, 15m, 1h, 1d
  - Indicators: EMA/SMA crossovers, RSI thresholds
  - Risk: stop_loss, take_profit, position_size
  - Clarifications for missing/ambiguous info
- **Conversation continuation**: Accepts base StrategySpec for incremental building
- **No LLM required**: Pure rule-based, deterministic

### Chat Router (`backend/app/routers/strategies.py`)
- `GET /api/strategies` - List saved strategies
- `POST /api/strategies` - Save strategy (with versioning)
- `GET /api/strategies/{sid}` - Get strategy
- `GET /api/strategies/chat/{cid}` - Get conversation history
- `POST /api/strategies/chat` - Send message, get updated draft

### Frontend Studio (`frontend/src/pages/Studio.jsx`)
- Chat interface with message history
- Draft strategy JSON display
- Save button to persist strategy
- Basic error handling

### Tests (`backend/tests/test_nlp.py`)
- 32 comprehensive tests for NLP parser
- All parsing patterns, edge cases, clarifications

### Research Service (`backend/app/services/research.py`)
- Multi-agent deterministic interpretations
- Facts + templated agent views (market, quant, risk, strategy manager)

---

## Gaps for Phase 6 Completion

### 1. Conversation Management (Missing)
- **No listing**: `GET /api/strategies/conversations` missing
- **No deletion**: `DELETE /api/strategies/conversations/{cid}` missing
- **No renaming**: No endpoint to rename conversations
- **Frontend**: No conversation list UI, no load/delete/rename controls

### 2. Backtest Integration from Chat (Missing)
- No "Run Backtest" action from chat
- No automatic backtest submission from draft spec
- No backtest result retrieval/explanation in chat
- No backtest ID reference in conversation

### 3. Paper Trading Integration from Chat (Missing)
- No "Deploy to Paper" action from chat
- No explicit approval flow in chat
- No deployment status tracking in conversation

### 4. LLM Integration (Missing)
- Only rule-based parser exists (nlp.py)
- No actual LLM integration for complex queries
- No local model support (Ollama, etc.)
- No fallback behavior documentation

### 5. Strategy Version Tracking in Conversation (Missing)
- Conversation draft_spec doesn't track strategy_id/version
- No link between conversation and saved strategy version
- No preservation of earlier versions when editing

### 6. Frontend Conversation Management (Missing)
- No conversation list sidebar
- No load previous conversation
- No delete conversation
- No rename conversation
- No new conversation button (only implicit via new tab)

### 6. Conversation-to-Backtest/Deployment References (Missing)
- Conversation doesn't store backtest_ids
- Conversation doesn't store deployment_ids
- No history of "ran backtest X" or "deployed Y" in conversation

---

## Implementation Plan

1. **Extend Conversation Router**: Add list, delete, rename endpoints
2. **Extend Chat Endpoint**: Add actions for backtest, paper deploy
3. **Enhance NLP Service**: Add structured action detection (backtest, deploy, explain)
4. **Update Frontend Studio**: Add conversation list, load/delete/rename, action buttons
4. **Add Tests**: Conversation CRUD, chat actions, backtest integration
5. **Document**: AI_STUDIO_AUDIT.md, AI_STUDIO_IMPLEMENTATION.md