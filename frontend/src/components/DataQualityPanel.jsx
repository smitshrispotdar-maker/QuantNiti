import React from "react";
import { Badge } from "../api.jsx";

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

