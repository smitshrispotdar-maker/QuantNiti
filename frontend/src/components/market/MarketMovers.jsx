import React, { useState } from "react";
import { TrendingDown, TrendingUp, BarChart3 } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { fmt, fmtCompact, signedPct, pnlColor } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

const TABS = [
  { id: "gainers", label: "Gainers", icon: TrendingUp },
  { id: "losers", label: "Losers", icon: TrendingDown },
  { id: "volume", label: "Volume", icon: BarChart3 },
];

export default function MarketMovers({ data, loading, onSelect }) {
  const [tab, setTab] = useState("gainers");
  const available = !!data && data.available !== false;
  const rows = data?.[tab] || [];

  return (
    <Panel
      className="h-full"
      title="Market movers"
      dense
      bodyClass="flex flex-col min-h-0"
      actions={
        <span className="flex items-center gap-0.5">
          {TABS.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`btn btn-xs ${tab === t.id ? "btn-ai" : "btn-ghost"}`} title={t.label}>
                <Icon size={11} /> {t.label}
              </button>
            );
          })}
        </span>
      }
    >
      {loading && (
        <div className="p-2 space-y-1.5">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-7" />)}</div>
      )}
      {!loading && !available && (
        <div className="p-3 text-2xs text-muted leading-relaxed">
          <div className="text-down mb-1">Movers unavailable</div>
          {data?.reason || "The configured provider returned no usable movers data."}
        </div>
      )}
      {!loading && available && rows.length === 0 && (
        <div className="p-3 text-2xs text-muted">No {tab} in the current provider snapshot.</div>
      )}
      {!loading && rows.length > 0 && (
        <div className="scroll-area flex-1 min-h-0">
          {rows.map((r) => (
            <button key={r.symbol} onClick={() => onSelect?.(r.symbol)}
              className="w-full flex items-center gap-2 px-3 py-1.5 border-b border-line-soft/60 text-left hover:bg-surface/60">
              <div className="min-w-0 flex-1">
                <div className="text-xs truncate">{displayName(r.symbol, r.name)}</div>
                <div className="text-2xs text-muted-2">{r.exchange || "NSE"} · {r.symbol.replace(/\.(NS|BO)$/, "")}</div>
              </div>
              <div className="text-right">
                <div className="num text-xs">{fmt(r.price)}</div>
                <div className={`num text-2xs ${pnlColor(r.change_pct)}`}>{signedPct(r.change_pct)}</div>
              </div>
              <div className={`num text-2xs w-[52px] text-right ${tab === "volume" ? "text-ai" : "text-muted-2"}`}>
                {fmtCompact(r.volume)}
              </div>
            </button>
          ))}
        </div>
      )}
      {data?.fetched_at && (
        <div className="px-3 py-1.5 text-2xs text-muted-2 border-t border-line-soft">
          {data.provider} · {new Date(data.fetched_at).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" })} IST
        </div>
      )}
    </Panel>
  );
}
