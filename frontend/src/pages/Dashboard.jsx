import React, { useEffect, useState } from "react";
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, watchlistApi, fmt, pnlColor, Badge, ErrorBox } from "../api.jsx";
const Candle = ({ x, y, width, height, payload }) => {   // custom candlestick: bar spans [low, high]; body drawn proportionally
  const { open, close, high, low } = payload; const up = close >= open, col = up ? "#00C853" : "#FF5252";
  const k = height / (high - low || 1), yo = y + (high - Math.max(open, close)) * k, hb = Math.max(1, Math.abs(close - open) * k);
  return <g><line x1={x + width / 2} x2={x + width / 2} y1={y} y2={y + height} stroke={col} /><rect x={x + 1} y={yo} width={Math.max(1, width - 2)} height={hb} fill={col} /></g>;
};

// Data Quality Panel Component
export function DataQualityPanel({ meta }) {
  const hasQuality = meta?.data_quality;
  const dq = hasQuality ? meta.data_quality : {};

  const statusColors = {
    LIVE: "text-up border-up/50",
    DELAYED: "text-amber-400 border-amber-400/50",
    SIMULATED: "text-ai border-ai/50",
    CACHED: "text-slate-400 border-slate-400/50",
    HISTORICAL: "text-slate-400 border-slate-400/50",
    UNAVAILABLE: "text-down border-down/50",
  };

  const getStatusClass = (status) => statusColors[status] || "text-slate-400 border-slate-400/50";

  const formatTimestamp = (ts) => {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", timeZoneName: "short"
      });
    } catch {
      return ts;
    }
  };

  const formatCacheAge = (seconds) => {
    if (seconds === null || seconds === undefined) return "—";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
    return `${Math.round(seconds / 86400)}d`;
  };

  if (!hasQuality) {
    return (
      <div className="card p-3 border-amber-500/30 bg-amber-500/5">
        <div className="flex items-center gap-2 mb-2">
          <svg className="w-5 h-5 text-ai" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 11a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-medium text-sm">Data Quality</span>
          <Badge status={meta?.status || "UNAVAILABLE"} />
          <span className={`badge ml-auto ${getStatusClass(meta?.source)}`}>{meta?.source}</span>
        </div>
        <p className="text-slate-400 text-sm">Quality information unavailable</p>
      </div>
    );
  }

  const hasIssues = dq.issues && dq.issues.length > 0;
  const hasGaps = dq.gaps && dq.gaps.length > 0;
  const hasDuplicates = dq.duplicates && dq.duplicates.length > 0;
  const hasWarnings = hasIssues || hasGaps || hasDuplicates;

  return (
    <div className={`card p-3 ${hasWarnings ? "border-amber-500/30 bg-amber-500/5" : "border-up/20 bg-up/5"}`}>
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-5 h-5 text-ai" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 11a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium text-sm">Data Quality</span>
        <Badge status={meta?.status || "UNAVAILABLE"} />
        <span className={`badge ml-auto ${getStatusClass(meta?.source)}`}>{meta?.source}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Bars</div>
          <div className="num font-medium">{dq.bar_count ?? 0}</div>
        </div>
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Timeframe</div>
          <div className="font-medium">{meta?.timeframe ?? "—"}</div>
        </div>
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Last Bar</div>
          <div className="font-medium text-xs truncate">{formatTimestamp(meta?.last_bar)}</div>
        </div>
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Fetched</div>
          <div className="font-medium text-xs truncate">{formatTimestamp(meta?.fetched_at)}</div>
        </div>
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Cache</div>
          <div className="font-medium">{dq.cached ? "HIT" : "MISS"}</div>
        </div>
        <div className="p-2 bg-ink/50 rounded">
          <div className="text-slate-500 text-xs">Cache Age</div>
          <div className="font-medium" data-testid="cache-age">{formatCacheAge(dq.cache_age_seconds)}</div>
        </div>
      </div>

      {hasWarnings && (
        <div className="border-t border-amber-500/20 pt-3">
          <div className="text-amber-400 text-sm font-medium mb-2">Quality Warnings</div>
          <div className="space-y-2 text-xs">
            {dq.issues && dq.issues.length > 0 && (
              <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded">
                <div className="font-medium text-amber-400 mb-1">OHLC Issues ({dq.issues.length})</div>
                <ul className="list-disc list-inside space-y-1 text-slate-300">
                  {dq.issues.slice(0, 3).map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                  {dq.issues.length > 3 && <li className="text-amber-400">+{dq.issues.length - 3} more...</li>}
                </ul>
              </div>
            )}
            {dq.gaps && dq.gaps.length > 0 && (
              <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded">
                <div className="font-medium text-amber-400 mb-1">Timestamp Gaps ({dq.gaps.length})</div>
                <ul className="list-disc list-inside space-y-1 text-slate-300">
                  {dq.gaps.slice(0, 3).map((gap, i) => (
                    <li key={i}>{gap}</li>
                  ))}
                  {dq.gaps.length > 3 && <li className="text-amber-400">+{dq.gaps.length - 3} more...</li>}
                </ul>
              </div>
            )}
            {dq.duplicates && dq.duplicates.length > 0 && (
              <div className="p-2 bg-amber-500/10 border border-amber-500/20 rounded">
                <div className="font-medium text-amber-400 mb-1">Duplicate Timestamps ({dq.duplicates.length})</div>
                <ul className="list-disc list-inside space-y-1 text-slate-300">
                  {dq.duplicates.slice(0, 3).map((dup, i) => (
                    <li key={i}>{dup}</li>
                  ))}
                  {dq.duplicates.length > 3 && <li className="text-amber-400">+{dq.duplicates.length - 3} more...</li>}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [wl, setWl] = useState([]); const [sym, setSym] = useState("BTC-USD"); const [tf, setTf] = useState("1d");
  const [d, setD] = useState(null); const [ov, setOv] = useState({ ema20: true, sma20: false, bb: false }); const [sub, setSub] = useState("rsi");
  const [res, setRes] = useState(null);
  const [addSymbol, setAddSymbol] = useState(""); const [addError, setAddError] = useState("");
  
  useEffect(() => { watchlistApi.get().then(setWl).catch(() => {}); }, []);
  useEffect(() => { setD(null); api(`/api/market/bars/${sym}?timeframe=${tf}&limit=120`).then(setD).catch(() => {}); api(`/api/market/research/${sym}?timeframe=${tf}`).then(setRes).catch(() => {}); }, [sym, tf]);
  
  const handleAddSymbol = async () => {
    if (!addSymbol.trim()) return;
    setAddError("");
    try {
      await watchlistApi.add(addSymbol.trim().toUpperCase());
      setAddSymbol("");
      setWl(await watchlistApi.get());
    } catch (e) {
      setAddError(e.detail || "Failed to add symbol");
    }
  };
  
  const handleRemoveSymbol = async (symbol) => {
    try {
      await watchlistApi.remove(symbol);
      setWl(await watchlistApi.get());
    } catch (e) {
      setAddError(e.detail || "Failed to remove symbol");
    }
  };
  const bars = d?.bars.map((b) => ({ ...b, range: [b.low, b.high], t: b.ts.slice(5, 16) })) || [];
  return (
    <div className="grid grid-cols-12 gap-3">
      <div className="card col-span-3 p-2">
        <div className="flex gap-2 mb-2">
          <input className="flex-1 bg-ink border border-line rounded px-2 py-1 text-sm" placeholder="Add symbol (e.g., AAPL)" value={addSymbol}
            onChange={(e) => { setAddSymbol(e.target.value); setAddError(""); }}
            onKeyDown={(e) => e.key === "Enter" && handleAddSymbol()} />
          <button className="btn btn-ai" onClick={handleAddSymbol} disabled={!addSymbol.trim()}>Add</button>
        </div>
        {addError && <p className="text-down text-xs mb-2">{addError}</p>}
        {wl.map((w) => (<button key={w.symbol} onClick={() => setSym(w.symbol)} className={`w-full flex justify-between px-2 py-1.5 text-sm rounded ${sym === w.symbol ? "bg-line" : ""}`}>
          <span>{w.symbol}</span>
          <span className="flex items-center gap-1">
            <span className="num">{fmt(w.price)} <span className={pnlColor(w.change_pct)}>{fmt(w.change_pct)}%</span></span>
            <button onClick={(e) => { e.stopPropagation(); handleRemoveSymbol(w.symbol); }} className="text-slate-400 hover:text-down p-1" title="Remove">✕</button>
          </span></button>))}
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
        {d && <DataQualityPanel meta={d.meta} />}
      </div>
      {res && <div className="col-span-12 grid grid-cols-2 gap-3">
        <div className="card p-3"><div className="text-xs text-slate-400 mb-2">COMPUTED FACTS</div>
          <div className="grid grid-cols-4 gap-2">{Object.entries(res.facts).map(([k, v]) => <div key={k}><div className="text-[10px] text-slate-500">{k}</div><div className="num">{v}</div></div>)}</div></div>
        <div className="card p-3 border-ai/40"><div className="text-xs text-ai mb-2">{res.label}</div>
          <p className="text-sm">{res.interpretations.market_analyst}</p>
          <div className="grid grid-cols-2 gap-2 my-2 text-xs"><ul className="text-up">{res.interpretations.bull.map((b, i) => <li key={i}>▲ {b}</li>)}</ul><ul className="text-down">{res.interpretations.bear.map((b, i) => <li key={i}>▼ {b}</li>)}</ul></div>
          <p className="text-xs text-slate-400">{res.interpretations.risk_analyst}</p><p className="text-sm mt-1 text-ai">{res.interpretations.strategy_manager}</p></div></div>}
    </div>
  );
}