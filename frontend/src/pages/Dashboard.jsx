import React, { useEffect, useState } from "react";
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, fmt, pnlColor, Badge } from "../api.jsx";
const Candle = ({ x, y, width, height, payload }) => {   // custom candlestick: bar spans [low, high]; body drawn proportionally
  const { open, close, high, low } = payload; const up = close >= open, col = up ? "#00C853" : "#FF5252";
  const k = height / (high - low || 1), yo = y + (high - Math.max(open, close)) * k, hb = Math.max(1, Math.abs(close - open) * k);
  return <g><line x1={x + width / 2} x2={x + width / 2} y1={y} y2={y + height} stroke={col} /><rect x={x + 1} y={yo} width={Math.max(1, width - 2)} height={hb} fill={col} /></g>;
};
export default function Dashboard() {
  const [wl, setWl] = useState([]); const [sym, setSym] = useState("BTC-USD"); const [tf, setTf] = useState("1d");
  const [d, setD] = useState(null); const [ov, setOv] = useState({ ema20: true, sma20: false, bb: false }); const [sub, setSub] = useState("rsi");
  const [q, setQ] = useState(""); const [res, setRes] = useState(null);
  useEffect(() => { api("/api/market/watchlist").then(setWl).catch(() => {}); }, []);
  useEffect(() => { setD(null); api(`/api/market/bars/${sym}?timeframe=${tf}&limit=120`).then(setD).catch(() => {}); api(`/api/market/research/${sym}?timeframe=${tf}`).then(setRes).catch(() => {}); }, [sym, tf]);
  const bars = d?.bars.map((b) => ({ ...b, range: [b.low, b.high], t: b.ts.slice(5, 16) })) || [];
  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="card col-span-3 p-2">
        <input className="w-full bg-ink border border-line rounded px-2 py-1 text-sm mb-2" placeholder="Search instrument" value={q}
          onChange={(e) => { setQ(e.target.value); e.target.value && api(`/api/market/search?q=${e.target.value}`).then((r) => r[0] && setSym(r[0])); }} />
        {wl.map((w) => (<button key={w.symbol} onClick={() => setSym(w.symbol)} className={`w-full flex justify-between px-2 py-1.5 text-sm rounded ${sym === w.symbol ? "bg-line" : ""}`}>
          <span>{w.symbol}</span><span className="num">{fmt(w.price)} <span className={pnlColor(w.change_pct)}>{fmt(w.change_pct)}%</span></span></button>))}
      </div>
      <div className="card col-span-9 p-3">
        <div className="flex items-center gap-2 mb-2 text-sm">
          <b>{sym}</b>{d && <><Badge status={d.meta.status} /><span className="badge text-slate-400 border-line">{d.meta.source}</span><span className="num text-xs text-slate-500">last bar {d.meta.last_bar.slice(0, 16)}</span></>}
          <span className="ml-auto flex gap-1">{["5m", "15m", "1h", "1d"].map((t) => <button key={t} onClick={() => setTf(t)} className={`btn ${tf === t ? "btn-ai" : ""}`}>{t}</button>)}</span></div>
        <div className="flex gap-2 mb-2 text-xs">{[["ema20", "EMA20"], ["sma20", "SMA20"], ["bb", "Bollinger"]].map(([k, l]) => <label key={k}><input type="checkbox" checked={ov[k]} onChange={() => setOv({ ...ov, [k]: !ov[k] })} /> {l}</label>)}
          <span className="ml-auto">{["rsi", "macd", "volume"].map((s) => <button key={s} onClick={() => setSub(s)} className={`btn mx-0.5 ${sub === s ? "btn-ai" : ""}`}>{s.toUpperCase()}</button>)}</span></div>
        <ResponsiveContainer width="100%" height={300}><ComposedChart data={bars}><CartesianGrid stroke="#1E222D" /><XAxis dataKey="t" tick={{ fontSize: 10 }} minTickGap={40} /><YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} orientation="right" />
          <Tooltip contentStyle={{ background: "#121620", border: "1px solid #1E222D" }} />
          <Bar dataKey="range" shape={<Candle />} isAnimationActive={false} />
          {ov.ema20 && <Line dataKey="ema20" dot={false} stroke="#00E5FF" strokeWidth={1.2} isAnimationActive={false} />}
          {ov.sma20 && <Line dataKey="sma20" dot={false} stroke="#FFC107" strokeWidth={1.2} isAnimationActive={false} />}
          {ov.bb && <><Line dataKey="bb_upper" dot={false} stroke="#7C4DFF" isAnimationActive={false} /><Line dataKey="bb_lower" dot={false} stroke="#7C4DFF" isAnimationActive={false} /></>}</ComposedChart></ResponsiveContainer>
        <ResponsiveContainer width="100%" height={110}><ComposedChart data={bars}><XAxis dataKey="t" hide /><YAxis tick={{ fontSize: 10 }} orientation="right" domain={sub === "rsi" ? [0, 100] : ["auto", "auto"]} /><Tooltip contentStyle={{ background: "#121620", border: "1px solid #1E222D" }} />
          {sub === "rsi" && <Line dataKey="rsi" dot={false} stroke="#00E5FF" isAnimationActive={false} />}
          {sub === "macd" && <><Bar dataKey="macd_hist" fill="#00C853" isAnimationActive={false} /><Line dataKey="macd" dot={false} stroke="#00E5FF" isAnimationActive={false} /><Line dataKey="macd_signal" dot={false} stroke="#FFC107" isAnimationActive={false} /></>}
          {sub === "volume" && <Bar dataKey="volume" fill="#334155" isAnimationActive={false} />}</ComposedChart></ResponsiveContainer>
      </div>
      {res && <div className="col-span-12 grid grid-cols-2 gap-3">
        <div className="card p-3"><div className="text-xs text-slate-400 mb-2">COMPUTED FACTS</div>
          <div className="grid grid-cols-4 gap-2">{Object.entries(res.facts).map(([k, v]) => <div key={k}><div className="text-[10px] text-slate-500">{k}</div><div className="num">{v}</div></div>)}</div></div>
        <div className="card p-3 border-ai/40"><div className="text-xs text-ai mb-2">{res.label}</div>
          <p className="text-sm">{res.interpretations.market_analyst}</p>
          <div className="grid grid-cols-2 gap-2 my-2 text-xs"><ul className="text-up">{res.interpretations.bull.map((b, i) => <li key={i}>▲ {b}</li>)}</ul><ul className="text-down">{res.interpretations.bear.map((b, i) => <li key={i}>▼ {b}</li>)}</ul></div>
          <p className="text-xs text-slate-400">{res.interpretations.risk_analyst}</p><p className="text-sm mt-1 text-ai">{res.interpretations.strategy_manager}</p></div></div>}
    </div>);
}
