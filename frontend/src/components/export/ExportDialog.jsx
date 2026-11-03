import React, { useState, useEffect } from "react";
import { api } from "../../api.jsx";

const EXPORT_FORMATS = [
  { value: "json", label: "JSON", icon: "📄", description: "Raw data for programmatic use" },
  { value: "markdown", label: "Markdown", icon: "📝", description: "Human-readable documentation" },
  { value: "pdf", label: "PDF", icon: "📑", description: "Formatted report for sharing" },
];

export default function ExportDialog({ isOpen, onClose, defaultSelection }) {
  const [format, setFormat] = useState("json");
  const [selection, setSelection] = useState({
    journal_entry_ids: [],
    strategy_ids: [],
    backtest_run_ids: [],
    research_run_ids: [],
    date_range_start: "",
    date_range_end: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState("");
  const [journalEntries, setJournalEntries] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [backtestRuns, setBacktestRuns] = useState([]);
  const [researchRuns, setResearchRuns] = useState([]);

  // Load available data for selection
  useEffect(() => {
    const loadOptions = async () => {
      try {
        // Load journal entries
        const journalData = await api("/api/journal?page=1&page_size=100");
        setJournalEntries(journalData.items);
        
        // Load strategies
        const strategiesData = await api("/api/strategies");
        setStrategies(strategiesData);
        
        // Load backtest runs
        const backtestData = await api("/api/backtests?page=1&page_size=100");
        setBacktestRuns(backtestData.items);
        
        // Load research runs
        const researchData = await api("/api/research?page=1&page_size=100");
        setResearchRuns(researchData.items);
      } catch (e) {
        console.error("Failed to load export options:", e);
      }
    };
    loadOptions();
  }, []);

  // Apply default selection if provided
  useEffect(() => {
    if (defaultSelection) {
      setSelection((prev) => ({ ...prev, ...defaultSelection }));
    }
  }, [defaultSelection]);

  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setProgress("Preparing export...");
    
    try {
      // Clean up empty arrays
      const body = {
        format,
        ...Object.fromEntries(
          Object.entries(selection).filter(([_, v]) => 
            Array.isArray(v) ? v.length > 0 : v !== ""
          )
        ),
      };
      
      setProgress("Generating export...");
      const data = await api("/api/strategies/export", {
        method: "POST",
        body,
      });
      
      setProgress("Downloading...");
      
      // Handle different response types
      let blob;
      let filename;
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
      
      if (format === "json") {
        blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        filename = `quantniti-export-${timestamp}.json`;
      } else if (format === "markdown") {
        blob = new Blob([data.markdown], { type: "text/markdown" });
        filename = `quantniti-export-${timestamp}.md`;
      } else if (format === "pdf") {
        // For PDF, the backend should return a base64 encoded PDF or blob
        // If it returns base64:
        if (data.pdf_base64) {
          const byteCharacters = atob(data.pdf_base64);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          blob = new Blob([byteArray], { type: "application/pdf" });
        } else if (data.content) {
          // Fallback: treat as base64
          const byteCharacters = atob(data.content);
          const byteNumbers = new Array(byteCharacters.length);
          for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          blob = new Blob([byteArray], { type: "application/pdf" });
        } else {
          throw new Error("Invalid PDF response format");
        }
        filename = `quantniti-export-${timestamp}.pdf`;
      }
      
      // Trigger download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      setProgress("Export completed!");
      setTimeout(() => {
        onClose();
        setProgress("");
      }, 1500);
    } catch (e) {
      setError(e);
      setProgress("");
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (category, id) => {
    setSelection((prev) => {
      const current = prev[category] || [];
      const updated = current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id];
      return { ...prev, [category]: updated };
    });
  };

  const renderSelectionSection = (title, items, category, getLabel, getSubLabel) => {
    if (items.length === 0) return null;
    
    return (
      <div className="mb-3">
        <h4 className="font-medium text-sm mb-2 text-slate-300">{title}</h4>
        <div className="space-y-1 max-h-40 overflow-auto border border-line rounded p-2">
          {items.map((item) => (
            <label
              key={item.id}
              className={`flex items-center gap-2 p-1.5 rounded cursor-pointer transition-colors ${
                selection[category]?.includes(item.id)
                  ? "bg-ai/10"
                  : "hover:bg-line/50"
              }`}
            >
              <input
                type="checkbox"
                checked={selection[category]?.includes(item.id)}
                onChange={() => toggleItem(category, item.id)}
                className="w-4 h-4 accent-ai"
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{getLabel(item)}</div>
                {getSubLabel && <div className="text-xs text-slate-400 truncate">{getSubLabel(item)}</div>}
              </div>
            </label>
          ))}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-panel border border-line rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-line">
          <h2 className="text-lg font-semibold">Export Data</h2>
          <button
            className="text-slate-400 hover:text-slate-200 text-xl"
            onClick={onClose}
            disabled={loading}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Format Selection */}
          <div>
            <h3 className="font-medium text-sm mb-3">Export Format</h3>
            <div className="grid grid-cols-3 gap-2">
              {EXPORT_FORMATS.map((f) => (
                <button
                  key={f.value}
                  className={`p-3 rounded border-2 text-left transition-all ${
                    format === f.value
                      ? "border-ai bg-ai/10"
                      : "border-line hover:border-ai/50"
                  }`}
                  onClick={() => setFormat(f.value)}
                  disabled={loading}
                >
                  <div className="text-2xl mb-1">{f.icon}</div>
                  <div className="font-medium">{f.label}</div>
                  <div className="text-xs text-slate-400">{f.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Data Selection */}
          <div>
            <h3 className="font-medium text-sm mb-3">Select Data to Export</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderSelectionSection(
                "Journal Entries",
                journalEntries,
                "journal_entry_ids",
                (e) => e.title || `Entry #${e.id}`,
                (e) => `${e.decision_type} · ${e.status} · ${new Date(e.created_at).toLocaleDateString()}`
              )}
              {renderSelectionSection(
                "Strategies",
                strategies,
                "strategy_ids",
                (s) => `${s.name} v${s.version}`,
                (s) => `ID: ${s.id} · ${new Date(s.created_at).toLocaleDateString()}`
              )}
              {renderSelectionSection(
                "Backtest Runs",
                backtestRuns,
                "backtest_run_ids",
                (b) => `Backtest #${b.id}`,
                (b) => `Strategy ${b.strategy_id} v${b.strategy_version} · Return: ${b.metrics?.total_return_pct?.toFixed(1)}% · ${new Date(b.created_at).toLocaleDateString()}`
              )}
              {renderSelectionSection(
                "Research Runs",
                researchRuns,
                "research_run_ids",
                (r) => `Research #${r.id}`,
                (r) => `${r.label} · ${r.is_simulated ? "Simulated" : "Live"} · ${new Date(r.created_at).toLocaleDateString()}`
              )}
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Date Range Start</label>
              <input
                type="date"
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                value={selection.date_range_start}
                onChange={(e) => setSelection({ ...selection, date_range_start: e.target.value })}
                disabled={loading}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Date Range End</label>
              <input
                type="date"
                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                value={selection.date_range_end}
                onChange={(e) => setSelection({ ...selection, date_range_end: e.target.value })}
                disabled={loading}
              />
            </div>
          </div>

          {/* Progress / Error */}
          {error && (
            <div className="border border-down/50 bg-down/10 text-down text-sm rounded p-3">
              Export failed: {error.detail?.message || error.message || "Unknown error"}
            </div>
          )}
          
          {progress && !error && (
            <div className="flex items-center gap-2 text-sm text-ai">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-ai"></div>
              <span>{progress}</span>
            </div>
          )}

          {/* Export Button */}
          <div className="flex justify-end gap-2 pt-2 border-t border-line">
            <button
              className="btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              className="btn btn-ai"
              onClick={handleExport}
              disabled={loading}
            >
              {loading ? "Exporting..." : `Export as ${format.toUpperCase()}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}