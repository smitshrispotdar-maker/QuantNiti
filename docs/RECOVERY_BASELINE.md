# QuantNiti — Post-Recovery Verification & Safe Baseline

**Date:** 2026-11-02  
**Purpose:** Verify repository state, environment, and establish reproducible baseline after recovery.

---

## 1. Repository Location & Git Status

| Item | Value |
|------|-------|
| **Working Directory** | `/Users/smitshrismackbook/Downloads/quantniti` |
| **Git Repository** | **No** — `quantniti/` is not a Git repository (no `.git` directory) |
| **Parent Directory Git** | `/Users/smitshrismackbook/Downloads/` has a Git repo, but `quantniti/` is **untracked** (`?? quantniti/`) |
| **Current Branch** | N/A (no commits in quantniti) |
| **Latest Commit** | N/A |
| **Remotes** | None configured for quantniti |

> **Note:** The quantniti project exists as an untracked directory inside a parent Git repository. No version history exists for this project specifically.

---

## 2. Actual Directory Structure

```
/Users/smitshrismackbook/Downloads/quantniti/
├── .env                          # Environment variables (matches .env.example)
├── .env.example                  # Template: DATABASE_URL, CORS_ORIGINS, USE_LIVE_DATA
├── .venv/                        # Root-level venv (EMPTY - only pip)
├── .vscode/settings.json         # VS Code settings
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py   # Initial schema migration
│   ├── alembic.ini               # Alembic config
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── db.py                 # SQLAlchemy engine & session
│   │   ├── models.py             # 8 SQLAlchemy models
│   │   ├── schemas.py            # Pydantic StrategySpec v1.0 + DTOs
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── market.py
│   │   │   ├── strategies.py
│   │   │   ├── backtests.py
│   │   │   ├── paper.py
│   │   │   └── journal.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── indicators.py
│   │       ├── backtest.py
│   │       ├── validation.py
│   │       ├── nlp.py
│   │       ├── research.py
│   │       └── market.py
│   ├── Dockerfile                # Python 3.12-slim
│   ├── requirements.txt          # 9 pinned dependencies
│   └── venv/                     # Backend venv (ALL DEPS INSTALLED HERE)
├── docker-compose.yml            # PG16 + Backend + Frontend
├── docs/
│   └── AUDIT_REPORT.md           # Audit report from Prompt 1
├── frontend/
│   ├── Dockerfile                # Node 20-alpine
│   ├── package.json              # React 18, Recharts, ReactFlow, etc.
│   ├── package-lock.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.jsx
│       ├── index.css
│       └── pages/
│           ├── Dashboard.jsx
│           ├── Studio.jsx
│           ├── Builder.jsx
│           ├── Backtest.jsx
│           ├── Paper.jsx
│           └── Journal.jsx
└── README.md                     # Run instructions, flow, safety design
```

---

## 3. Python & Node.js Versions

| Component | Version | Notes |
|-----------|---------|-------|
| **System Python** | 3.13.5 (Anaconda) | `python3 --version` |
| **Backend venv Python** | 3.13.5 | `backend/venv/bin/python --version` |
| **Dockerfile Python** | 3.12-slim | **Mismatch** — venv uses 3.13.5, Dockerfile specifies 3.12 |
| **System Node.js** | v24.8.0 | `node --version` |
| **System npm** | 11.21.0 | `npm --version` |
| **Dockerfile Node** | 20-alpine | **Mismatch** — system uses 24.8.0, Dockerfile specifies 20 |
| **Docker** | 29.6.2 | Available |
| **Docker Compose** | v5.3.1 | Available |

> **Compatibility Concern:** Python 3.13 may have compatibility issues with some dependencies pinned for 3.12. The Docker environment (3.12) is the reference; local venv uses 3.13.

---

## 4. Declared Dependencies & Compatibility

### Backend (`backend/requirements.txt`)

| Package | Pinned Version | Installed (venv) | Status |
|---------|----------------|------------------|--------|
| fastapi | 0.115.0 | 0.162.0 | **Newer** — may have breaking changes |
| uvicorn[standard] | 0.30.6 | 0.54.0 | **Newer** |
| sqlalchemy | 2.0.35 | 2.1.6 | **Newer** |
| alembic | 1.13.3 | 1.20.1 | **Newer** |
| psycopg2-binary | 2.9.9 | 2.9.13 | **Newer** |
| pydantic | 2.9.2 | 2.14.2 | **Newer** — v2.x compatible |
| pandas | 2.2.3 | 3.1.0 | **Major version newer** — potential breaking changes |
| numpy | 2.1.1 | 2.5.4 | **Newer** |
| yfinance | 0.2.43 | 1.7.0 | **Major version newer** — API may differ |

