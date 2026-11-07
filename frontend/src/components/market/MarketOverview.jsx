import React from "react";
import { Activity, Clock3, Server } from "lucide-react";
import { Badge, fmt, fmtCompact, fmtDateTime, signed, signedPct, pnlColor } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";
import { Stat, StatusDot } from "../ui/Panel.jsx";

export default function MarketOverview({ quote, symbol, session, loading, error, onRetry }) {
  const initialLoading = loading && !quote;
  const status = quote?.status || (initialLoading ? "LOADING" : "UNAVAILABLE");
  const change = quote?.change;
  const simulated = status === "SIMULATED";
  const unavailable = !initialLoading && (status === "UNAVAILABLE" || !quote?.available);

  return (
    <section className="card px-3 py-2.5">
      <div className="flex items-start gap-5 flex-wrap">
        <div className="min-w-[190px]">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-wide text-text">{displayName(quote?.symbol || symbol, quote?.name)}</h2>
            <span className="badge text-muted-2">{quote?.exchange || "NSE"}</span>
            <span className="badge text-muted-2">{quote?.kind === "index" ? "INDEX" : "EQUITY"}</span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className={`num text-2xl font-semibold ${unavailable ? "text-muted" : "text-text"}`}>
              {unavailable ? "—" : fmt(quote?.price)}
            </span>
            <span className={`num text-xs ${pnlColor(change)}`}>
              {unavailable ? "—" : `${signed(change)} (${signedPct(quote?.change_pct)})`}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            <Badge status={status} />
            <span className="text-2xs text-muted-2 flex items-center gap-1">
              <Server size={10} /> {quote?.provider || "NO PROVIDER"}
            </span>
            <span className="text-2xs text-muted-2 flex items-center gap-1">
              <Clock3 size={10} /> {fmtDateTime(quote?.fetched_at || quote?.last_bar)}
            </span>
          </div>
          {simulated && (
            <div className="mt-1.5 text-2xs text-ai">
              Simulated series (live provider disabled/unavailable). Not a market quote.
            </div>
          )}
          {unavailable && (
            <div className="mt-1.5 text-2xs text-down flex items-start gap-1">
              <span className="truncate">{quote?.reason || "Provider unavailable."}</span>
              <button className="underline shrink-0" onClick={onRetry}>Retry</button>
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-6 gap-x-5 gap-y-1.5 flex-1 min-w-[320px]">
          <Stat label="Open" value={unavailable ? "—" : fmt(quote?.open)} />
          <Stat label="High" value={unavailable ? "—" : fmt(quote?.high)} valueClass="text-up" />
          <Stat label="Low" value={unavailable ? "—" : fmt(quote?.low)} valueClass="text-down" />
          <Stat label="Prev close" value={unavailable ? "—" : fmt(quote?.prev_close)} />
          <Stat label="Volume" value={unavailable ? "—" : fmtCompact(quote?.volume)} hint={quote?.volume ? "provider reported" : "not reported"} />
          <Stat
            label="Market session"
            value={
              <span className="flex items-center gap-1.5">
                <StatusDot status={session?.status} />
                {session?.status || "—"}
              </span>
            }
            hint={`${session?.open || "09:15"}–${session?.close || "15:30"} IST`}
          />
        </div>

        <div className="min-w-[150px] text-right">
          <div className="text-2xs uppercase tracking-wider text-muted-2 flex items-center justify-end gap-1">
            <Activity size={11} /> Data integrity
          </div>
          <div className="text-2xs text-muted mt-1 leading-relaxed">
            {quote?.capabilities?.realtime
              ? "Licensed realtime feed"
              : "Delayed provider data — never labelled LIVE."}
          </div>
          <div className="text-2xs text-muted-2 mt-1">
            {quote?.capabilities?.trade_prints ? "Trade prints available" : "No exchange trade prints"}
          </div>
        </div>
      </div>
    </section>
  );
}
