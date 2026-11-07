import React, { useMemo } from "react";
import { BrainCircuit, ShieldAlert, Sparkles } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { fmt, signedPct } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

function swingLevels(bars) {
  const rows = (bars || []).filter((b) => b.low != null && b.high != null);
  if (!rows.length) return { support: null, resistance: null };
  const recent = rows.slice(-30);
  return {
    support: Math.min(...recent.map((b) => Number(b.low))),
    resistance: Math.max(...recent.map((b) => Number(b.high))),
  };
}

export default function AIInsights({ symbol, data, bars, loading, error, onRetry }) {
  const facts = data?.facts;
  const interp = data?.interpretations;
  const available = data?.available !== false && facts;
  const { support, resistance } = useMemo(() => swingLevels(bars), [bars]);
  const stance = interp?.strategy_manager?.split(".")[0] || "NEUTRAL";

  return (
    <Panel
      className="h-full"
      title={<span className="flex items-center gap-1.5"><BrainCircuit size={12} className="text-ai" /> AI market intelligence</span>}
      dense
      bodyClass="flex flex-col min-h-0"
      actions={<span className="badge badge-ai normal-case tracking-normal">ANALYSIS · NOT PREDICTION</span>}
    >
      <div className="flex-1 scroll-area min-h-0 p-3 space-y-3">
        {loading && (
          <div className="space-y-2">
            <div className="skeleton h-4 w-2/3" />
            <div className="skeleton h-16" />
            <div className="skeleton h-12" />
          </div>
        )}

        {!loading && !available && (
          <div className="text-2xs text-muted leading-relaxed">
            <div className="badge badge-down mb-2">AI ANALYSIS UNAVAILABLE</div>
            {data?.reason || error?.detail?.reason || error?.detail || "Insufficient market data to compute analysis."}
            <button className="btn btn-xs btn-ai mt-2" onClick={onRetry}>Retry</button>
          </div>
        )}

        {!loading && available && (
          <>
            <div className="flex items-center gap-2">
              <span className="badge badge-ai">{stance}</span>
              <span className="text-2xs text-muted-2">{displayName(symbol)} · derived from provider bars</span>
            </div>

            <div className="grid grid-cols-2 gap-x-3 gap-y-2">
              {[
                ["RSI 14", facts.rsi14, facts.rsi14 > 65 ? "overbought" : facts.rsi14 < 35 ? "oversold" : "neutral"],
                ["EMA 20", fmt(facts.ema20), "trend"],
                ["EMA 50", fmt(facts.ema50), "trend"],
                ["MACD hist", facts.macd_hist, facts.macd_hist >= 0 ? "positive" : "negative"],
                ["Ann. vol 30d", `${facts.ann_vol_30d_pct}%`, "volatility"],
                ["30-bar return", signedPct(facts.return_30bar_pct), "momentum"],
              ].map(([label, value, hint]) => (
                <div key={label} className="min-w-0">
                  <div className="text-2xs uppercase tracking-wider text-muted-2">{label}</div>
                  <div className="num text-xs text-text">{value ?? "—"}</div>
                  <div className="text-2xs text-muted-2">{hint}</div>
                </div>
              ))}
            </div>

            <div className="border-t border-line-soft pt-2 grid grid-cols-2 gap-3">
              <div>
                <div className="text-2xs uppercase tracking-wider text-muted-2">Support (30-bar low)</div>
                <div className="num text-xs text-up">{support == null ? "—" : fmt(support)}</div>
              </div>
              <div>
                <div className="text-2xs uppercase tracking-wider text-muted-2">Resistance (30-bar high)</div>
                <div className="num text-xs text-down">{resistance == null ? "—" : fmt(resistance)}</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="text-2xs uppercase tracking-wider text-muted-2 flex items-center gap-1"><Sparkles size={10} /> Bullish evidence</div>
              {(interp?.bull || []).length === 0 && <div className="text-2xs text-muted-2">No bullish evidence in the current window.</div>}
              {(interp?.bull || []).map((t, i) => (
                <div key={i} className="text-2xs text-muted flex gap-1.5"><span className="text-up">▲</span>{t}</div>
              ))}
            </div>

            <div className="space-y-1.5">
              <div className="text-2xs uppercase tracking-wider text-muted-2 flex items-center gap-1"><ShieldAlert size={10} /> Bearish / risk evidence</div>
              {(interp?.bear || []).length === 0 && <div className="text-2xs text-muted-2">No bearish evidence in the current window.</div>}
              {(interp?.bear || []).map((t, i) => (
                <div key={i} className="text-2xs text-muted flex gap-1.5"><span className="text-down">▼</span>{t}</div>
              ))}
            </div>

            <div className="border-t border-line-soft pt-2 space-y-1">
              <div className="text-2xs text-muted leading-relaxed">{interp?.market_analyst}</div>
              <div className="text-2xs text-amber leading-relaxed">{interp?.risk_analyst}</div>
              <div className="text-2xs text-muted-2 leading-relaxed">
                Scenario: watch a hold above support {support == null ? "—" : fmt(support)}; a close below it invalidates the bullish case.
                A rejection near resistance {resistance == null ? "—" : fmt(resistance)} favours caution. Analysis of past data — not a forecast.
              </div>
            </div>
          </>
        )}
      </div>
    </Panel>
  );
}
