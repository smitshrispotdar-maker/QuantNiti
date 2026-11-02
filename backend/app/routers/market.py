import pandas as pd
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from typing import List
from ..db import get_db
from ..services import market as m, indicators as ind, research
from ..schemas import MarketBarsResponse, WatchlistItem, SymbolInfo, MarketMeta, MarketBarRow

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/watchlist", response_model=List[WatchlistItem])
def watchlist(db: Session = Depends(get_db)):
    out = []
    for s in m.WATCHLIST:
        df, meta = m.get_bars(s, "1d", 60, db=db)
        out.append({
            **meta,
            "price": round(df.close.iloc[-1], 2),
            "change_pct": round((df.close.iloc[-1] / df.close.iloc[-2] - 1) * 100, 2)
        })
    return out


@router.get("/bars/{symbol}", response_model=MarketBarsResponse)
def bars(symbol: str, timeframe: str = "1d", limit: int = Query(200, le=1000), db: Session = Depends(get_db)):
    df, meta = m.get_bars(symbol, timeframe, max(limit, 60), db=db)
    c = df.close
    bb = ind.bbands(c)
    mc = ind.macd(c)
    df = df.assign(
        sma20=ind.sma(c, 20),
        ema20=ind.ema(c, 20),
        ema50=ind.ema(c, 50),
        rsi=ind.rsi(c),
        macd=mc[0],
        macd_signal=mc[1],
        macd_hist=mc[2],
        bb_upper=bb[0],
        bb_lower=bb[2]
    ).tail(limit)
    df.index.name = "ts"
    df = df.reset_index().round(4)
    df["ts"] = df["ts"].astype(str)
    df = df.where(pd.notna(df), None)
    rows = df.to_dict("records")
    return {"meta": meta, "bars": rows}


@router.get("/research/{symbol}")
def research_view(symbol: str, timeframe: str = "1d", db: Session = Depends(get_db)):
    df, meta = m.get_bars(symbol, timeframe, 200, db=db)
    return {"meta": meta, **research.run(df)}


@router.get("/search")
def search(q: str):
    return [s for s in m.WATCHLIST + ["MSFT", "TSLA", "QQQ", "SOL-USD"] if q.upper() in s]


@router.get("/symbols", response_model=List[SymbolInfo])
def symbols():
    """Return all supported symbols with metadata."""
    return [
        {
            "symbol": s,
            "name": m.SYMBOL_NAMES.get(s, s),
            "timezone": m.EXCHANGE_TIMEZONES.get(s, "UTC"),
        }
        for s in m.WATCHLIST
    ]