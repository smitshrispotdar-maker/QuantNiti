import React, { useEffect, useState } from "react";
import { api, fmt, pnlColor, ErrorBox } from "../api.jsx";
export default function Paper() {
  const [accts, setAccts] = useState([]); const [aid, setAid] = useState(null); const [a, setA] = useState(null); const [strats, setStrats] = useState([]); const [err, setErr] = useState(null);
  const [o, setO] = useState({ symbol: "BTC-USD", side: "BUY", qty: 0.1 }); const [sid, setSid] = useState(""); const [note, setNote] = useState("");
  const load = async (id = aid) => { setAccts(await api("/api/paper/accounts")); if (id) setA(await api(`/api/paper/accounts/${id}`)); };
  useEffect(() => { load().catch(() => {}); api("/api/strategies").then(setStrats).catch(() => {}); }, []);
  const act = (fn) => async () => { setErr(null); try { const r = await fn(); if (r?.action) setNote(`Strategy signal: ${r.action}`); await load(); } catch (e) { setErr(e); } };
  const P = (p, b) => api(p, { method: "POST", body: b });
  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="card col-span-3 p-2"><button className="btn btn-ai w-full mb-2" onClick={async () => { const n = await P("/api/paper/accounts", { name: "Paper account", starting_cash: 100000 }); setAid(n.id); await load(n.id); }}>New paper account ($100k simulated)</button>
        {accts.map((x) => <button key={x.id} onClick={() => { setAid(x.id); load(x.id); }} className={`w-full text-left px-2 py-1.5 text-sm rounded ${aid === x.id ? "bg-line" : ""}`}>#{x.id} <span className="badge text-ai border-ai/40">{x.status}</span></button>)}</div>
      <div className="col-span-9">{a ? <>
        <div className="grid grid-cols-4 gap-2 mb-3">{[["Cash", fmt(a.cash)], ["Equity", fmt(a.equity)], ["P&L", fmt(a.pnl), a.pnl], ["Status", a.status]].map(([l, v, s]) => <div key={l} className="card p-2"><div className="text-[10px] text-slate-500">{l} · PAPER/SIMULATED</div><div className={`num text-lg ${s != null ? pnlColor(s) : ""}`}>{v}</div></div>)}</div>
        <div className="flex gap-2 mb-3 flex-wrap">
          <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/pause`))}>Pause</button><button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/resume`))}>Resume</button>
          <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/stop`))}>Stop</button><button className="btn border-down text-down" onClick={act(() => P(`/api/paper/accounts/${aid}/control/kill`))}>KILL SWITCH</button>
          <span className="ml-auto flex gap-1"><select className="bg-panel border border-line rounded px-1 text-sm" value={sid} onChange={(e) => setSid(e.target.value)}><option value="">Strategy…</option>{strats.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}</select>
            <button className="btn btn-ai" disabled={!sid} onClick={act(() => P(`/api/paper/accounts/${aid}/deploy`, { strategy_id: Number(sid) }))}>Deploy</button><button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/step`))}>Evaluate now</button></span></div>
        <ErrorBox err={err} />{note && <div className="text-sm text-ai mb-2">{note}</div>}
        <div className="flex gap-2 mb-3 text-sm"><input className="bg-panel border border-line rounded px-2 w-28" value={o.symbol} onChange={(e) => setO({ ...o, symbol: e.target.value })} /><select className="bg-panel border border-line rounded" value={o.side} onChange={(e) => setO({ ...o, side: e.target.value })}><option>BUY</option><option>SELL</option></select>
          <input type="number" className="bg-panel border border-line rounded px-2 w-24 num" value={o.qty} onChange={(e) => setO({ ...o, qty: Number(e.target.value) })} /><button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/orders`, o))}>Place simulated order</button></div>
        <table className="w-full text-sm num card"><thead className="text-slate-500 text-left"><tr><th className="p-2">Symbol</th><th>Qty</th><th>Avg</th><th>Last</th><th>Unrealized</th><th>Realized</th></tr></thead><tbody>
          {a.positions.map((p) => <tr key={p.symbol} className="border-t border-line"><td className="p-2">{p.symbol}</td><td>{p.qty}</td><td>{fmt(p.avg_price)}</td><td>{fmt(p.last)}</td><td className={pnlColor(p.unrealized)}>{fmt(p.unrealized)}</td><td className={pnlColor(p.realized)}>{fmt(p.realized)}</td></tr>)}</tbody></table>
        <div className="text-xs text-slate-500 mt-3 mb-1">FILLS</div>{a.orders?.map((x) => <div key={x.id} className="num text-xs"><span className={x.side === "BUY" ? "text-up" : "text-down"}>{x.side}</span> {x.qty} {x.symbol} @ {fmt(x.fill_price)} · {x.reason} · {x.label}</div>)}
      </> : <p className="text-slate-500 text-sm">Create or select a simulated account.</p>}</div>
    </div>);
}
