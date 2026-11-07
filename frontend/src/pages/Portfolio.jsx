import React, { useCallback, useEffect, useMemo, useState } from "react";
import { PieChart, Plus, RefreshCw, Wallet } from "lucide-react";
import Panel from "../components/ui/Panel.jsx";
import { ErrorBox, fmt, fmtCompact, paperApi, pnlColor, signed, signedPct } from "../api.jsx";
import { displayName } from "../market/instruments.js";

const acctId = (a) => a?.id ?? a?.account?.id ?? null;
const acctName = (a) => a?.name || a?.account?.name || `Paper account ${acctId(a) || ""}`;
const accountInfo = (a) => a?.account || a || {};
const positionsOf = (a) => (a?.positions || []).filter((p) => Math.abs(p.qty) > 1e-9);
const positionValue = (p) => {
  const qty = Number(p.qty || 0);
  const last = Number(p.current_price ?? p.last ?? p.avg_price ?? p.avg_entry_price ?? 0);
  return qty * last;
};

export default function Portfolio() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await paperApi.accounts();
      setAccounts(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e);
      setAccounts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    setCreating(true);
    setError(null);
    try {
      await paperApi.create({ name: "Portfolio paper account", starting_cash: 500000 });
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setCreating(false);
    }
  };

  const summary = useMemo(() => {
    let equity = 0;
    let cash = 0;
    let starting = 0;
    const bySymbol = new Map();
    for (const a of accounts) {
      const info = accountInfo(a);
      const metrics = a.metrics || {};
      equity += Number(info.equity ?? a.equity ?? metrics.equity ?? 0);
      cash += Number(info.cash ?? a.cash ?? metrics.cash ?? 0);
      starting += Number(info.starting_cash ?? a.starting_cash ?? 0);
      for (const p of positionsOf(a)) {
        const value = positionValue(p);
        const entry = bySymbol.get(p.symbol) || { symbol: p.symbol, value: 0, qty: 0, unrealized: 0 };
        entry.value += value;
        entry.qty += Number(p.qty || 0);
        entry.unrealized += Number(p.unrealized ?? p.unrealized_pnl ?? 0);
        bySymbol.set(p.symbol, entry);
      }
    }
    const pnl = equity - starting;
    return {
      equity,
      cash,
      starting,
      pnl,
      pnlPct: starting ? (pnl / starting) * 100 : null,
      allocation: [...bySymbol.values()].sort((a, b) => b.value - a.value),
      totalInvested: [...bySymbol.values()].reduce((sum, x) => sum + x.value, 0),
    };
  }, [accounts]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <PieChart size={16} className="text-ai" />
        <h1 className="text-sm font-semibold">Portfolio</h1>
        <span className="badge badge-ai">PAPER / SIMULATED</span>
        <span className="text-2xs text-muted-2">Aggregated across simulated paper accounts — no broker connection.</span>
        <button className="btn btn-xs btn-ghost ml-auto" onClick={load}><RefreshCw size={11} /> Refresh</button>
        <button className="btn btn-xs btn-ai" onClick={create} disabled={creating}><Plus size={11} /> New paper account</button>
      </div>

      {error && <ErrorBox err={error} onRetry={load} />}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        {[
          ["Total equity", fmt(summary.equity), ""],
          ["Cash", fmt(summary.cash), "text-muted"],
          ["Total P&L", `${signed(summary.pnl)} (${signedPct(summary.pnlPct)})`, pnlColor(summary.pnl)],
          ["Paper accounts", String(accounts.length), ""],
        ].map(([label, value, tone]) => (
          <div key={label} className="card p-3">
            <div className="text-2xs uppercase tracking-wider text-muted-2">{label}</div>
            <div className={`num text-base mt-1 ${tone}`}>{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3">
        <Panel title="Allocation by instrument" className="xl:col-span-1" dense>
          {loading && <div className="p-3 space-y-2"><div className="skeleton h-6" /><div className="skeleton h-6" /></div>}
          {!loading && summary.allocation.length === 0 && (
            <div className="p-3 text-2xs text-muted">No open positions in any paper account.</div>
          )}
          <div className="p-3 space-y-2">
            {summary.allocation.map((row) => {
              const pct = summary.totalInvested ? (row.value / summary.totalInvested) * 100 : 0;
              return (
                <div key={row.symbol}>
                  <div className="flex items-center gap-2 text-2xs">
                    <span className="text-text">{displayName(row.symbol)}</span>
                    <span className="num text-muted-2 ml-auto">{fmtCompact(row.value)}</span>
                    <span className="num text-muted-2 w-10 text-right">{fmt(pct, 1)}%</span>
                  </div>
                  <div className="h-1.5 rounded bg-surface mt-1 overflow-hidden">
                    <div className="h-full bg-ai/60" style={{ width: `${Math.max(1, pct)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>

        <div className="xl:col-span-2 space-y-3">
          {loading && <div className="card p-4"><div className="skeleton h-24" /></div>}
          {!loading && accounts.length === 0 && (
            <div className="card p-5 text-center">
              <Wallet size={20} className="mx-auto text-muted-2" />
              <div className="text-xs text-text mt-2">No paper portfolio yet</div>
              <div className="text-2xs text-muted mt-1">Create a simulated account, then place orders from the Market terminal.</div>
              <button className="btn btn-ai mt-3" onClick={create} disabled={creating}>Create paper account</button>
            </div>
          )}
          {accounts.map((a) => {
            const info = accountInfo(a);
            const metrics = a.metrics || {};
            const positions = positionsOf(a);
            const equity = info.equity ?? a.equity ?? metrics.equity;
            const cash = info.cash ?? a.cash ?? metrics.cash;
            const base = info.starting_cash ?? a.starting_cash;
            const pnl = metrics.total_return ?? a.pnl ?? (equity != null && base != null ? equity - base : null);
            return (
              <Panel
                key={acctId(a)}
                title={<span className="flex items-center gap-1.5"><Wallet size={12} /> {acctName(a)} <span className="badge text-muted-2">#{acctId(a)}</span></span>}
                actions={<span className="flex items-center gap-2 normal-case tracking-normal"><span className="badge badge-ai">SIMULATED</span><span className={`num text-xs ${pnlColor(pnl)}`}>{signed(pnl)}</span></span>}
                dense
              >
                <div className="grid grid-cols-3 gap-2 px-3 py-2 border-b border-line-soft">
                  <div><div className="text-2xs text-muted-2">Equity</div><div className="num text-xs">{fmt(equity)}</div></div>
                  <div><div className="text-2xs text-muted-2">Cash</div><div className="num text-xs">{fmt(cash)}</div></div>
                  <div><div className="text-2xs text-muted-2">Start</div><div className="num text-xs">{fmt(base)}</div></div>
                </div>
                {positions.length === 0 && <div className="p-3 text-2xs text-muted">No open positions.</div>}
                {positions.map((p) => (
                  <div key={p.symbol} className="flex items-center gap-2 px-3 py-1.5 border-b border-line-soft/50 text-2xs">
                    <span className="text-text flex-1 truncate">{displayName(p.symbol)}</span>
                    <span className="num text-muted">{fmt(p.qty, 4)}</span>
                    <span className="num text-muted-2">@ {fmt(p.avg_entry_price ?? p.avg_price)}</span>
                    <span className="num text-text w-16 text-right">{fmt(p.current_price ?? p.last)}</span>
                    <span className={`num w-20 text-right ${pnlColor(p.unrealized_pnl ?? p.unrealized)}`}>{signed(p.unrealized_pnl ?? p.unrealized)}</span>
                  </div>
                ))}
              </Panel>
            );
          })}
        </div>
      </div>

      <div className="text-2xs text-muted-2">
        Portfolio values use the latest available provider prices. Realized/unrealized figures are simulated and do not represent broker balances.
      </div>
    </div>
  );
}
