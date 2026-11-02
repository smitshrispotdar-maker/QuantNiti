import React, { useEffect, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, fmt, pnlColor, ErrorBox, Badge } from "../api.jsx";

export default function Backtest({ saved, setSaved, draft }) {
  const [list, setList] = useState([]);
  const [sid, setSid] = useState(saved?.id || "");
  const [r, setR] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const [initialCash, setInitialCash] = useState(100000);
  const [transactionCostBps, setTransactionCostBps] = useState(0);
  const [slippageBps, setSlippageBps] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => { api("/api/strategies").then(setList).catch(() => {}); }, [saved]);

  const validateForm = () => {
    if (!sid) return "Please select a strategy";
    if (initialCash <= 0) return "Initial capital must be positive";
    if (transactionCostBps < 0 || transactionCostBps > 10000) return "Transaction costs must be between 0 and 10000 bps";
    if (slippageBps < 0 || slippageBps > 10000) return "Slippage must be between 0 and 10000 bps";
    if (startDate && endDate && new Date(startDate) >= new Date(endDate)) {
      return "Start date must be before end date";
    }
    return null;
  };

  const run = async () => {
    const validationError = validateForm();
    if (validationError) {
      setErr({ detail: { validation: { passed: false, errors: [validationError] } } });
      return;
    }
    setErr(null);
    setR(null);
    setLoading(true);
    try {
      const result = await api("/api/backtests", {
        method: "POST",
        body: {
          strategy_id: Number(sid),
          initial_cash: initialCash,
          transaction_cost_bps: transactionCostBps,
          slippage_bps: slippageBps,
          start_date: startDate || undefined,
          end_date: endDate || undefined,
        },
      });
      setR(result);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const M = r?.metrics;
  const strategySpec = r?.strategy_spec;

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <select className="bg-panel border border-line rounded px-2" value={sid} onChange={(e) => setSid(e.target.value)}>
          <option value="">Select saved strategy...</option>
          {list.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}
        </select>
        <button className="btn btn-ai" disabled={!sid || loading} onClick={run}>
          {loading ? "Running..." : "Run backtest"}
        </button>
      </div>

      {/* Configuration Panel */}
      <div className="card p-3 mb-3">
        <div className="text-sm font-medium mb-2">Backtest Configuration</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Initial Capital</label>
            <input
              type="number"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              min="1"
              step="1000"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Transaction Cost (bps)</label>
            <input
              type="number"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={transactionCostBps}
              onChange={(e) => setTransactionCostBps(Number(e.target.value))}
              min="0"
              max="10000"
              step="1"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Slippage (bps)</label>
            <input
              type="number"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={slippageBps}
              onChange={(e) => setSlippageBps(Number(e.target.value))}
              min="0"
              max="10000"
              step="1"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Bars</label>
            <input
              type="number"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={500}
              onChange={() => {}}
              min="30"
              step="100"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Start Date</label>
            <input
              type="date"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">End Date</label>
            <input
              type="date"
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        <ErrorBox err={err} />
      </div>

      <div className="flex gap-2 mb-3">
        <select className="bg-panel border border-line rounded px-2" value={sid} onChange={(e) => setSid(e.target.value)}>
          <option value="">Select saved strategy...</option>
          {list.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}
        </select>
        <button className="btn btn-ai" disabled={!sid || loading} onClick={run}>
          {loading ? "Running..." : "Run backtest"}
        </button>
      </div>

      <ErrorBox err={err} />

      {r && <>
        {/* Strategy & Config Info */}
        <div className="card p-3 mb-3">
          <div className="flex flex-wrap gap-4 text-sm mb-2">
            <span className="text-slate-400">Strategy:</span>
            <span className="font-medium">{r.strategy_spec?.name || "Unknown"}</span>
            <span className="text-slate-400">Version:</span>
            <span className="font-medium">v{r.strategy_version}</span>
            <span className="text-slate-400">Timeframe:</span>
            <span className="font-medium">{r.meta?.timeframe}</span>
            <span className="text-slate-400">Data:</span>
            <Badge status={r.meta?.status} />
            <span className="badge ml-auto">{r.meta?.source}</span>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="text-slate-400">Initial Capital:</span>
            <span className="font-medium">${fmt(r.initial_cash)}</span>
            <span className="text-slate-400">Tx Cost:</span>
            <span className="font-medium">{r.transaction_cost_bps} bps</span>
            <span className="text-slate-400">Slippage:</span>
            <span className="font-medium">{r.slippage_bps} bps</span>
            <span className="text-slate-400">Period:</span>
            <span className="font-medium">
              {r.start_date ? new Date(r.start_date).toLocaleDateString() : "—"} – {r.end_date ? new Date(r.end_date).toLocaleDateString() : "—"}
            </span>
            <span className="text-slate-400">Data:</span>
            <span className="font-medium">{r.meta?.source} · {r.meta?.status}</span>
          </div>
        </div>

        {/* Validation Gate */}
        <div className={`card p-2 mb-3 text-sm ${r.validation.passed ? "border-up/50 text-up" : "border-down/50 text-down"}`}>
          {r.validation.passed ? (
            <span>✓ Validation gate passed — eligible for paper deployment.</span>
          ) : (
            r.validation.errors.map((e, i) => <div key={i}>✕ {e}</div>)
          )}
          {r.validation.warnings.map((w, i) => <div key={i} className="text-amber-400">! {w}</div>)}
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-7 gap-2 mb-3">
          {[["Total return", M.total_return_pct + "%", M.total_return_pct], ["Max drawdown", M.max_drawdown_pct + "%", -1], ["Sharpe", M.sharpe, M.sharpe], ["Win rate", M.win_rate_pct + "%", 1], ["Profit factor", M.profit_factor ?? "—", 1], ["Exposure", M.exposure_pct + "%", 1], ["Trades", M.trades, 1]].map(([l, v, s]) =>
            <div key={l} className="card p-2">
              <div className="text-[10px] text-slate-500">{l}</div>
              <div className={`num text-lg ${pnlColor(s)}`}>{v}</div>
            </div>
          )}
        </div>

        {/* Strategy Spec Snapshot */}
        {strategySpec && (
          <details className="card p-3 mb-3">
            <summary className="cursor-pointer text-sm font-medium text-ai">Strategy Specification (Snapshot)</summary>
            <pre className="num text-[10px] text-slate-400 mt-2 overflow-auto max-h-64">{JSON.stringify(strategySpec, null, 2)}</pre>
          </details>
        )}

        {/* Equity Curve */}
        <div className="card p-3">
          <div className="text-xs text-slate-400 mb-1">EQUITY CURVE · {r.meta.source} · {r.validation.passed ? "VALIDATED" : "STALE"}</div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={r.equity_curve}>
              <CartesianGrid stroke="#1E222D" />
              <XAxis dataKey="ts" tickFormatter={(t) => t.slice(5, 10)} tick={{ fontSize: 10 }} minTickGap={50} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} orientation="right" />
              <Tooltip contentStyle={{ background: "#121620", border: "1px solid #1E222D" }} />
              <Area dataKey="equity" stroke="#00C853" fill="#00C85322" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="100%" height={110}>
            <AreaChart data={r.equity_curve}>
              <XAxis dataKey="ts" hide />
              <YAxis tick={{ fontSize: 10 }} />
              <Area dataKey="drawdown" stroke="#FF5252" fill="#FF525233" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Trades Table */}
        {r.trades && r.trades.length > 0 && (
          <div className="card p-3 mt-3">
            <div className="text-sm font-medium mb-2">Trade Log ({r.trades.length} trades)</div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 text-xs">
                    <th className="text-left p-2">Time</th>
                    <th className="text-left p-2">Side</th>
                    <th className="text-right p-2">Entry</th>
                    <th className="text-right p-2">Exit</th>
                    <th className="text-right p-2">PnL</th>
                    <th className="text-right p-2">Return</th>
                    <th className="text-left p-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {r.trades.map((t, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="text-xs p-2">{t.ts?.slice(5, 16)}</td>
                      <td className="p-2"><span className={t.reason?.includes("exit") ? "text-down" : "text-up"}>{t.reason?.includes("exit") ? "SELL" : "BUY"}</span></td>
                      <td className="text-right num p-2">{fmt(t.entry)}</td>
                      <td className="text-right num p-2">{fmt(t.exit)}</td>
                      <td className="text-right num p-2">{fmt(t.pnl)}</td>
                      <td className="text-right num p-2">{fmt(t.ret * 100)}%</td>
                      <td className="text-xs p-2 text-slate-400">{t.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </>}
    </div>
  );
}