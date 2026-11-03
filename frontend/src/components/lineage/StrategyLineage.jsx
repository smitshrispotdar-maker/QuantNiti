import React, { useEffect, useState } from "react";
import { api } from "../../api.jsx";

const EVENT_TYPE_CONFIG = {
  conversation: { icon: "💬", color: "text-ai", bg: "bg-ai/10", label: "Conversation" },
  strategy: { icon: "📝", color: "text-up", bg: "bg-up/10", label: "Strategy Created" },
  draft_update: { icon: "✏️", color: "text-ai", bg: "bg-ai/10", label: "Draft Updated" },
  backtest: { icon: "📊", color: "text-up", bg: "bg-up/10", label: "Backtest" },
  research: { icon: "🔬", color: "text-ai", bg: "bg-ai/10", label: "Research" },
  journal: { icon: "📓", color: "text-ai", bg: "bg-ai/10", label: "Journal Entry" },
  deployment: { icon: "📈", color: "text-up", bg: "bg-up/10", label: "Deployment" },
  deployment_closed: { icon: "🛑", color: "text-down", bg: "bg-down/10", label: "Deployment Closed" },
};

const formatTime = (ts) => {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString();
};

const formatShortTime = (ts) => {
  if (!ts) return "—";
  const d = new Date(ts);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return "Just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
};

const getEventLink = (event) => {
  switch (event.entity_type) {
    case "conversation":
      return `/studio?conv=${event.entity_id}`;
    case "strategy":
      return `/builder?strategy=${event.entity_id}`;
    case "backtest":
      return `/backtest?run=${event.entity_id}`;
    case "research":
      return `/research?run=${event.entity_id}`;
    case "journal":
      return `/journal?entry=${event.entity_id}`;
    case "deployment":
    case "deployment_closed":
      return `/paper?deployment=${event.entity_id}`;
    default:
      return null;
  };
};

const formatDetails = (event) => {
  const d = event.details;
  const parts = [];

  if (d.strategy_id) parts.push(`Strategy #${d.strategy_id}${d.strategy_version ? ` v${d.strategy_version}` : ""}`);
  if (d.conversation_id) parts.push(`Conv #${d.conversation_id}`);
  if (d.backtest_run_id) parts.push(`Backtest #${d.backtest_run_id}`);
  if (d.research_run_id) parts.push(`Research #${d.research_run_id}`);
  if (d.deployment_id) parts.push(`Deploy #${d.deployment_id}`);
  if (d.status) parts.push(`Status: ${d.status}`);
  if (d.total_return_pct !== undefined) parts.push(`Return: ${d.total_return_pct.toFixed(1)}%`);
  if (d.trades !== undefined) parts.push(`Trades: ${d.trades}`);
  if (d.status && d.status !== "ACTIVE") parts.push(`Status: ${d.status}`);
  if (d.is_simulated !== undefined) parts.push(d.is_simulated ? "Simulated" : "Live");
  if (d.validation_passed !== undefined) parts.push(d.validation_passed ? "Validated" : "Failed Validation");

  return parts.join(" · ");
};

function renderEventItem(event, index, events) {
  const config = EVENT_TYPE_CONFIG[event.event_type] || { icon: "📌", color: "text-slate-400", bg: "bg-slate-400/10", label: event.event_type };
  const link = getEventLink(event);
  const isLast = index === events.length - 1;

  return (
    <div key={`${event.entity_type}-${event.entity_id}-${event.timestamp}`} className="relative">
      {/* Timeline dot */}
      <div className="absolute -left-10 w-3 h-3 rounded-full border-2 border-line flex items-center justify-center bg-panel" style={{ backgroundColor: "inherit" }}>
        <span className="text-xs" style={{ color: config.color }}>{config.icon}</span>
      </div>
      {/* Connecting line */}
      {!isLast && (
        <div className="absolute -left-9.5 top-4 bottom-0 w-0.5 bg-line" />
      )}

      <div className="card p-3 hover:bg-line/50 transition-colors group">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`font-medium ${config.color}`}>{config.label}</span>
              <span className="text-xs text-slate-500">{formatShortTime(event.timestamp)}</span>
              <span className="text-xs text-slate-400">{formatTime(event.timestamp)}</span>
            </div>
            <p className="text-sm font-medium text-slate-200 truncate">{event.title}</p>
            <p className="text-xs text-slate-400 mt-1 truncate">{formatDetails(event)}</p>
            {event.details.strategy_version && (
              <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-line text-slate-400">
                Strategy v{event.details.strategy_version}
              </span>
            )}
          </div>
          {getEventLink(event) && (
            <a
              href={getEventLink(event)}
              className="btn text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
              target="_blank"
              rel="noopener noreferrer"
            >
              Open
            </a>
          )}
        </div>
      </div>
    </div>
  );
};



export default function StrategyLineage({ strategyId, conversationId, entityType, entityId, className = "" }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        let url = "/api/lineage";
        const params = new URLSearchParams();

        if (entityType && entityId) {
          url = `/api/lineage/entity/${entityType}/${entityId}`;
        } else {
          if (strategyId) params.set("strategy_id", strategyId);
          if (conversationId) params.set("conversation_id", conversationId);
        }

        if (params.toString()) url += `?${params.toString()}`;

        const data = await api(url);
        if (mounted) {
          setEvents(data.events || []);
        }
      } catch (e) {
        if (mounted) setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    load();
    return () => { mounted = false; };
  }, [strategyId, conversationId, entityType, entityId]);

  if (loading) {
    return (
      <div className={`card p-6 ${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ai"></div>
          <span className="ml-3 text-slate-400">Loading lineage...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`card p-6 ${className}`}>
        <div className="text-center py-8 text-down">
          <p className="mb-2">Failed to load lineage</p>
          <p className="text-sm text-slate-500">{error.detail?.message || error.message || "Unknown error"}</p>
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className={`card p-8 ${className}`}>
        <div className="text-center py-8 text-slate-500">
          <p className="mb-2">No lineage events found</p>
          <p className="text-sm">Create a strategy, run a backtest, or start a conversation to build lineage</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`card ${className}`}>
      <div className="p-3 border-b border-line flex items-center justify-between">
        <h3 className="font-medium">Strategy Lineage</h3>
        <span className="text-xs text-slate-400">{events.length} event{events.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="p-3">
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-line" />

          <div className="space-y-4 ml-10">
            {events.map((event, index) => renderEventItem(event, index, events))}
          </div>
        </div>
      </div>
    </div>
  );
}