> **Critical Finding:** All installed packages are **newer than pinned versions**, some by major versions (pandas 2→3, yfinance 0.2→1.7). The Docker build will install pinned versions, but the local venv has drifted. **Recommendation:** Recreate venv from `requirements.txt` or update `requirements.txt` to match working versions.

### Frontend (`frontend/package.json`)

| Package | Declared | Installed (node_modules) | Status |
|---------|----------|-------------------------|--------|
| react | 18.3.1 | 18.3.1 | ✅ Match |
| react-dom | 18.3.1 | 18.3.1 | ✅ Match |
| recharts | 2.12.7 | 2.12.7 | ✅ Match |
| reactflow | 11.11.4 | 11.11.4 | ✅ Match |
| lucide-react | 0.441.0 | 0.441.0 | ✅ Match |
| vite | 5.4.8 | 5.4.8 | ✅ Match |
| @vitejs/plugin-react | 4.3.2 | 4.3.2 | ✅ Match |
| tailwindcss | 3.4.13 | 3.4.13 | ✅ Match |
| postcss | 8.4.47 | 8.4.47 | ✅ Match |
| autoprefixer | 10.4.20 | 10.4.20 | ✅ Match |

> **Frontend dependencies match exactly.** Build succeeds.

### Environment Variables (`.env`)

| Variable | Value | Status |
|----------|-------|--------|
| `DATABASE_URL` | `postgresql+psycopg2://quant:quant@db:5432/quantniti` | ✅ Matches `.env.example` |
| `CORS_ORIGINS` | `http://localhost:5173` | ✅ Matches `.env.example` |
| `USE_LIVE_DATA` | `true` | ✅ Matches `.env.example` |

> No secrets exposed. Values are Docker Compose defaults.

---

## 5. Files Verified: Present vs Missing

### Backend — All Audit-Claimed Files **PRESENT**

| File | Exists | Syntax OK | Imports OK |
|------|--------|-----------|------------|
| `app/main.py` | ✅ | ✅ | ⚠️ Requires DB |
| `app/db.py` | ✅ | ✅ | ✅ |
| `app/models.py` | ✅ | ✅ | ✅ |
| `app/schemas.py` | ✅ | ✅ | ✅ |
| `app/services/indicators.py` | ✅ | ✅ | ✅ |
| `app/services/backtest.py` | ✅ | ✅ | ✅ |
| `app/services/validation.py` | ✅ | ✅ | ✅ |
| `app/services/nlp.py` | ✅ | ✅ | ✅ |
| `app/services/research.py` | ✅ | ✅ | ✅ |
| `app/services/market.py` | ✅ | ✅ | ✅ |
| `app/routers/market.py` | ✅ | ✅ | ✅ |
| `app/routers/strategies.py` | ✅ | ✅ | ✅ |
| `app/routers/backtests.py` | ✅ | ✅ | ✅ |
| `app/routers/paper.py` | ✅ | ✅ | ✅ |
| `app/routers/journal.py` | ✅ | ✅ | ✅ |
| `alembic/versions/0001_initial.py` | ✅ | ✅ | ✅ |
| `alembic/env.py` | ✅ | ✅ | ✅ |
| `requirements.txt` | ✅ | — | — |
| `Dockerfile` | ✅ | — | — |

### Frontend — All Audit-Claimed Files **PRESENT**

| File | Exists | Build OK |
|------|--------|----------|
| `src/main.jsx` | ✅ | ✅ |
| `src/App.jsx` | ✅ | ✅ |
| `src/api.jsx` | ✅ | ✅ |
| `src/pages/Dashboard.jsx` | ✅ | ✅ |
| `src/pages/Studio.jsx` | ✅ | ✅ |
| `src/pages/Builder.jsx` | ✅ | ✅ |
| `src/pages/Backtest.jsx` | ✅ | ✅ |
| `src/pages/Paper.jsx` | ✅ | ✅ |
| `src/pages/Journal.jsx` | ✅ | ✅ |
| `package.json` | ✅ | ✅ |
| `vite.config.js` | ✅ | ✅ |
| `tailwind.config.js` | ✅ | ✅ |
| `Dockerfile` | ✅ | — |

### Infrastructure — All Present

| File | Exists |
|------|--------|
| `docker-compose.yml` | ✅ |
| `.env.example` | ✅ |
| `.env` | ✅ |
| `README.md` | ✅ |

### Missing (Confirmed)

| Expected | Status |
|----------|--------|
| Backend unit tests (`backend/tests/` or `test_*.py`) | **MISSING** — Zero test files |
| Frontend tests (`*.test.jsx`, `*.spec.jsx`) | **MISSING** — Zero test files |
| `backend/.git` / `frontend/.git` | **MISSING** — No Git repo in quantniti |
| Authentication middleware | **MISSING** — Single seeded user only |

---

## 6. Verification Command Results

