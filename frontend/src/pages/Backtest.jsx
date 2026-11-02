import React, { useEffect, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, fmt, pnlColor, ErrorBox } from "../api.jsx";
export default function Backtest({ saved, setSaved, draft }) {
  const [list, setList] = useState([]); const [sid, setSid] = useState(saved?.id || ""); const [r, setR] = useState(null); const [err, setErr] = useState(null);
  useEffect(() => { api("/api/strategies").then(setList).catch(() => {}); }, [saved]);
  const run = async () => { setErr(null); setR(null); try { setR(await api("/api/backtests", { method: "POST", body: { strategy_id: Number(sid) } })); } catch (e) { setErr(e); } };
  const M = r?.metrics;
  return (
    <div>
      <div className="flex gap-2 mb-3"><select className="bg-panel border border-line rounded px-2" value={sid} onChange={(e) => setSid(e.target.value)}><option value="">Select saved strategy…</option>{list.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}</select>
        <button className="btn btn-ai" disabled={!sid} onClick={run}>Run backtest</button></div>
      <ErrorBox err={err} />
      {r && <>
        <div className={`card p-2 mb-3 text-sm ${r.validation.passed ? "border-up/50 text-up" : "border-down/50 text-down"}`}>{r.validation.passed ? "✓ Validation gate passed — eligible for paper deployment." : r.validation.errors.map((e, i) => <div key={i}>✕ {e}</div>)}
          {r.validation.warnings.map((w, i) => <div key={i} className="text-amber-400">! {w}</div>)}</div>
        <div className="grid grid-cols-7 gap-2 mb-3">{[["Total return", M.total_return_pct + "%", M.total_return_pct], ["Max drawdown", M.max_drawdown_pct + "%", -1], ["Sharpe", M.sharpe, M.sharpe], ["Win rate", M.win_rate_pct + "%", 1], ["Profit factor", M.profit_factor ?? "—", 1], ["Exposure", M.exposure_pct + "%", 1], ["Trades", M.trades, 1]].map(([l, v, s]) =>
          <div key={l} className="card p-2"><div className="text-[10px] text-slate-500">{l}</div><div className={`num text-lg ${pnlColor(s)}`}>{v}</div></div>)}</div>
        <div className="card p-3"><div className="text-xs text-slate-400 mb-1">EQUITY CURVE · {r.meta.source} · SIMULATED</div>
          <ResponsiveContainer width="100%" height={260}><AreaChart data={r.equity_curve}><CartesianGrid stroke="#1E222D" /><XAxis dataKey="ts" tickFormatter={(t) => t.slice(5, 10)} tick={{ fontSize: 10 }} minTickGap={50} /><YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} /><Tooltip contentStyle={{ background: "#121620", border: "1px solid #1E222D" }} />
            <Area dataKey="equity" stroke="#00C853" fill="#00C85322" isAnimationActive={false} /></AreaChart></ResponsiveContainer>
          <ResponsiveContainer width="100%" height={110}><AreaChart data={r.equity_curve}><XAxis dataKey="ts" hide /><YAxis tick={{ fontSize: 10 }} /><Area dataKey="drawdown" stroke="#FF5252" fill="#FF525233" isAnimationActive={false} /></AreaChart></ResponsiveContainer></div></>}
    </div>);
}
