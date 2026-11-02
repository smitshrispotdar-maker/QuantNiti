import React, { useState } from "react";
import { api, ErrorBox } from "../api.jsx";
export default function Studio({ setDraft, draft, setSaved, saved }) {
  const [cid, setCid] = useState(null); const [msgs, setMsgs] = useState([]); const [text, setText] = useState(""); const [err, setErr] = useState(null);
  const send = async () => {
    if (!text.trim()) return; setErr(null);
    try { const r = await api("/api/strategies/chat", { method: "POST", body: { conversation_id: cid, message: text } }); setCid(r.conversation_id); setMsgs(r.messages); setDraft(r.draft_spec); setText(""); } catch (e) { setErr(e); }
  };
  const save = async () => { try { setSaved(await api("/api/strategies", { method: "POST", body: { spec: draft } })); } catch (e) { setErr(e); } };
  return (
    <div className="grid grid-cols-2 gap-3 h-[80vh]">
      <div className="card p-3 flex flex-col"><div className="flex-1 overflow-auto space-y-2">
        {!msgs.length && <p className="text-sm text-slate-500">Try: "Buy BTC when EMA 20 crosses above EMA 50, exit on cross below, stop loss 5%, position size 30%"</p>}
        {msgs.map((m, i) => <div key={i} className={`text-sm p-2 rounded ${m.role === "user" ? "bg-line ml-8" : "border border-ai/30 mr-8"}`}>{m.text}
          {m.clarifications?.map((c, j) => <div key={j} className="text-amber-400 mt-1">? {c}</div>)}</div>)}</div>
        <ErrorBox err={err} /><div className="flex gap-2 mt-2"><input className="flex-1 bg-ink border border-line rounded px-2" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Describe a strategy…" /><button className="btn btn-ai" onClick={send}>Send</button></div></div>
      <div className="card p-3 overflow-auto"><div className="flex justify-between mb-2"><span className="text-xs text-ai">CANONICAL STRATEGY JSON v1.0</span>
        <button className="btn" disabled={!draft} onClick={save}>Save{saved ? ` (saved v${saved.version})` : ""}</button></div>
        <pre className="num text-xs text-slate-300">{draft ? JSON.stringify(draft, null, 2) : "No draft yet."}</pre></div>
    </div>);
}
