import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import SessionLocal, Base, engine
from .models import User
from .routers import market, strategies, backtests, paper, journal, watchlist, research, lineage
Base.metadata.create_all(bind=engine)  # safety net; Alembic is the primary path
with SessionLocal() as db:  # single seeded local user (no auth in MVP)
    if not db.get(User, 1): db.add(User(id=1, email="local@quantniti")); db.commit()
app = FastAPI(title="QuantNiti — PAPER/SIMULATED ONLY")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["*"], allow_headers=["*"])
for r in (market, strategies, backtests, paper, journal, watchlist, research, lineage): app.include_router(r.router)
@app.get("/api/health")
def health(): return {"ok": True, "mode": "PAPER/SIMULATED", "live_trading": False}
