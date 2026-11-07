import React from "react";
import { Building2, Globe2 } from "lucide-react";
import Panel, { StatusDot } from "../ui/Panel.jsx";
import { fmt, signed, signedPct, pnlColor } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

function Row({ item, onSelect, selected }) {
  const unavailable = item.status === "UNAVAILABLE" || item.price == null;
  return (
    <button
      onClick={() => !unavailable && onSelect?.(item.symbol)}
      className={`w-full flex items-center gap-2 px-3 py-1.5 border-b border-line-soft/60 text-left hover:bg-surface/60 ${selected ? "bg-ai/10" : ""} ${unavailable ? "cursor-default opacity-60" : ""}`}
      title={item.reason || item.provider || ""}
    >
      <div className="min-w-0 flex-1">
        <div className="text-xs truncate">{displayName(item.symbol, item.name)}</div>
        <div className="text-2xs text-muted-2">{item.exchange || "NSE"}</div>
      </div>
      {unavailable ? (
        <span className="badge badge-down">UNAVAILABLE</span>
      ) : (
        <>
          <div className="num text-xs text-right">{fmt(item.price)}</div>
          <div className={`num text-2xs w-[62px] text-right ${pnlColor(item.change_pct)}`}>{signedPct(item.change_pct)}</div>
        </>
      )}
    </button>
  );
}

export default function MarketIndices({ items = [], session, selected, onSelect, loading }) {
  const vix = items.find((i) => i.symbol === "^INDIAVIX");
  return (
    <Panel
      className="h-full"
      title={<span className="flex items-center gap-1.5"><Globe2 size={12} /> Market overview</span>}
      dense
      bodyClass="flex flex-col min-h-0"
      actions={<span className="flex items-center gap-1.5 normal-case tracking-normal"><StatusDot status={session?.status} /><span className="text-2xs text-muted">{session?.status || "—"}</span></span>}
    >
      <div className="px-3 py-2 border-b border-line-soft flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-2xs text-muted">
          <Building2 size={11} />
          <span>NSE / BSE</span>
        </div>
        <span className="badge text-muted-2">{session?.label || "Session status unavailable"}</span>
        <span className="ml-auto num text-2xs text-muted-2">{session?.open || "09:15"}–{session?.close || "15:30"} IST</span>
      </div>

      {!loading && vix && (
        <div className="px-3 py-2 border-b border-line-soft flex items-center gap-2">
          <span className="text-2xs uppercase tracking-wider text-muted-2">INDIA VIX</span>
          <span className="num text-sm text-text">{vix.price == null ? "—" : fmt(vix.price)}</span>
          <span className={`num text-2xs ml-auto ${pnlColor(vix.change_pct)}`}>{vix.change_pct == null ? "—" : signedPct(vix.change_pct)}</span>
        </div>
      )}

      <div className="scroll-area flex-1 min-h-0">
        {loading && items.length === 0 && (
          <div className="p-2 space-y-1.5">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-8" />)}</div>
        )}
        {items.map((item) => (
          <Row key={item.symbol} item={item} selected={selected === item.symbol} onSelect={onSelect} />
        ))}
        {!loading && items.length === 0 && (
          <div className="p-3 text-2xs text-muted">Index snapshot unavailable from the configured provider.</div>
        )}
      </div>
    </Panel>
  );
}
