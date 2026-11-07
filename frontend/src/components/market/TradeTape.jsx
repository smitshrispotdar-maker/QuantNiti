import React from "react";
import { Radio } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { fmt, fmtCompact } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

/**
 * Exchange trade prints. The configured free provider does not supply a
 * licensed NSE/BSE transaction feed, so this panel intentionally shows an
 * explicit unavailable state instead of simulated prints.
 */
export default function TradeTape({ symbol, tape, loading }) {
  const items = tape?.items || [];
  const available = tape?.available && items.length > 0;

  return (
    <Panel
      className="h-full"
      title={<span className="flex items-center gap-1.5"><Radio size={12} /> Market trade tape</span>}
      dense
      bodyClass="flex flex-col min-h-0"
      actions={<span className="badge text-muted-2 normal-case tracking-normal">{displayName(symbol)}</span>}
    >
      {loading && <div className="p-2 space-y-1.5">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-5" />)}</div>}
      {!loading && !available && (
        <div className="p-3">
          <div className="badge badge-down mb-1.5">NOT CONNECTED</div>
          <div className="text-2xs text-muted leading-relaxed">
            {tape?.reason || "No exchange trade-print feed is connected."}
          </div>
          <div className="text-2xs text-muted-2 mt-2 leading-relaxed">
            Provider: {tape?.provider || "YAHOO FINANCE"}. QuantNiti will not fabricate market transactions.
          </div>
        </div>
      )}
      {!loading && available && (
        <div className="scroll-area flex-1 min-h-0">
          <div className="grid grid-cols-3 px-3 py-1 text-2xs uppercase tracking-wider text-muted-2 border-b border-line-soft">
            <span>Time</span><span className="text-right">Price</span><span className="text-right">Qty</span>
          </div>
          {items.map((t, i) => (
            <div key={`${t.time}-${i}`} className="grid grid-cols-3 px-3 py-1 border-b border-line-soft/50 text-2xs">
              <span className="num text-muted">{t.time}</span>
              <span className={`num text-right ${t.side === "SELL" ? "text-down" : "text-up"}`}>{fmt(t.price)}</span>
              <span className="num text-right text-muted">{fmtCompact(t.qty)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