| Check | Command | Result | Details |
|-------|---------|--------|---------|
| **Python syntax (all modules)** | `python -m py_compile backend/app/*.py backend/app/services/*.py backend/app/routers/*.py` | ✅ **PASSED** | No syntax errors |
| **Service imports (no DB)** | `from app.services import *` | ✅ **PASSED** | All 6 service modules import cleanly |
| **Router imports (no DB)** | `from app.routers import *` | ✅ **PASSED** | All 5 routers import cleanly |
| **Schema validation** | `StrategySpec` instantiation + validation | ✅ **PASSED** | Pydantic v2 works |
| **NLP parser** | `parse("Buy BTC when EMA 20 crosses above EMA 50...")` | ✅ **PASSED** | Extracts indicators, rules, risk correctly |
| **Indicators computation** | `compute(df, indicators)` | ✅ **PASSED** | SMA, EMA, RSI, MACD, BBANDS work |
| **Backtest engine** | `run(spec, df, 100000)` | ✅ **PASSED** | Metrics, equity curve, trades generated |
| **Validation gate** | `validate(spec, metrics)` | ✅ **PASSED** | Blocks on <5 trades, DD exceedance |
| **Market service (mock)** | `get_bars("BTC-USD", "1d", 60)` | ✅ **PASSED** | Returns deterministic mock data + metadata |
| **Research service** | `run(df)` | ✅ **PASSED** | Returns facts + 5 agent interpretations |
| **Frontend production build** | `npm run build` | ✅ **PASSED** | 697 kB JS, 17 kB CSS, 2.35s |
| **Docker Compose config** | `docker compose config` | ✅ **PASSED** | Valid YAML, all services defined |
| **Main app import (with DB)** | `from app.main import app` | ⚠️ **BLOCKED** | Requires PostgreSQL at host `db` (Docker only) |
| **Backend unit tests** | N/A | ❌ **NOT RUN** | No test files exist |
| **Frontend unit tests** | N/A | ❌ **NOT RUN** | No test files, no test runner |
| **Database migrations** | N/A | ❌ **NOT RUN** | Requires PostgreSQL (Docker) |
| **End-to-end integration** | N/A | ❌ **NOT RUN** | Requires full Docker stack |

---

## 7. Database & Docker Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| **PostgreSQL Image** | `postgres:16-alpine` | Defined in docker-compose.yml |
| **Alembic Config** | ✅ Valid | `alembic.ini` + `alembic/env.py` |
| **Initial Migration** | ✅ Exists | `0001_initial.py` creates all 8 tables |
| **Docker Compose** | ✅ Valid | 3 services: db, backend, frontend |
| **Backend Dockerfile** | ✅ Exists | Python 3.12-slim, installs requirements |
| **Frontend Dockerfile** | ✅ Exists | Node 20-alpine, npm install, vite dev |
| **Database Connectivity** | ⚠️ **UNTTESTED** | Requires `docker compose up -d db` |
| **Migration Execution** | ⚠️ **UNTTESTED** | Requires `docker compose run --rm backend alembic upgrade head` |

> **Database is not running.** All DB-dependent checks are blocked until Docker stack is started.

---

## 8. Discrepancies: Audit Report vs Actual Repository

| Area | Audit Claim | Actual Finding | Severity |
|------|-------------|----------------|----------|
| **Git Repository** | "Is directory a git repo: yes" | **No** — quantniti/ has no `.git`, untracked in parent | Medium |
| **Python Version** | Dockerfile: 3.12 | Local venv: 3.13.5 | Low (Docker is reference) |
| **Node Version** | Dockerfile: 20 | System: 24.8.0 | Low (Docker is reference) |
| **Backend Dependencies** | Pinned versions in requirements.txt | **All newer** in venv (some major versions) | **High** — venv drifted |
| **Test Files** | "Zero test files" | Confirmed: **0 test files** | — |
| **MarketBar Cache** | "Not populated" | Confirmed: `market.py` never writes to `MarketBar` | — |
| **NLP Parser** | "Rule-based regex" | Confirmed: Pure regex, no LLM | — |
| **Paper Trading Safety** | "No broker integrations" | Confirmed: Zero broker SDKs, all orders labeled `PAPER/SIMULATED` | — |
| **AUDIT_REPORT.md** | Created in docs/ | ✅ Exists at `docs/AUDIT_REPORT.md` | — |

> **Key Discrepancy:** The audit's environment info claimed "Is directory a git repo: yes" but the quantniti directory itself is **not a Git repository**. The parent Downloads directory has Git, but quantniti is untracked.

---

## 9. Exact Commands to Start the Application

### Prerequisites
- Docker Desktop running
- Ports 5432, 8000, 5173 available

### Step-by-Step

