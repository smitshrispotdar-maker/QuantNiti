# QuantNiti — AI quantitative research & PAPER-trading platform
**Paper/simulated only. No broker integration, no real money, no credentials anywhere in this codebase.**

## Run
```bash
cp .env.example .env          # defaults work with Docker Compose
docker compose up --build     # db + backend (runs `alembic upgrade head` on start) + frontend
```
- App: http://localhost:5173 · API docs: http://localhost:8000/docs
- Manual migration: `docker compose run --rm backend alembic upgrade head`
- Offline / no Yahoo access: set `USE_LIVE_DATA=false` in `.env` (deterministic mock bars, badged `SIMULATED`).

## Flow
1. **AI Studio** → describe a strategy → canonical JSON appears → *Save*.
2. **Builder** → loads the chat draft as nodes; *Sync to strategy* writes canvas edits back to the same schema.
3. **Backtest** → pick saved strategy → metrics + validation gate.
4. **Paper trading** → create account → *Deploy* (blocked unless the latest backtest passes) → *Evaluate now*. Pause / stop / kill controls.
5. **Journal** → log decisions with evidence snapshot; add outcome reviews later.

## Safety design
Parsing/agents only emit `StrategySpec` JSON (Pydantic, allowlisted indicators/operators). `services/validation.py` gates every backtest and deployment. Nothing evals code.

## Known MVP limits
Rule-based parser and templated bull/bear agents (no LLM; plug one in behind `services/nlp.py` / `services/research.py`), native pandas backtester instead of Backtrader, long-only, no auth (single seeded user), `market_bars` table defined but bars are not yet cached into it.
