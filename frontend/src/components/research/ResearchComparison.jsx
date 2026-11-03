import React, { useState, useEffect } from "react";
import { api, fmt } from "../../api.jsx";

export default function ResearchComparison() {
  const [runs, setRuns] = useState([]);
  const [selectedRunIds, setSelectedRunIds] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Load available research runs
  const loadRuns = async () => {
    try {
      const params = new URLSearchParams({ page: page.toString(), page_size: 50 });
      const data = await api(`/api/research?${params}`);
      setRuns(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [page]);

  const toggleRun = (runId) => {
    setSelectedRunIds((prev) =>
      prev.includes(runId) ? prev.filter((id) => id !== runId) : [...prev, runId].slice(0, 5)
    );
  };

  const handleCompare = async () => {
    if (selectedRunIds.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api("/api/strategies/research/compare", {
        method: "POST",
        body: { run_ids: selectedRunIds },
      });
      setComparison(data);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  const formatFactValue = (key, value) => {
    if (value === null || value === undefined) return "—";
    if (typeof value === "number") {
      // Format specific keys
      if (key.includes("pct") || key.includes("vol") || key.includes("drawdown") || key.includes("return")) {
        return fmt(value, 2) + "%";
      }
      if (key.includes("rsi")) return fmt(value, 1);
      if (key.includes("ema") || key.includes("macd") || key.includes("close")) return fmt(value, 2);
      return fmt(value);
    }
    return String(value);
  };

  const renderFactsComparison = () => {
    if (!comparison || !comparison.comparison || !comparison.comparison.facts) return null;
    
    const facts = comparison.comparison.facts;
    const runIds = comparison.runs.map((r) => r.id);
    
    // Collect all unique fact keys
    const allKeys = new Set();
    runIds.forEach((id) => {
      if (facts[id]) Object.keys(facts[id]).forEach((k) => allKeys.add(k));
    });
    
    const sortedKeys = Array.from(allKeys).sort();
    
    return (
      <div className="card p-3 mb-3">
        <h3 className="font-medium mb-2">Facts Comparison</h3>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400 border-b border-line">
                <th className="p-2">Metric</th>
                {runIds.map((id) => {
                  const run = comparison.runs.find((r) => r.id === id);
                  return (
                    <th key={id} className="p-2 font-mono">
                      Run #{id} {run?.label && `(${run.label})`}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedKeys.map((key) => (
                <tr key={key} className="border-b border-line/50">
                  <td className="p-2 text-slate-300 font-medium">{key.replace(/_/g, " ")}</td>
                  {runIds.map((id) => (
                    <td key={id} className="p-2 font-mono text-slate-200">
                      {facts[id]?.[key] !== undefined ? formatFactValue(key, facts[id][key]) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderInterpretationsComparison = () => {
    if (!comparison || !comparison.comparison || !comparison.comparison.interpretations) return null;
    
    const interpretations = comparison.comparison.interpretations;
    const runIds = comparison.runs.map((r) => r.id);
    
    return (
      <div className="card p-3 mb-3">
        <h3 className="font-medium mb-2">Interpretations Comparison</h3>
        <div className="space-y-3">
          {runIds.map((id) => {
            const interp = interpretations[id];
            const run = comparison.runs.find((r) => r.id === id);
            if (!interp) return null;
            return (
              <div key={id} className="border border-line rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-ai">Run #{id} {run?.label && `(${run.label})`}</h4>
                  <span className="text-xs text-slate-400">{run?.is_simulated ? "SIMULATED" : "LIVE"}</span>
                </div>
                <div className="space-y-1 text-sm">
                  {interp.market_analyst && (
                    <p><span className="text-xs text-ai font-medium">Market Analyst: </span>{interp.market_analyst}</p>
                  )}
                  {interp.risk_analyst && (
                    <p><span className="text-xs text-amber-400 font-medium">Risk Analyst: </span>{interp.risk_analyst}</p>
                  )}
                  {interp.strategy_manager && (
                    <p><span className="text-xs text-up font-medium">Strategy Manager: </span>{interp.strategy_manager}</p>
                  )}
                  {interp.bull && interp.bull.length > 0 && (
                    <div>
                      <span className="text-xs text-up font-medium">Bullish: </span>
                      <ul className="list-disc list-inside text-xs">
                        {interp.bull.map((b, i) => <li key={i}>{b}</li>)}
                      </ul>
                    </div>
                  )}
                  {interp.bear && interp.bear.length > 0 && (
                    <div>
                      <span className="text-xs text-down font-medium">Bearish: </span>
                      <ul className="list-disc list-inside text-xs">
                        {interp.bear.map((b, i) => <li key={i}>{b}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderRiskComparison = () => {
    if (!comparison || !comparison.comparison || !comparison.comparison.risk) return null;
    
    const risk = comparison.comparison.risk;
    const runIds = comparison.runs.map((r) => r.id);
    
    return (
      <div className="card p-3 mb-3">
        <h3 className="font-medium mb-2">Risk Observations</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {runIds.map((id) => {
            const runRisk = risk[id];
            const run = comparison.runs.find((r) => r.id === id);
            if (!runRisk) return null;
            return (
              <div key={id} className="border border-line rounded p-3">
                <h4 className="font-medium text-sm mb-2">Run #{id} {run?.label && `(${run.label})`}</h4>
                <div className="space-y-1 text-xs">
                  <p><span className="text-slate-400">Risk Assessment: </span><span className="font-medium">{runRisk}</span></p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderProvenance = () => {
    if (!comparison || !comparison.comparison || !comparison.comparison.provenance) return null;
    
    const provenance = comparison.comparison.provenance;
    const runIds = comparison.runs.map((r) => r.id);
    
    return (
      <div className="card p-3 mb-3">
        <h3 className="font-medium mb-2">Data Provenance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {runIds.map((id) => {
            const prov = provenance[id];
            const run = comparison.runs.find((r) => r.id === id);
            if (!prov) return null;
            return (
              <div key={id} className="border border-line rounded p-3">
                <h4 className="font-medium text-sm mb-2">Run #{id} {run?.label && `(${run.label})`}</h4>
                <div className="space-y-1 text-xs">
                  <p><span className="text-slate-400">Data Source: </span>{prov.data_source}</p>
                  <p><span className="text-slate-400">Simulated: </span>{prov.is_simulated ? "Yes" : "No"}</p>
                  <p><span className="text-slate-400">Created: </span>{prov.created_at ? new Date(prov.created_at).toLocaleString() : "N/A"}</p>
                  <p><span className="text-slate-400">Strategy ID: </span>{prov.strategy_id || "N/A"}</p>
                  <p><span className="text-slate-400">Backtest ID: </span>{prov.backtest_run_id || "N/A"}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="card">
      <div className="p-3 border-b border-line flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">Research Comparison</h3>
        <span className="text-xs text-slate-400">
          {selectedRunIds.length} run{selectedRunIds.length !== 1 ? "s" : ""} selected
        </span>
      </div>
      <div className="p-3 space-y-3">
        {/* Run Selection */}
        <div>
          <h4 className="font-medium text-sm mb-2">Select 2-5 Research Runs to Compare</h4>
          {error && (
            <div className="border border-down/50 bg-down/10 text-down text-sm rounded p-2 mb-3">
              {error.detail?.message || error.message || "Failed to load runs"}
            </div>
          )}
          <div className="space-y-1 max-h-60 overflow-auto">
            {runs.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-4">No research runs available</p>
            ) : (
              runs.map((r) => (
                <label
                  key={r.id}
                  className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                    selectedRunIds.includes(r.id)
                      ? "bg-ai/10 border border-ai/30"
                      : "hover:bg-line/50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedRunIds.includes(r.id)}
                    onChange={() => toggleRun(r.id)}
                    disabled={!selectedRunIds.includes(r.id) && selectedRunIds.length >= 5}
                    className="w-4 h-4 accent-ai"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium">Run #{r.id}</span>
                      <span className={`badge ${r.is_simulated ? "text-amber-400 border-amber-400/50" : "text-up border-up/50"} text-[10px]`}>
                        {r.is_simulated ? "SIMULATED" : "LIVE"}
                      </span>
                      {r.label && <span className="text-xs text-slate-400">{r.label}</span>}
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      {r.strategy_id && <span>Strategy: {r.strategy_id}</span>}
                      {r.created_at && <span>{new Date(r.created_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                  {selectedRunIds.length >= 5 && !selectedRunIds.includes(r.id) && (
                    <span className="text-xs text-slate-500">Max 5</span>
                  )}
                </label>
              ))
            )}
          </div>
          <div className="flex justify-center gap-2 mt-3">
            {page > 1 && <button className="btn" onClick={() => setPage(page - 1)}>Previous</button>}
            <span className="flex items-center text-sm text-slate-400">Page {page} of {Math.ceil(total / 50)} (Total: {total})</span>
            {page * 50 < total && <button className="btn" onClick={() => setPage(page + 1)}>Next</button>}
          </div>
        </div>

        {selectedRunIds.length >= 2 && (
          <button
            className="btn btn-ai w-full"
            onClick={handleCompare}
            disabled={loading}
          >
            {loading ? "Comparing..." : "Compare Selected Runs"}
          </button>
        )}

        {comparison && !loading && (
          <div className="border-t border-line pt-3 space-y-3">
            <h4 className="font-medium text-ai">
              Comparison of {comparison.runs.length} runs
            </h4>
            {renderFactsComparison()}
            {renderInterpretationsComparison()}
            {renderRiskComparison()}
            {renderProvenance()}
            
            {comparison.comparison?.summary && (
              <div className="card p-3 border border-ai/30 bg-ai/5">
                <h4 className="font-medium text-ai mb-2">Summary</h4>
                <p className="text-sm">{comparison.comparison.summary}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}