import React, { useState, useEffect } from "react";
import { api, ErrorBox, Badge } from "../api.jsx";

export default function Studio({ setDraft, draft, setSaved, saved }) {
  const [cid, setCid] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [err, setErr] = useState(null);
  const [convs, setConvs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showConvs, setShowConvs] = useState(false);
  const [newConvTitle, setNewConvTitle] = useState("");
  const [renamingCid, setRenamingCid] = useState(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await api("/api/strategies/conversations");
      setConvs(data);
    } catch (e) {
      console.error("Failed to load conversations:", e);
    }
  };

  const loadConversation = async (id) => {
    setLoading(true);
    try {
      const data = await api(`/api/strategies/chat/${id}`);
      setCid(data.id);
      setMsgs(data.messages || []);
      setDraft(data.draft_spec || null);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const newConversation = async () => {
    setCid(null);
    setMsgs([]);
    setDraft(null);
    setSaved(null);
    setShowConvs(false);
  };

  const deleteConversation = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await api(`/api/strategies/conversations/${id}`, { method: "DELETE" });
      if (cid === id) {
        newConversation();
      }
      loadConversations();
    } catch (e) {
      setErr(e);
    }
  };

  const startRename = (id, title) => {
    setRenamingCid(id);
    setNewConvTitle(title);
  };

  const saveRename = async (id) => {
    if (!newConvTitle.trim()) return;
    try {
      await api(`/api/strategies/conversations/${id}/rename`, {
        method: "POST",
        body: { title: newConvTitle },
      });
      setRenamingCid(null);
      loadConversations();
    } catch (e) {
      setErr(e);
    }
  };

  const send = async () => {
    if (!text.trim()) return;
    setErr(null);
    setLoading(true);
    try {
      const r = await api("/api/strategies/chat", {
        method: "POST",
        body: { conversation_id: cid, message: text },
      });
      setCid(r.conversation_id);
      setMsgs(r.messages);
      setDraft(r.draft_spec);
      setText("");
      loadConversations(); // Refresh list to show updated title/count
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async () => {
    if (!draft) return;
    setErr(null);
    setLoading(true);
    try {
      const result = await api("/api/backtests", {
        method: "POST",
        body: { strategy_id: saved?.id || 0, initial_cash: 100000 },
      });
      // Add backtest result to conversation
      await api("/api/strategies/chat", {
        method: "POST",
        body: {
          conversation_id: cid,
          message: `Backtest completed: Return ${result.metrics.total_return_pct}%, Drawdown ${result.metrics.max_drawdown_pct}%, Trades ${result.metrics.trades}`,
        },
      });
      // Reload to show backtest result in chat
      if (cid) loadConversation(cid);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const deployPaper = async () => {
    if (!draft || !saved) {
      setErr({ detail: { validation: { passed: false, errors: ["Please save the strategy first"] } } });
      return;
    }
    if (!window.confirm("Deploy this strategy to paper trading? This will create a live simulated deployment.")) return;
    setErr(null);
    setLoading(true);
    try {
      await api(`/api/paper/accounts/${1}/deployments`, {
        method: "POST",
        body: { strategy_id: saved.id },
      });
      await api("/api/strategies/chat", {
        method: "POST",
        body: {
          conversation_id: cid,
          message: "Deployed strategy to paper trading.",
        },
      });
      if (cid) loadConversation(cid);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const explainStrategy = async () => {
    if (!draft) return;
    setErr(null);
    try {
      const r = await api("/api/strategies/chat", {
        method: "POST",
        body: { conversation_id: cid, message: "Explain the current strategy" },
      });
      setMsgs(r.messages);
      setDraft(r.draft_spec);
    } catch (e) {
      setErr(e);
    }
  };

  const saveStrategy = async () => {
    if (!draft) return;
    try {
      const savedStrategy = await api("/api/strategies", { method: "POST", body: { spec: draft } });
      setSaved(savedStrategy);
    } catch (e) {
      setErr(e);
    }
  };

  // Format conversation title for display
  const getConvTitle = (c) => {
    if (c.title) return c.title;
    if (c.messages && c.messages.length > 0) {
      const firstUserMsg = c.messages.find(m => m.role === "user");
      if (firstUserMsg) return firstUserMsg.text.slice(0, 40) + (firstUserMsg.text.length > 40 ? "…" : "");
    }
    return "New conversation";
  };

  const formatTime = (ts) => {
    if (!ts) return "";
    const d = new Date(ts);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="flex h-[80vh]">
      {/* Conversations Sidebar */}
      <aside className={`w-64 border-r border-line bg-panel transition-all ${showConvs ? "" : "hidden md:block"}`}>
        <div className="flex items-center justify-between p-2 border-b border-line">
          <span className="text-xs text-ai font-medium">CONVERSATIONS</span>
          <button className="md:hidden text-slate-400" onClick={() => setShowConvs(false)}>×</button>
        </div>
        <button className="btn btn-ai w-full mx-2 mb-2 text-xs" onClick={newConversation}>
          + New Conversation
        </button>
        <div className="flex-1 overflow-auto space-y-1 px-2">
          {convs.length === 0 && (
            <p className="text-xs text-slate-500 p-2">No conversations yet</p>
          )}
          {convs.map((c) => (
            <div
              key={c.id}
              className={`group relative px-2 py-1.5 rounded text-sm cursor-pointer transition-colors ${
                cid === c.id ? "bg-ai/10 text-ai" : "text-slate-400 hover:text-slate-200 hover:bg-line"
              }`}
              onClick={() => loadConversation(c.id)}
            >
              <div className="flex items-center justify-between">
                <span className="truncate">{getConvTitle(c)}</span>
                {cid === c.id && <span className="text-[10px] text-ai">ACTIVE</span>}
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500 mt-0.5">
                <span>{c.message_count} msgs</span>
                <span>{formatTime(c.updated_at)}</span>
              </div>
              <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5">
                {cid !== c.id && (
                  <button
                    className="p-1 text-slate-400 hover:text-ai rounded"
                    onClick={(e) => { e.stopPropagation(); startRename(c.id, getConvTitle(c)); }}
                    title="Rename"
                  >
                    ✏️
                  </button>
                )}
                <button
                  className="p-1 text-slate-400 hover:text-down rounded"
                  onClick={(e) => { e.stopPropagation(); deleteConversation(c.id, e); }}
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
              {renamingCid === c.id && (
                <div className="mt-1 flex gap-1">
                  <input
                    className="flex-1 bg-ink border border-ai rounded px-1 text-xs"
                    value={newConvTitle}
                    onChange={(e) => setNewConvTitle(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveRename(c.id)}
                    autoFocus
                  />
                  <button className="btn btn-ai text-xs" onClick={() => saveRename(c.id)}>OK</button>
                  <button className="btn text-xs" onClick={() => setRenamingCid(null)}>Cancel</button>
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>

      {/* Mobile Conversations Toggle */}
      <button className="md:hidden fixed bottom-4 right-4 z-50 btn btn-ai" onClick={() => setShowConvs(!showConvs)}>
        {showConvs ? "Close" : "Conversations"}
      </button>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="card p-3 flex flex-col h-full">
            <div className="flex-1 overflow-auto space-y-2">
              {!msgs.length && !cid && (
                <p className="text-sm text-slate-500 text-center py-8">
                  Start a conversation or select one from the sidebar.<br />
                  <span className="text-xs">Try: "Buy BTC when EMA 20 crosses above EMA 50, exit on cross below, stop loss 5%, position size 30%"</span>
                </p>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={`text-sm p-2 rounded max-w-[80%] ${m.role === "user" ? "bg-line ml-auto" : "border border-ai/30"}`}>
                  {m.text}
                  {m.clarifications?.map((c, j) => (
                    <div key={j} className="text-amber-400 text-xs mt-1">⚠ {c}</div>
                  ))}
                </div>
              ))}
            </div>
            <ErrorBox err={err} />
            <div className="flex gap-2 mt-2">
              <input
                className="flex-1 bg-ink border border-line rounded px-2"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
                placeholder="Describe a strategy, or say 'run backtest', 'deploy', 'explain'…"
                disabled={loading}
              />
              <button className="btn btn-ai" onClick={send} disabled={loading || !text.trim()}>
                {loading ? "Sending…" : "Send"}
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="card p-3 border-t border-line flex flex-wrap gap-2">
          <button className="btn" onClick={runBacktest} disabled={!draft || loading}>
            ▶ Run Backtest
          </button>
          <button className="btn btn-ai" onClick={deployPaper} disabled={!saved || loading}>
            📈 Deploy to Paper
          </button>
          <button className="btn" onClick={explainStrategy} disabled={!draft || loading}>
            💡 Explain
          </button>
          <button className="btn" onClick={saveStrategy} disabled={!draft || loading}>
            💾 Save Strategy
          </button>
        </div>
      </div>

      {/* Right Panel - Draft Strategy */}
      <div className="w-72 border-l border-line bg-panel flex flex-col">
        <div className="flex justify-between items-center p-2 border-b border-line">
          <span className="text-xs text-ai font-medium">CANONICAL STRATEGY JSON v1.0</span>
          {cid && <span className="text-[10px] text-slate-400">Conv #{cid}</span>}
        </div>
        <div className="flex-1 overflow-auto p-2">
          <pre className="num text-[10px] text-slate-300">{draft ? JSON.stringify(draft, null, 2) : "No draft yet. Start chatting to build a strategy."}</pre>
        </div>
        <div className="p-2 border-t border-line">
          <button className="btn w-full" disabled={!draft || loading} onClick={saveStrategy}>
            Save Strategy {saved ? `v${saved.version}` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}