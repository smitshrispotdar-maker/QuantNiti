import pandas as pd
from fastapi import APIRouter, Query
from ..services import market as m, indicators as ind, research
router = APIRouter(prefix="/api/market", tags=["market"])
@router.get("/watchlist")
def watchlist():
    out = []
    for s in m.WATCHLIST:
        df, meta = m.get_bars(s, "1d", 60)
        out.append({**meta, "price": round(df.close.iloc[-1], 2), "change_pct": round((df.close.iloc[-1] / df.close.iloc[-2] - 1) * 100, 2)})
    return out
@router.get("/bars/{symbol}")
def bars(symbol: str, timeframe: str = "1d", limit: int = Query(200, le=1000)):
    df, meta = m.get_bars(symbol, timeframe, max(limit, 60))
    c = df.close; bb = ind.bbands(c); mc = ind.macd(c)
    df = df.assign(sma20=ind.sma(c, 20), ema20=ind.ema(c, 20), ema50=ind.ema(c, 50), rsi=ind.rsi(c), macd=mc[0], macd_signal=mc[1], macd_hist=mc[2], bb_upper=bb[0], bb_lower=bb[2]).tail(limit)
    df.index.name = "ts"
    df = df.reset_index().round(4)
    df["ts"] = df["ts"].astype(str)
    df = df.where(pd.notna(df), None)
    rows = df.to_dict("records")
    return {"meta": meta, "bars": rows}
@router.get("/research/{symbol}")
def research_view(symbol: str, timeframe: str = "1d"):
    df, meta = m.get_bars(symbol, timeframe, 200)
    return {"meta": meta, **research.run(df)}
@router.get("/search")
def search(q: str):
    return [s for s in m.WATCHLIST + ["MSFT", "TSLA", "QQQ", "SOL-USD"] if q.upper() in s]
