import React, { useState, useEffect } from "react";
import { api } from "../../api.jsx";

export default function StrategyVersionDiff({ strategyId }) {
  const [versions, setVersions] = useState([]);
  const [fromVersion, setFromVersion] = useState("");
  const [toVersion, setToVersion] = useState("");
  const [diff, setDiff] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load available versions on mount
  useEffect(() => {
    if (!strategyId) return;
    const loadVersions = async () => {
      try {
        const data = await api(`/api/strategies/${strategyId}/versions`);
        setVersions(data);
        if (data.length >= 2) {
          // Default to comparing first and last version
          setFromVersion(data[0].version);
          setToVersion(data[data.length - 1].version);
        }
      } catch (e) {
        setError(e);
      }
    };
    loadVersions();
  }, [strategyId]);

  // Fetch diff when versions change
  useEffect(() => {
    if (!strategyId || !fromVersion || !toVersion || fromVersion === toVersion) {
      setDiff(null);
      return;
    }
    const loadDiff = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api(`/api/strategies/${strategyId}/diff?from_version=${fromVersion}&to_version=${toVersion}`);
        setDiff(data);
      } catch (e) {
        setError(e);
      } finally {
        setLoading(false);
      }
    };
    loadDiff();
  }, [strategyId, fromVersion, toVersion]);

  const renderDiffValue = (value, indent = 0) => {
    if (value === null || value === undefined) {
      return <span className="text-slate-500 italic">—</span>;
    }
    if (typeof value === "object") {
      return (
        <pre className="num text-[10px] text-slate-300 overflow-auto max-h-40" style={{ marginLeft: `${indent}px` }}>
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    return <span className="font-mono">{String(value)}</span>;
  };

  const renderChange = (key, change) => {
    const { from, to } = change;
    const isAdded = from === null || from === undefined;
    const isRemoved = to === null || to === undefined;
    const isModified = !isAdded && !isRemoved;

    return (
      <div key={key} className="border border-line rounded p-3 mb-2">
        <div className="flex items-center gap-2 mb-2">
          <span className={`font-medium text-sm ${isAdded ? "text-up" : isRemoved ? "text-down" : "text-amber-400"}`}>
            {isAdded ? "➕ Added" : isRemoved ? "➖ Removed" : "🔄 Modified"}
          </span>
          <span className="text-xs text-slate-400 uppercase">{key.replace(/_/g, " ")}</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] text-slate-500 mb-1">From (v{fromVersion})</div>
            {renderDiffValue(from, 20)}
          </div>
          <div>
            <div className="text-[10px] text-slate-500 mb-1">To (v{toVersion})</div>
            {renderDiffValue(to, 20)}
          </div>
        </div>
      </div>
    );
  };

  if (!strategyId) {
    return (
      <div className="card p-6 text-center text-slate-500">
        <p>Select a strategy to compare versions</p>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="card p-6 text-center text-slate-500">
        <p>No versions found for this strategy</p>
      </div>
    );
  }

  if (versions.length < 2) {
    return (
      <div className="card p-6 text-center text-slate-500">
        <p>Need at least 2 versions to compare. Current version: {versions[0]?.version}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="p-3 border-b border-line flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">Strategy Version Diff</h3>
        <span className="text-xs text-slate-400">Strategy #{strategyId} · {versions.length} version{versions.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="p-3 space-y-3">
        {/* Version Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">From Version (older)</label>
            <select
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={fromVersion}
              onChange={(e) => setFromVersion(e.target.value)}
              disabled={loading}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.version}>
                  v{v.version} ({new Date(v.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">To Version (newer)</label>
            <select
              className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
              value={toVersion}
              onChange={(e) => setToVersion(e.target.value)}
              disabled={loading}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.version}>
                  v{v.version} ({new Date(v.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
        </div>

        {fromVersion === toVersion && fromVersion && (
          <div className="text-amber-400 text-sm text-center p-2">
            Select different versions to compare
          </div>
        )}

        {error && (
          <div className="border border-down/50 bg-down/10 text-down text-sm rounded p-2">
            Failed to load diff: {error.detail?.message || error.message || "Unknown error"}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ai"></div>
            <span className="ml-3 text-slate-400">Loading diff...</span>
          </div>
        )}

        {diff && !loading && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xs text-ai font-medium">v{diff.from_version}</span>
                <span className="text-slate-400">→</span>
                <span className="text-xs text-up font-medium">v{diff.to_version}</span>
              </div>
              <span className="text-xs text-slate-400">{new Date(diff.timestamp).toLocaleString()}</span>
            </div>

            {diff.changes && Object.keys(diff.changes).length > 0 ? (
              <div>
                <h4 className="font-medium text-sm mb-2 text-amber-400">
                  {Object.keys(diff.changes).length} change{Object.keys(diff.changes).length !== 1 ? "s" : ""} detected
                </h4>
                {Object.entries(diff.changes).map(([key, change]) => renderChange(key, change))}
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500">
                <p>No changes detected between v{diff.from_version} and v{diff.to_version}</p>
              </div>
            )}
          </div>
        )}

        {!diff && !loading && fromVersion !== toVersion && (
          <div className="text-center py-8 text-slate-500">
            <p>Select versions to compare</p>
          </div>
        )}
      </div>
    </div>
  );
}