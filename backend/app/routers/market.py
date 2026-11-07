"""India-only market data API."""
import asyncio
import pandas as pd
from fastapi import APIRouter, Query, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import List, Optional

from ..db import get_db
from ..services import market as m, indicators as ind, research
from ..services import instruments as inst
from ..schemas import MarketBarsResponse, WatchlistItem, SymbolInfo, MarketMeta, MarketBarRow

router = APIRouter(prefix="/api/market", tags=["market"])


def _canonical(symbol: str) -> str:
    resolved = inst.resolve_symbol(symbol)
    if not resolved:
        raise HTTPException(404, f"Unsupported instrument: {symbol}. QuantNiti supports NSE/BSE instruments only.")
    return resolved


def _bars_payload(symbol: str, timeframe: str, limit: int, db: Session) -> dict:
    df, meta = m.get_bars(symbol, timeframe, max(limit, 60), db=db)
    if df.empty:
        return {"meta": meta, "bars": []}
    c = df.close
    bb = ind.bbands(c)
    mc = ind.macd(c)
    df = df.assign(
        sma20=ind.sma(c, 20),
        ema9=ind.ema(c, 9),
        ema20=ind.ema(c, 20),
        ema21=ind.ema(c, 21),
        ema50=ind.ema(c, 50),
        ema200=ind.ema(c, 200),
        rsi=ind.rsi(c),
        macd=mc[0],
        macd_signal=mc[1],
        macd_hist=mc[2],
        bb_upper=bb[0],
        bb_middle=bb[1],
        bb_lower=bb[2],
    ).tail(limit)
    df.index.name = "ts"
    df = df.reset_index()
    df["ts"] = df["ts"].astype(str)
    df = df.where(pd.notna(df), None)
    return {"meta": meta, "bars": df.round(4).to_dict("records")}


@router.get("/status")
def market_status():
    """NSE/BSE cash-market session status. Calendar only — not an exchange feed."""
    return {"exchanges": {"NSE": inst.session_status(), "BSE": inst.session_status()}, **inst.session_status()}


@router.get("/capabilities")
def capabilities():
    """Explicitly describe provider coverage / realtime limitations."""
    return m.capabilities()


@router.get("/indices")
def indices(db: Session = Depends(get_db)):
    """Key Indian index snapshot (delayed provider data)."""
    return {"items": m.indices(db=db), "session": inst.session_status()}


@router.get("/overview/{symbol}")
def overview(symbol: str, db: Session = Depends(get_db)):
    """Compact quote + OHLC + provider status for an Indian instrument."""
    symbol = _canonical(symbol)
    q = m.quote(symbol, db=db)
    q["capabilities"] = m.capabilities()
    return q


@router.get("/watchlist")
def watchlist(db: Session = Depends(get_db)):
    """Default Indian market watchlist with current quotes."""
    out = []
    for s in m.WATCHLIST:
        try:
            out.append(m.quote(s, db=db))
        except Exception as e:
            out.append({
                "symbol": s, "name": inst.name_for(s), "exchange": inst.exchange_for(s),
                "price": None, "change": None, "change_pct": None, "volume": None,
                "status": "UNAVAILABLE", "provider": None, "reason": str(e)[:160],
            })
    return out


@router.get("/bars/{symbol}", response_model=MarketBarsResponse)
def bars(symbol: str, timeframe: str = "1d", limit: int = Query(200, le=1000), db: Session = Depends(get_db)):
    symbol = _canonical(symbol)
    if timeframe not in m.FREQ:
        raise HTTPException(400, f"Unsupported timeframe: {timeframe}")
    return _bars_payload(symbol, timeframe, limit, db)


@router.get("/research/{symbol}")
def research_view(symbol: str, timeframe: str = "1d", db: Session = Depends(get_db)):
    symbol = _canonical(symbol)
    df, meta = m.get_bars(symbol, timeframe, 300, db=db)
    if len(df) < 31:
        reason = (meta.get("data_quality", {}).get("issues") or [None])[0]
        return {
            "meta": meta,
            "facts": None,
            "interpretations": None,
            "label": "AI ANALYSIS UNAVAILABLE — INSUFFICIENT MARKET DATA",
            "available": False,
            "reason": reason or f"Insufficient bars for analysis ({len(df)} available, at least 31 required).",
        }
    result = research.run(df)
    result["available"] = True
    result["meta"] = meta
    return result


@router.get("/movers")
def market_movers(limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    return m.movers(db=db, limit=limit)


@router.get("/tape/{symbol}")
def tape(symbol: str):
    """Exchange trade prints. Explicitly unavailable with the current provider."""
    return m.trade_tape(symbol)


@router.get("/search")
def search(q: str = "", limit: int = Query(25, ge=1, le=100)):
    """Search the India-only instrument universe."""
    return inst.search(q, limit=limit)


@router.get("/symbols", response_model=List[SymbolInfo])
def symbols():
    """Return all supported Indian instruments with metadata."""
    return [
        {
            "symbol": item["symbol"],
            "name": item["name"],
            "timezone": "Asia/Kolkata",
            "exchange": item["exchange"],
            "kind": item["kind"],
            "available": bool(item.get("yahoo")),
            "reason": inst.unavailable_reason(item["symbol"]),
        }
        for item in inst.INSTRUMENTS
    ]


@router.websocket("/stream/{symbol}")
async def stream(websocket: WebSocket, symbol: str, timeframe: str = "1d"):
    """Server-side quote snapshot stream.

    Yahoo Finance has no licensed realtime NSE stream, so this endpoint polls
    the provider and pushes a clearly-labelled snapshot. Every payload includes
    ``provider_stream: false`` and the provider status.
    """
    await websocket.accept()
    canonical = inst.resolve_symbol(symbol) or symbol
    try:
        while True:
            df, meta = await run_in_threadpool(m.get_bars, canonical, timeframe, 5, None, False)
            payload = {
                "type": "quote",
                "symbol": canonical,
                "timeframe": timeframe,
                "status": meta.get("status", "UNAVAILABLE"),
                "source": meta.get("source"),
                "fetched_at": meta.get("fetched_at"),
                "last_bar": meta.get("last_bar"),
                "provider_stream": False,
                "transport": "websocket-snapshot",
                "note": "Snapshot push over WebSocket; the provider does not offer a realtime exchange stream.",
            }
            if not df.empty:
                last = df.iloc[-1]
                prev = float(df["close"].iloc[-2]) if len(df) > 1 else None
                payload.update({
                    "price": round(float(last["close"]), 2),
                    "open": round(float(last["open"]), 2),
                    "high": round(float(last["high"]), 2),
                    "low": round(float(last["low"]), 2),
                    "volume": float(last["volume"]) if "volume" in last else None,
                    "prev_close": round(prev, 2) if prev else None,
                    "change": round(float(last["close"]) - prev, 2) if prev else None,
                    "change_pct": round((float(last["close"]) / prev - 1) * 100, 2) if prev else None,
                })
            await websocket.send_json(payload)
            await asyncio.sleep(15)
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