```bash
# 1. Navigate to project
cd /Users/smitshrismackbook/Downloads/quantniti

# 2. Start PostgreSQL only (with healthcheck)
docker compose up -d db

# 3. Wait for DB healthy (≈10-30s), then run migrations
docker compose run --rm backend alembic upgrade head

# 4. Start backend (runs migrations again as safety net, then uvicorn)
docker compose up -d backend

# 5. Verify backend API docs
# Open http://localhost:8000/docs in browser

# 6. Start frontend (Vite dev server)
docker compose up -d frontend

# 7. Verify frontend
# Open http://localhost:5173 in browser

# 8. Full flow test:
#    Dashboard → Studio (chat) → Builder (sync) → Backtest (run) → Paper (deploy + step) → Journal (log)
```

### Alternative: Local Development (without Docker for DB)

```bash
# Requires local PostgreSQL running on localhost:5432 with user/pass quant/quant
# Update .env: DATABASE_URL=postgresql+psycopg2://quant:quant@localhost:5432/quantniti

# Backend
cd backend
source venv/bin/activate
# Or recreate venv: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm run dev
```

---

## 10. Prioritized Blockers to Resolve Before Development

| Priority | Blocker | Impact | Resolution |
|----------|---------|--------|------------|
| **P0** | **Backend venv dependencies drifted** (all packages newer than pinned) | Local dev may behave differently from Docker | Recreate venv: `cd backend && rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` |
| **P0** | **No test infrastructure** | Cannot verify correctness, regressions undetected | Add `pytest`, `pytest-asyncio`, `httpx` to backend; `vitest`, `@testing-library/react`, `jsdom` to frontend |
| **P0** | **Database not running** | All integration/DB tests blocked | `docker compose up -d db` |
| **P1** | **No Git repository for quantniti** | No version control, no collaboration | `cd quantniti && git init && git add . && git commit -m "Initial commit"` |
| **P1** | **Python 3.13 vs 3.12 mismatch** | Potential compatibility issues | Use Docker for reference environment; document version requirement |
| **P1** | **Transaction costs/slippage missing** | Backtest returns overstated | Add to `RiskLimits` schema + backtest engine (P0-1 in audit) |
| **P2** | **MarketBar cache not implemented** | Repeated Yahoo API calls, no local history | Implement write-through in `market.get_bars()` (P0-2 in audit) |
| **P2** | **No authentication** | Single-user only | Add JWT/API key middleware (P1-7 in audit) |

---

## 11. Paper-Trading Safety Verification

| Check | Result | Evidence |
|-------|--------|----------|
| Broker SDKs imported | ✅ **NONE** | `pip list` shows no `alpaca-trade-api`, `ib_insync`, `ccxt`, etc. |
| Real order endpoints | ✅ **NONE** | All order endpoints in `paper.py` create `PaperOrder` with `label="PAPER/SIMULATED"` |
| Simulated pricing | ✅ **CONFIRMED** | `_fill()` uses `market.get_bars(symbol, "1d", 60)[0].close.iloc[-1]` — latest close |
| Simulated cash/positions | ✅ **CONFIRMED** | `PaperAccount.cash` + computed positions from `PaperOrder` history |
| Deployment gate | ✅ **ENFORCED** | `deploy` endpoint calls `validation.validate()` and rejects on any error |
| Kill switch | ✅ **IMPLEMENTED** | `control/kill` sets `status=KILLED`, blocks all future orders |
| No short selling | ✅ **ENFORCED** | `SELL` qty validated against `held` position |

> **All paper-trading safety checks pass.** The system is **simulation-only** with no path to real-money execution.

---

## 12. Files Created/Modified During This Verification

| File | Action |
|------|--------|
| `docs/RECOVERY_BASELINE.md` | **CREATED** — This report |

> **No application source code, dependencies, database contents, or environment files were modified.** All checks were read-only or used isolated Python execution.

---

## Summary & Next Recommended Step

**Actual State:** The QuantNiti repository is a **complete, syntactically correct MVP** with all core workflows implemented (Studio → Builder → Backtest → Paper → Journal). The code compiles, imports cleanly, and core logic (NLP, indicators, backtest, validation, market mock, research) executes correctly in isolation.

**Critical Gaps:**
1. **Dependencies drifted** — local venv has major-version-newer packages than `requirements.txt`
2. **Zero tests** — no way to verify correctness or prevent regressions
3. **No Git history** — quantniti not version-controlled
4. **Database not running** — full integration untested

**Next Step (Recommended):**

```bash
# 1. Fix dependency drift
cd /Users/smitshrismackbook/Downloads/quantniti/backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Initialize Git
cd /Users/smitshrismackbook/Downloads/quantniti
git init
git add .
git commit -m "Initial commit: QuantNiti MVP"

# 3. Start Docker stack for integration testing
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
docker compose up -d frontend

# 4. Add test infrastructure (backend + frontend)
# Then begin Week 2 work per audit roadmap
```

**Verification Complete.** The baseline is established and reproducible.