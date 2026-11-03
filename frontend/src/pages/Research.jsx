import React, { useEffect, useState } from "react";
import { api, fmt, Badge, ErrorBox } from "../api.jsx";
import StrategyLineage from "../components/lineage/StrategyLineage";
import ResearchComparison from "../components/research/ResearchComparison";
import ExportDialog from "../components/export/ExportDialog";

export default function Research() {
  const [runs, setRuns] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState({
    strategy_id: "",
    conversation_id: "",
    backtest_run_id: "",
    deployment_id: "",
  });
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [newResearch, setNewResearch] = useState({
    strategy_id: "",
    strategy_version: "",
    conversation_id: "",
    backtest_run_id: "",
    deployment_id: "",
  });
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedRunDetail, setSelectedRunDetail] = useState(null);
  const [showComparison, setShowComparison] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showSchedule, setShowSchedule] = useState(false);
  const [scheduleConfig, setScheduleConfig] = useState({
    enabled: false,
    cron_schedule: "0 6 * * *",
    strategies: [],
    symbols: [],
    timeframes: [],
    max_runs_per_day: 5,
  });
  const [scheduleLoading, setScheduleLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: 20,
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== "")),
      });
      const data = await api(`/api/research?${params}`);
      setRuns(data.items);
      setTotal(data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, filters]);

  // Load schedule config on mount
  useEffect(() => {
    const loadSchedule = async () => {
      try {
        const data = await api("/api/strategies/research/schedule");
        setScheduleConfig(data);
      } catch (e) {
        console.error("Failed to load schedule:", e);
      }
    };
    loadSchedule();
  }, []);

  const handleNewResearch = async (e) => {
    e.preventDefault();
    setErr(null);
    try {
      const result = await api("/api/research", {
        method: "POST",
        body: newResearch,
      });
      setNewResearch({ strategy_id: "", strategy_version: "", conversation_id: "", backtest_run_id: "", deployment_id: "" });
      setShowNewForm(false);
      load();
    } catch (e) {
      setErr(e);
    }
  };

  const handleFromChat = async () => {
    // This would be called from Studio page
  };

  const handleView = (run) => {
    setSelectedRunDetail(run);
  };

  const handleSaveSchedule = async () => {
    setScheduleLoading(true);
    try {
      await api("/api/strategies/research/schedule", {
        method: "POST",
        body: scheduleConfig,
      });
      setShowSchedule(false);
    } catch (e) {
      setErr(e);
    } finally {
      setScheduleLoading(false);
    }
  };

  const StatusBadge = ({ simulated }) => (
    <span className={`badge ${simulated ? "text-amber-400 border-amber-400/50" : "text-up border-up/50"} text-[10px]`}>
      {simulated ? "SIMULATED" : "LIVE"}
    </span>
  );

  const formatTime = (ts) => {
    if (!ts) return "";
    const d = new Date(ts);
    return d.toLocaleString();
  };

  if (selectedRunDetail) {
    const r = selectedRunDetail;
    const facts = r.facts || {};
    const interp = r.interpretations || {};
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-3">
          <button className="btn" onClick={() => setSelectedRunDetail(null)}>← Back</button>
          <h2 className="text-lg font-semibold">Research Run #{r.id}</h2>
          <StatusBadge simulated={r.is_simulated} />
        </div>
        <ErrorBox err={err} />
        
        <div className="card p-3 mb-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <div><span className="text-xs text-slate-400">ID</span><div className="font-mono">{r.id}</div></div>
            <div><span className="text-xs text-slate-400">Status</span><div>{r.label}</div></div>
            <div><span className="text-xs text-slate-400">Data Source</span><div>{r.data_source}</div></div>
            <div><span className="text-xs text-slate-400">Created</span><div>{formatTime(r.created_at)}</div></div>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {r.strategy_id && <Badge status={`strategy-${r.strategy_id}`} />}
            {r.conversation_id && <Badge status={`conv-${r.conversation_id}`} />}
            {r.backtest_run_id && <Badge status={`backtest-${r.backtest_run_id}`} />}
            {r.deployment_id && <Badge status={`deploy-${r.deployment_id}`} />}
            {r.is_simulated && <Badge status="SIMULATED" />}
          </div>
        </div>

        <div className="card p-3 mb-3">
          <h3 className="font-medium mb-2">Facts</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(r.facts || {}).map(([k, v]) => (
              <div key={k} className="card p-2">
                <div className="text-[10px] text-slate-500">{k.replace(/_/g, " ")}</div>
                <div className="num text-lg">{typeof v === 'number' ? fmt(v) : v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-3 mb-3">
          <h3 className="font-medium mb-2">Interpretations</h3>
          <div className="space-y-2">
            <div>
              <div className="text-xs text-ai font-medium mb-1">Market Analyst</div>
              <p className="text-sm">{r.interpretations?.market_analyst || "—"}</p>
            </div>
            <div>
              <div className="text-xs text-up font-medium mb-1">Bullish Signals ({r.interpretations?.bull?.length || 0})</div>
              <ul className="list-disc list-inside text-sm space-y-1">
                {(r.interpretations?.bull || []).map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
            <div>
              <div className="text-xs text-down font-medium mb-1">Bearish Signals ({r.interpretations?.bear?.length || 0})</div>
              <ul className="list-disc list-inside text-sm space-y-1">
                {(r.interpretations?.bear || []).map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
            <div>
              <div className="text-xs text-amber-400 font-medium mb-1">Risk Analyst</div>
              <p className="text-sm">{r.interpretations?.risk_analyst || "—"}</p>
            </div>
            <div>
              <div className="text-xs text-ai font-medium mb-1">Strategy Manager</div>
              <p className="text-sm">{r.interpretations?.strategy_manager || "—"}</p>
            </div>
          </div>
        </div>

        <div className="card p-3">
          <h3 className="font-medium mb-2">Provenance</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            <div><span className="text-slate-400">Data Source</span><div className="font-medium">{r.data_source}</div></div>
            <div><span className="text-slate-400">Simulated</span><div className="font-medium">{r.is_simulated ? "Yes" : "No"}</div></div>
            <div><span className="text-slate-400">Created</span><div className="font-medium">{formatTime(r.created_at)}</div></div>
            <div><span className="text-slate-400">Updated</span><div className="font-medium">{formatTime(r.updated_at)}</div></div>
          </div>
          {r.data_quality && (
            <div className="mt-2">
              <div className="text-xs text-slate-400 mb-1">Data Quality</div>
              <pre className="num text-[10px] text-slate-500 overflow-auto max-h-40">
                {JSON.stringify(r.data_quality, null, 2)}
              </pre>
            </div>
          )}
          <div className="mt-2">
            <div className="text-xs text-slate-400 mb-1">Strategy Spec Snapshot</div>
            <pre className="num text-[10px] text-slate-500 overflow-auto max-h-64">
              {JSON.stringify(r.strategy_spec_snapshot, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">Research Runs</h2>
        <div className="flex gap-2">
          <button className="btn btn-ai" onClick={() => setShowNewForm(true)}>+ New Research</button>
          <button className="btn" onClick={() => setShowComparison(true)}>Compare Runs</button>
          <button className="btn" onClick={() => setShowExport(true)}>Export</button>
          <button className="btn" onClick={() => setShowSchedule(true)}>Schedule</button>
          <button className="btn" onClick={() => setShowNewForm(false)}>Cancel</button>
        </div>
      </div>

      {showNewForm && (
        <div className="card p-3 mb-3">
          <h3 className="font-medium mb-2">Create New Research Run</h3>
          <ErrorBox err={err} />
          <form onSubmit={handleNewResearch} className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Strategy ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={newResearch.strategy_id}
                  onChange={(e) => setNewResearch({ ...newResearch, strategy_id: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Strategy Version</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={newResearch.strategy_version}
                  onChange={(e) => setNewResearch({ ...newResearch, strategy_version: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Conversation ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={newResearch.conversation_id}
                  onChange={(e) => setNewResearch({ ...newResearch, conversation_id: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Backtest Run ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={newResearch.backtest_run_id}
                  onChange={(e) => setNewResearch({ ...newResearch, backtest_run_id: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Deployment ID</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={newResearch.deployment_id}
                  onChange={(e) => setNewResearch({ ...newResearch, deployment_id: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-ai" type="submit">Run Research</button>
              <button className="btn" type="button" onClick={() => setShowNewForm(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <ErrorBox err={err} />

      <div className="card p-3 mb-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.strategy_id}
            onChange={(e) => setFilters({ ...filters, strategy_id: e.target.value })}
          >
            <option value="">All Strategies</option>
            <option value="1">Strategy 1</option>
          </select>
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.conversation_id}
            onChange={(e) => setFilters({ ...filters, conversation_id: e.target.value })}
          >
            <option value="">All Conversations</option>
          </select>
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.backtest_run_id}
            onChange={(e) => setFilters({ ...filters, backtest_run_id: e.target.value })}
          >
            <option value="">All Backtests</option>
          </select>
          <select
            className="bg-ink border border-line rounded px-2 py-1 text-sm"
            value={filters.deployment_id}
            onChange={(e) => setFilters({ ...filters, deployment_id: e.target.value })}
          >
            <option value="">All Deployments</option>
          </select>
        </div>
      </div>

      {/* Strategy Lineage for selected strategy */}
      {filters.strategy_id && (
        <div className="mb-3">
          <StrategyLineage strategyId={parseInt(filters.strategy_id)} />
        </div>
      )}

      {loading && runs.length === 0 && <div className="text-center py-8 text-slate-500">Loading...</div>}

      {!loading && runs.length === 0 && (
        <div className="card p-8 text-center text-slate-500">
          <p className="mb-2">No research runs yet</p>
          <button className="btn btn-ai" onClick={() => setShowNewForm(true)}>Run your first research</button>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <>
          <div className="space-y-2">
            {runs.map((r) => (
              <div key={r.id} className="card p-3" onClick={() => handleView(r)}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Research Run #{r.id}</span>
                    <StatusBadge simulated={r.is_simulated} />
                  </div>
                  <div className="text-xs text-slate-400">{formatTime(r.created_at)}</div>
                </div>
                <div className="flex flex-wrap gap-2 mt-1">
                  {r.strategy_id && <Badge status={`strategy-${r.strategy_id}`} />}
                  {r.conversation_id && <Badge status={`conv-${r.conversation_id}`} />}
                  {r.backtest_run_id && <Badge status={`backtest-${r.backtest_run_id}`} />}
                  {r.deployment_id && <Badge status={`deploy-${r.deployment_id}`} />}
                </div>
                <div className="mt-2 text-sm text-slate-400">
                  {r.label}
                </div>
              </div>
            ))}
          </div>
          <div className="flex justify-center gap-2 mt-3">
            {page > 1 && <button className="btn" onClick={() => setPage(page - 1)}>Previous</button>}
            <span className="flex items-center text-sm text-slate-400">Page {page} of {Math.ceil(total / 20)} (Total: {total})</span>
            {page * 20 < total && <button className="btn" onClick={() => setPage(page + 1)}>Next</button>}
          </div>
        </>
      )}

      {/* Research Comparison Modal */}
      {showComparison && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-panel border border-line rounded-lg w-full max-w-4xl max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <h2 className="text-lg font-semibold">Research Comparison</h2>
              <button className="text-slate-400 hover:text-slate-200 text-xl" onClick={() => setShowComparison(false)}>×</button>
            </div>
            <div className="p-4">
              <ResearchComparison />
            </div>
          </div>
        </div>
      )}

      {/* Export Dialog */}
      <ExportDialog
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        defaultSelection={{ research_run_ids: runs.map(r => r.id) }}
      />

      {/* Scheduled Research Modal */}
      {showSchedule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-panel border border-line rounded-lg w-full max-w-md max-h-[90vh] overflow-auto">
            <div className="flex items-center justify-between p-4 border-b border-line">
              <h2 className="text-lg font-semibold">Scheduled Research Configuration</h2>
              <button className="text-slate-400 hover:text-slate-200 text-xl" onClick={() => setShowSchedule(false)}>×</button>
            </div>
            <div className="p-4 space-y-4">
              <ErrorBox err={err} />
              
              <div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    className="w-4 h-4 accent-ai"
                    checked={scheduleConfig.enabled}
                    onChange={(e) => setScheduleConfig({ ...scheduleConfig, enabled: e.target.checked })}
                  />
                  <span className="font-medium">Enable Scheduled Research</span>
                </label>
                <p className="text-xs text-slate-500 mt-1">
                  When enabled, research runs will be automatically executed on the configured schedule.
                  Note: This requires a backend scheduler service to be running.
                </p>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Cron Schedule</label>
                <input
                  type="text"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm font-mono"
                  value={scheduleConfig.cron_schedule}
                  onChange={(e) => setScheduleConfig({ ...scheduleConfig, cron_schedule: e.target.value })}
                  placeholder="0 6 * * * (daily at 6 AM)"
                />
                <p className="text-xs text-slate-500 mt-1">Standard cron expression (minute hour day month weekday)</p>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Strategy IDs (comma-separated)</label>
                <input
                  type="text"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={scheduleConfig.strategies.join(",")}
                  onChange={(e) => setScheduleConfig({ ...scheduleConfig, strategies: e.target.value.split(",").map(s => parseInt(s.trim())).filter(s => !isNaN(s)) })}
                  placeholder="1,2,3"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Symbols (comma-separated)</label>
                <input
                  type="text"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={scheduleConfig.symbols.join(",")}
                  onChange={(e) => setScheduleConfig({ ...scheduleConfig, symbols: e.target.value.split(",").map(s => s.trim().toUpperCase()).filter(Boolean) })}
                  placeholder="BTC-USD,ETH-USD"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Timeframes (comma-separated)</label>
                <input
                  type="text"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={scheduleConfig.timeframes.join(",")}
                  onChange={(e) => setScheduleConfig({ ...scheduleConfig, timeframes: e.target.value.split(",").map(s => s.trim()).filter(Boolean) })}
                  placeholder="1d,1h"
                />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Max Runs Per Day</label>
                <input
                  type="number"
                  className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                  value={scheduleConfig.max_runs_per_day}
                  onChange={(e) => setScheduleConfig({ ...scheduleConfig, max_runs_per_day: parseInt(e.target.value) || 5 })}
                  min="1"
                  max="50"
                />
              </div>

              <div className="flex gap-2 pt-2 border-t border-line">
                <button className="btn btn-ai flex-1" onClick={handleSaveSchedule} disabled={scheduleLoading}>
                  {scheduleLoading ? "Saving..." : "Save Configuration"}
                </button>
                <button className="btn flex-1" onClick={() => setShowSchedule(false)}>Cancel</button>
              </div>

              <div className="text-xs text-slate-500 border-t border-line pt-3">
                <p className="font-medium mb-1">Note:</p>
                <p>The current backend only stores the configuration. Automatic execution requires a separate scheduler service (e.g., APScheduler, Celery Beat, or cron) to be implemented and deployed. This UI configures the schedule parameters for when such a service is available.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}