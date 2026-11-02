import pandas as pd
def sma(s, n): return s.rolling(int(n)).mean()
def ema(s, n): return s.ewm(span=int(n), adjust=False).mean()
def rsi(s, n=14):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, 1e-12))
def macd(s, fast=12, slow=26, sig=9):
    line = ema(s, fast) - ema(s, slow); signal = ema(line, sig); return line, signal, line - signal
def bbands(s, n=20, k=2):
    m = sma(s, n); sd = s.rolling(int(n)).std(); return m + k * sd, m, m - k * sd
def compute(df: pd.DataFrame, indicators) -> pd.DataFrame:
    """Adds one column per indicator id (MACD -> id=histogram line, BBANDS -> id=middle band) to a copy of df."""
    out = df.copy(); out["price"] = out["close"]
    for i in indicators:
        p = i.params; t = i.type
        if t == "SMA": out[i.id] = sma(out.close, p.get("period", 20))
        elif t == "EMA": out[i.id] = ema(out.close, p.get("period", 20))
        elif t == "RSI": out[i.id] = rsi(out.close, p.get("period", 14))
        elif t == "MACD": out[i.id] = macd(out.close, p.get("fast", 12), p.get("slow", 26), p.get("signal", 9))[0]
        elif t == "BBANDS":
            u, m, l = bbands(out.close, p.get("period", 20), p.get("k", 2)); out[i.id] = m; out[i.id + "_upper"] = u; out[i.id + "_lower"] = l
    return out
