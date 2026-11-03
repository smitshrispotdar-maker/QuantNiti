import React, { useEffect, useState } from "react";
import { api, fmt, ErrorBox } from "../api.jsx";
import StrategyLineage from "../components/lineage/StrategyLineage";

const DECISION_TYPES = [
  "strategy_hypothesis", "research_finding", "backtest_review", "risk_review",
  "strategy_approval", "strategy_rejection", "strategy_modification",
  "paper_trading_review", "general_note"
];

const STATUSES = ["draft", "under_review", "approved", "rejected", "superseded", "completed"];

export default function Journal({ saved }) {
  const [rows, setRows] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({
    strategy_id: saved?.id || "",
    status: "",
    decision_type: "",
  });
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    title: "",
    decision_type: "general_note",
    status: "draft",
    strategy_id: saved?.id || "",
    strategy_version: saved?.version || "",
    conversation_id: "",
    backtest_run_id: "",
    research_run_id: "",
    deployment_id: "",
    hypothesis_rationale: "",
    evidence_summary: "",
    risks_assumptions: "",
    decision_next_steps: "",
    expected_outcome: "",
    actual_outcome: "",
    recommendation: "",
    evidence: {},
  });
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== "")),
      });
      const data = await api(`/api/journal?${params}`);
      setRows(data.items);
      setTotal(data.total);
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, pageSize, filters]);

  const resetForm = () => {
    setForm({
      title: "",
      decision_type: "general_note",
      status: "draft",
      strategy_id: saved?.id || "",
      strategy_version: saved?.version || "",
      conversation_id: "",
      backtest_run_id: "",
      research_run_id: "",
      deployment_id: "",
      hypothesis_rationale: "",
      evidence_summary: "",
      risks_assumptions: "",
      decision_next_steps: "",
      expected_outcome: "",
      actual_outcome: "",
      recommendation: "",
      evidence: {},
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const endpoint = editingId ? `/api/journal/${editingId}` : "/api/journal";
      const method = editingId ? "PATCH" : "POST";
      await api(endpoint, { method, body: form });
      resetForm();
      load();
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (entry) => {
    setEditingId(entry.id);
    setForm({
      title: entry.title,
      decision_type: entry.decision_type,
      status: entry.status,
      strategy_id: entry.strategy_id || "",
      strategy_version: entry.strategy_version || "",
      conversation_id: entry.conversation_id || "",
      backtest_run_id: entry.backtest_run_id || "",
      research_run_id: entry.research_run_id || "",
      deployment_id: entry.deployment_id || "",
      hypothesis_rationale: entry.hypothesis_rationale || "",
      evidence_summary: entry.evidence_summary || "",
      risks_assumptions: entry.risks_assumptions || "",
      decision_next_steps: entry.decision_next_steps || "",
      expected_outcome: entry.expected_outcome || "",
      actual_outcome: entry.actual_outcome || "",
      recommendation: entry.recommendation || "",
      evidence: entry.evidence || {},
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this journal entry?")) return;
    try {
      await api(`/api/journal/${id}`, { method: "DELETE" });
      load();
    } catch (e) {
      setErr(e);
    }
  };

  const handleReview = async (id, review) => {
    try {
      await api(`/api/journal/${id}/review`, { method: "POST", body: { outcome_review: review } });
      load();
    } catch (e) {
      setErr(e);
    }
  };

  const DecisionTypeBadge = ({ type }) => (
    <span className="badge text-ai border-ai/40 text-[10px]">{type.replace(/_/g, " ")}</span>
  );

  const StatusBadge = ({ status }) => {
    const colors = {
      draft: "text-slate-400 border-slate-400/50",
      under_review: "text-amber-400 border-amber-400/50",
      approved: "text-up border-up/50",
      rejected: "text-down border-down/50",
      superseded: "text-slate-400 border-slate-400/50",
      completed: "text-ai border-ai/50",
    };
    return <span className={`badge ${colors[status] || "text-slate-400 border-line"} text-[10px]`}>{status}</span>;
  };

  return (
    <div className="max-w-5xl">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">Decision Journal</h2>
        <button className="btn btn-ai" onClick={() => { resetForm(); setShowForm(true); }}>
          + New Entry
        </button>
      </div>

      {/* Filters */}
      <div className="card p-3 mb-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.strategy_id}
            onChange={(e) => setFilters({ ...filters, strategy_id: e.target.value })}
          >
            <option value="">All Strategies</option>
            <option value={1}>Strategy 1</option>
          </select>
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">All Statuses</option>
            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.decision_type}
            onChange={(e) => setFilters({ ...filters, decision_type: e.target.value })}
          >
            <option value="">All Types</option>
            {DECISION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
      </div>

      {/* Strategy Lineage for selected strategy */}
      {filters.strategy_id && (
        <div className="mb-3">
          <StrategyLineage strategyId={parseInt(filters.strategy_id)} />
        </div>
      )}

      {showForm && (
        <div className="card p-3 mb-3">
          <h3 className="font-medium mb-2">{editingId ? "Edit Entry" : "New Journal Entry"}</h3>
          <ErrorBox err={err} />
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Title *</label>
                <input
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  required
                  placeholder="Brief title for this entry"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Decision Type</label>
                <select
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.decision_type}
                  onChange={(e) => setForm({ ...form, decision_type: e.target.value })}
                >
                  {DECISION_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Status</label>
                <select
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Strategy ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.strategy_id}
                  onChange={(e) => setForm({ ...form, strategy_id: e.target.value })}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Strategy Version</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.strategy_version}
                  onChange={(e) => setForm({ ...form, strategy_version: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Conversation ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.conversation_id}
                  onChange={(e) => setForm({ ...form, conversation_id: e.target.value })}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Backtest Run ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.backtest_run_id}
                  onChange={(e) => setForm({ ...form, backtest_run_id: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Research Run ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.research_run_id}
                  onChange={(e) => setForm({ ...form, research_run_id: e.target.value })}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Deployment ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.deployment_id}
                  onChange={(e) => setForm({ ...form, deployment_id: e.target.value })}
                  placeholder="Optional"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Hypothesis / Rationale</label>
              <textarea
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                value={form.hypothesis_rationale}
                onChange={(e) => setForm({ ...form, hypothesis_rationale: e.target.value })}
                rows={3}
                placeholder="What is the hypothesis or rationale behind this decision?"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Evidence Summary</label>
              <textarea
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                value={form.evidence_summary}
                onChange={(e) => setForm({ ...form, evidence_summary: e.target.value })}
                rows={3}
                placeholder="Summary of evidence supporting this decision"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Risks & Assumptions</label>
                <textarea
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.risks_assumptions}
                  onChange={(e) => setForm({ ...form, risks_assumptions: e.target.value })}
                  rows={3}
                  placeholder="Key risks and assumptions"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Decision & Next Steps</label>
                <textarea
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.decision_next_steps}
                  onChange={(e) => setForm({ ...form, decision_next_steps: e.target.value })}
                  rows={3}
                  placeholder="Decision made and next steps"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Expected Outcome</label>
                <textarea
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.expected_outcome}
                  onChange={(e) => setForm({ ...form, expected_outcome: e.target.value })}
                  rows={2}
                  placeholder="What outcome is expected?"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Actual Outcome</label>
                <textarea
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={form.actual_outcome}
                  onChange={(e) => setForm({ ...form, actual_outcome: e.target.value })}
                  rows={2}
                  placeholder="What actually happened? (fill after outcome observed)"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Recommendation / Summary</label>
              <textarea
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                value={form.recommendation}
                onChange={(e) => setForm({ ...form, recommendation: e.target.value })}
                rows={2}
                placeholder="Brief recommendation or summary"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Evidence (JSON)</label>
              <textarea
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm font-mono text-[10px]"
                value={JSON.stringify(form.evidence, null, 2)}
                onChange={(e) => {
                  try {
                    setForm({ ...form, evidence: JSON.parse(e.target.value) });
                  } catch {}
                }}
                rows={4}
                placeholder='{"key": "value"}'
              />
            </div>
            <div className="flex gap-2">
              <button className="btn btn-ai" type="submit" disabled={loading}>
                {loading ? "Saving..." : (editingId ? "Update" : "Create")}
              </button>
              <button className="btn" type="button" onClick={resetForm}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <ErrorBox err={err} />

      {loading && rows.length === 0 && <div className="text-center py-8 text-slate-500">Loading...</div>}

      {!loading && rows.length === 0 && (
        <div className="card p-8 text-center text-slate-500">
          <p className="mb-2">No journal entries yet</p>
          <button className="btn btn-ai" onClick={() => { resetForm(); setShowForm(true); }}>Create your first entry</button>
        </div>
      )}

      {!loading && rows.length > 0 && (
        <>
          <div className="space-y-2">
            {rows.map((j) => (
              <div key={j.id} className="card p-3">
                <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-medium">{j.title}</h3>
                    <DecisionTypeBadge type={j.decision_type} />
                    <StatusBadge status={j.status} />
                  </div>
                  <div className="text-xs text-slate-500">
                    {new Date(j.created_at).toLocaleDateString()} · {new Date(j.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2 text-xs text-slate-400">
                  {j.strategy_id && <span>Strategy: {j.strategy_id} v{j.strategy_version}</span>}
                  {j.conversation_id && <span>Conv: #{j.conversation_id}</span>}
                  {j.backtest_run_id && <span>Backtest: #{j.backtest_run_id}</span>}
                  {j.research_run_id && <span>Research: #{j.research_run_id}</span>}
                  {j.deployment_id && <span>Deployment: #{j.deployment_id}</span>}
                </div>
                {j.hypothesis_rationale && (
                  <p className="text-sm mb-1">{j.hypothesis_rationale}</p>
                )}
                {j.evidence_summary && (
                  <p className="text-sm mb-1 text-slate-300">{j.evidence_summary}</p>
                )}
                {j.risks_assumptions && (
                  <p className="text-sm mb-1 text-amber-400">{j.risks_assumptions}</p>
                )}
                {j.decision_next_steps && (
                  <p className="text-sm mb-1 text-ai">{j.decision_next_steps}</p>
                )}
                {j.expected_outcome && (
                  <p className="text-sm mb-1 text-up">{j.expected_outcome}</p>
                )}
                {j.actual_outcome && (
                  <p className="text-sm mb-1 text-down">{j.actual_outcome}</p>
                )}
                {j.recommendation && (
                  <p className="text-sm mb-1 font-medium">{j.recommendation}</p>
                )}
                {j.evidence && Object.keys(j.evidence).length > 0 && (
                  <pre className="num text-[10px] text-slate-500 mt-2 overflow-auto max-h-40">
                    {JSON.stringify(j.evidence, null, 2)}
                  </pre>
                )}
                {j.outcome_review && (
                  <p className="text-sm mt-2 text-ai">Outcome Review: {j.outcome_review}</p>
                )}
                <div className="flex gap-2 mt-3 pt-2 border-t border-line">
                  <button className="btn" onClick={() => handleEdit(j)}>Edit</button>
                  <button className="btn border-down text-down" onClick={() => handleDelete(j.id)}>Delete</button>
                  {!j.outcome_review && (
                    <form onSubmit={(e) => { e.preventDefault(); handleReview(j.id, e.target.elements[0].value); e.target.reset(); }}>
                      <input className="flex-1 bg-ink border border-line rounded px-2 py-1 text-sm" placeholder="Add outcome review…" required />
                      <button className="btn btn-ai" type="submit">Save Review</button>
                    </form>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-2 mt-3">
            {page > 1 && <button className="btn" onClick={() => setPage(page - 1)}>Previous</button>}
            <span className="flex items-center text-sm text-slate-400">Page {page} of {Math.ceil(total / pageSize)} (Total: {total})</span>
            {page * pageSize < total && <button className="btn" onClick={() => setPage(page + 1)}>Next</button>}
          </div>
        </>
      )}
    </div>
  );
}