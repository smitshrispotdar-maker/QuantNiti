import React, { useEffect, useState } from "react";
import { api } from "../api.jsx";
export default function Journal({ saved }) {
  const [rows, setRows] = useState([]); const [rec, setRec] = useState(""); const [rev, setRev] = useState({});
  const load = () => api("/api/journal").then(setRows).catch(() => {}); useEffect(() => { load(); }, []);
  const add = async () => { const ev = await api("/api/market/research/BTC-USD").catch(() => ({})); await api("/api/journal", { method: "POST", body: { strategy_id: saved?.id, recommendation: rec, evidence: ev.facts || {} } }); setRec(""); load(); };
  return (<div className="max-w-3xl">
    <div className="flex gap-2 mb-3"><input className="flex-1 bg-panel border border-line rounded px-2" value={rec} onChange={(e) => setRec(e.target.value)} placeholder="Record a decision or recommendation (snapshots current evidence)" /><button className="btn btn-ai" disabled={!rec} onClick={add}>Log decision</button></div>
    {rows.map((j) => <div key={j.id} className="card p-3 mb-2 text-sm"><div className="text-xs text-slate-500 num">{j.created_at.slice(0, 16)} · strategy {j.strategy_id ?? "—"} v{j.strategy_version ?? "—"}</div><p>{j.recommendation}</p>
      <pre className="num text-[10px] text-slate-500">{JSON.stringify(j.evidence)}</pre>
      {j.outcome_review ? <p className="text-ai">Outcome: {j.outcome_review}</p> : <div className="flex gap-2 mt-1"><input className="flex-1 bg-ink border border-line rounded px-2" placeholder="Outcome review…" value={rev[j.id] || ""} onChange={(e) => setRev({ ...rev, [j.id]: e.target.value })} /><button className="btn" onClick={async () => { await api(`/api/journal/${j.id}/review`, { method: "POST", body: { outcome_review: rev[j.id] } }); load(); }}>Save review</button></div>}</div>)}</div>);
}
