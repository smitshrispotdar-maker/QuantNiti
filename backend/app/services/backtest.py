"""Deterministic long-only backtester (vectorised signals, bar-by-bar fills at next open → no look-ahead)."""
import math
import numpy as np, pandas as pd
from ..schemas import StrategySpec, Rule
from .indicators import compute
from . import market
def _side(df, x):
    return df[x] if isinstance(x, str) else pd.Series(float(x), index=df.index)
def eval_rule(df, r: Rule) -> pd.Series:
    a, b = _side(df, r.left), _side(df, r.right)
    if r.op == ">": return a > b
    if r.op == "<": return a < b
    if r.op == "crosses_above": return (a > b) & (a.shift() <= b.shift())
    return (a < b) & (a.shift() >= b.shift())
def signals(df, spec: StrategySpec):
    full = pd.Series(False, index=df.index)
    entry = pd.concat([eval_rule(df, r) for r in spec.entry_rules], axis=1).all(axis=1) if spec.entry_rules else full
    exit_ = pd.concat([eval_rule(df, r) for r in spec.exit_rules], axis=1).any(axis=1) if spec.exit_rules else full
    return entry.fillna(False), exit_.fillna(False)
def run(spec: StrategySpec, bars: pd.DataFrame, initial_cash=100_000.0, transaction_cost_bps=0.0, slippage_bps=0.0):
    df = compute(bars, spec.indicators); entry, exit_ = signals(df, spec); r = spec.risk
    cash, qty, entry_px, trades, eq = initial_cash, 0.0, 0.0, [], []
    in_bars = 0
    for i in range(len(df) - 1):
        row, nxt = df.iloc[i], df.iloc[i + 1]; px = nxt.open
        # Apply slippage: buy at higher price, sell at lower price
        buy_px = px * (1 + slippage_bps / 10000)
        sell_px = px * (1 - slippage_bps / 10000)
        if qty > 0:
            reason = None
            if exit_.iloc[i]: reason = "exit_rule"
            elif r.stop_loss_pct and row.close <= entry_px * (1 - r.stop_loss_pct / 100): reason = "stop_loss"
            elif r.take_profit_pct and row.close >= entry_px * (1 + r.take_profit_pct / 100): reason = "take_profit"
            if reason:
                # Apply transaction cost on sell
                sell_px_net = sell_px * (1 - transaction_cost_bps / 10000)
                cash += qty * sell_px_net
                trades.append({"entry": entry_px, "exit": px, "pnl": qty * (sell_px_net - entry_px), "ret": sell_px_net / entry_px - 1, "reason": reason, "ts": str(df.index[i + 1])})
                qty = 0.0
        elif entry.iloc[i] and not math.isnan(px):
            # Apply transaction cost on buy
            buy_px_net = buy_px * (1 + transaction_cost_bps / 10000)
            qty = (cash * r.max_position_pct / 100) / buy_px_net; cash -= qty * buy_px_net; entry_px = buy_px_net
        if qty > 0: in_bars += 1
        eq.append(cash + qty * row.close)
    eq.append(cash + qty * df.close.iloc[-1])
    s = pd.Series(eq, index=df.index); rets = s.pct_change().dropna()
    dd = (s / s.cummax() - 1).min()
    pnl = np.array([t["pnl"] for t in trades]) if trades else np.array([])
    gp, gl = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    ann = {"1d": 252, "1h": 252 * 24, "15m": 252 * 96, "5m": 252 * 288, "1m": 252 * 1440}[spec.timeframe]
    metrics = {"total_return_pct": round((s.iloc[-1] / initial_cash - 1) * 100, 2), "max_drawdown_pct": round(dd * 100, 2),
               "sharpe": round(float(rets.mean() / rets.std() * math.sqrt(ann)), 2) if rets.std() > 0 else 0.0,
               "win_rate_pct": round(float((pnl > 0).mean() * 100), 1) if len(pnl) else 0.0,
               "profit_factor": round(float(gp / gl), 2) if gl > 0 else (None if gp == 0 else 999.0),
               "exposure_pct": round(in_bars / len(df) * 100, 1), "trades": len(trades)}
    curve = [{"ts": str(k), "equity": round(v, 2), "drawdown": round((v / s[:k].max() - 1) * 100, 2)} for k, v in s.items()]
    return metrics, curve, trades

def compute_market_data(symbol: str, timeframe: str, bars: int, db) -> tuple:
    """Fetch market data for paper trading execution. Returns (df, meta)."""
    return market.get_bars(symbol, timeframe, bars, db)
