"""Market data: Yahoo Finance (free) with a deterministic mock fallback. Every response carries source + freshness metadata."""
import os, zlib
from datetime import datetime, timedelta
import numpy as np, pandas as pd
WATCHLIST = ["BTC-USD", "ETH-USD", "AAPL", "SPY"]
FREQ = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1h", "1d": "1D"}
YF_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}
BASE = {"BTC-USD": 65000, "ETH-USD": 3200, "AAPL": 190, "SPY": 520}
def _mock(symbol, tf, n):
    rng = np.random.default_rng(zlib.crc32(f"{symbol}{tf}".encode()))  # deterministic per symbol/timeframe
    base = BASE.get(symbol, 100)
    ret = rng.normal(0.0004, 0.018 if "USD" in symbol else 0.011, n)
    close = base * np.exp(np.cumsum(ret))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + rng.uniform(0, .008, n)); low = np.minimum(open_, close) * (1 - rng.uniform(0, .008, n))
    end = pd.Timestamp.utcnow().floor(FREQ[tf]).tz_localize(None)
    idx = pd.date_range(end=end, periods=n, freq=FREQ[tf])
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": rng.uniform(1e3, 1e5, n)}, index=idx)
def get_bars(symbol: str, tf: str = "1d", n: int = 300):
    """Returns (DataFrame, meta). Falls back to MOCK when live data is unavailable."""
    symbol = symbol.upper().replace("/", "-")
    if os.getenv("USE_LIVE_DATA", "true") == "true":
        try:
            import yfinance as yf
            period = "2y" if tf == "1d" else ("60d" if tf in ("5m", "15m", "1h") else "5d")
            df = yf.download(symbol, period=period, interval=YF_INTERVAL[tf], progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna().tail(n)
            if len(df) > 30:
                df.index = pd.to_datetime(df.index).tz_localize(None)
                return df, _meta(symbol, tf, df, "YAHOO FINANCE", "DELAYED")
        except Exception:
            pass
    df = _mock(symbol, tf, n)
    return df, _meta(symbol, tf, df, "MOCK GENERATOR", "SIMULATED")
def _meta(symbol, tf, df, source, status):
    return {"symbol": symbol, "timeframe": tf, "source": source, "status": status,
            "last_bar": df.index[-1].isoformat(), "fetched_at": datetime.utcnow().isoformat(), "label": "PAPER/SIMULATED"}
