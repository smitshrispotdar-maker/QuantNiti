# QuantNiti — India market terminal, AI research & PAPER trading
**Paper/simulated only. No broker integration, no real money, no credentials anywhere in this codebase.**

QuantNiti is an **India-only** market terminal for NSE/BSE instruments: NIFTY 50,
BANK NIFTY, FINNIFTY, key Indian indices, INDIA VIX and NSE/BSE-listed stocks.
The default logged-in screen is the NIFTY 50 terminal (chart, watchlist, movers,
market overview, trade tape, AI analysis and paper-trading ticket). US equities,
crypto and other international instruments are intentionally unsupported.

## Run
```bash
cp .env.example .env          # defaults work with Docker Compose
docker compose up --build     # db + backend (runs `alembic upgrade head`) + frontend
```
- App: http://localhost:5173 · API docs: http://localhost:8000/docs
- Manual migration: `docker compose run --rm backend alembic upgrade head`
- Offline / no Yahoo access: set `USE_LIVE_DATA=false` in `.env`. Deterministic
  mock bars are returned and every payload is badged `SIMULATED`.

## Flow
1. **Market** → NIFTY 50 opens by default. Search and manage the India-only
   watchlist, switch timeframe/overlays, inspect movers and AI analysis, and
   place simulated orders from the paper ticket.
2. **AI Studio** → describe a strategy → canonical JSON appears → *Save*.
3. **Strategy Builder** → loads the chat draft as nodes; *Sync to strategy*
   writes canvas edits back to the same schema.
4. **Backtesting** → pick a saved strategy → metrics + validation gate.
5. **Paper Trading** → create an account → *Deploy* (blocked unless the latest
   backtest passes) → *Evaluate now*. Pause / stop / kill controls.
6. **Portfolio** → aggregated simulated equity, cash, positions and allocation.
7. **Trade Journal** → log decisions with evidence snapshot and outcome reviews.

## Data honesty
- The configured provider is **Yahoo Finance**, which supplies **delayed** NSE/BSE
  data. Quotes are labelled `DELAYED`, never `LIVE`.
- The WebSocket at `/api/market/stream/{symbol}` pushes server-side polled
  snapshots (`provider_stream: false`). It is not an exchange feed.
- NSE/BSE trade prints and order-book depth are **not provided** by this
  provider. Those panels show an explicit not-connected state and never
  fabricate transactions.
- If a provider request fails and live data is enabled, supported Indian
  instruments return `UNAVAILABLE` with no bars or prices. Mock data is only
  used when `USE_LIVE_DATA=false` (development) and is labelled `SIMULATED`.
- NIFTY NEXT 50 has no provider coverage in the current catalogue; it remains
  searchable but is marked `UNAVAILABLE` instead of being mapped to a wrong ticker.

## Verify
```bash
cd backend && ./venv/bin/python -m pytest -q
cd frontend && npm test && npm run build
```

## Safety design
Parsing/agents only emit `StrategySpec` JSON (Pydantic, allowlisted indicators and
operators). `services/validation.py` gates every backtest and deployment. Nothing
evals generated code. Research output is explicitly labelled **analysis, not
prediction**, and agents cannot trade.

## Known limits
Rule-based parser and templated bull/bear agents (no LLM; plug one in behind
`services/nlp.py` / `services/research.py`), native pandas backtester, long-only
paper execution, and delayed provider data as described above.
