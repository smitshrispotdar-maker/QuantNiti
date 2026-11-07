import React, { useEffect, useMemo, useRef, useState } from "react";
import { createChart, ColorType, CrosshairMode, LineStyle } from "lightweight-charts";
import { Maximize2, RotateCcw } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { TIMEFRAMES, displayName } from "../../market/instruments.js";
import { ema, bollinger, rsi, macd, toLineData } from "../../market/indicators.js";
import { Badge, fmt, fmtCompact, pnlColor, signedPct } from "../../api.jsx";

const UP = "#16C784";
const DOWN = "#EA3943";

const OVERLAYS = [
  { id: "ema9", label: "EMA 9", color: "#F0B90B" },
  { id: "ema21", label: "EMA 21", color: "#38BDF8" },
  { id: "ema50", label: "EMA 50", color: "#A78BFA" },
  { id: "ema200", label: "EMA 200", color: "#F472B6" },
  { id: "bb", label: "Bollinger", color: "#64748B" },
];

function chartTime(ts, timeframe) {
  if (!ts) return null;
  if (timeframe === "1d" || timeframe === "1w") {
    const day = String(ts).slice(0, 10);
    return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
  }
  const ms = new Date(ts).getTime();
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
}

function prepare(bars, timeframe) {
  const seen = new Set();
  const rows = [];
  for (const b of bars || []) {
    const time = chartTime(b.ts, timeframe);
    if (!time || seen.has(time) || b.open == null || b.close == null) continue;
    seen.add(time);
    rows.push({
      time,
      open: Number(b.open),
      high: Number(b.high),
      low: Number(b.low),
      close: Number(b.close),
      volume: Number(b.volume || 0),
    });
  }
  rows.sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
  return rows;
}

export default function ChartPanel({
  symbol, timeframe, setTimeframe, bars = [], meta, loading, error, onRetry,
  orders = [], position = null, streamState = "idle",
}) {
  const shellRef = useRef(null);
  const chartRef = useRef(null);
  const candleRef = useRef(null);
  const volumeRef = useRef(null);
  const lineRefs = useRef({});
  const priceLinesRef = useRef([]);
  const subRef = useRef(null);
  const subChartRef = useRef(null);
  const syncingRef = useRef(false);

  const [overlays, setOverlays] = useState({ ema9: true, ema21: true, ema50: true, ema200: false, bb: false });
  const [sub, setSub] = useState("volume");
  const [hover, setHover] = useState(null);
  const isTest = import.meta.env.MODE === "test";

  const rows = useMemo(() => prepare(bars, timeframe), [bars, timeframe]);
  const latest = rows[rows.length - 1];
  const first = rows[0];
  const periodChange = latest && first ? ((latest.close / first.open - 1) * 100) : null;

  useEffect(() => {
    if (isTest || !shellRef.current) return undefined;
    const el = shellRef.current;
    let chart;
    try {
      chart = createChart(el, {
        width: el.clientWidth,
        height: el.clientHeight,
        layout: {
          background: { type: ColorType.Solid, color: "#0F141D" },
          textColor: "#7C8AA0",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
        },
        grid: { vertLines: { color: "#141B26" }, horzLines: { color: "#141B26" } },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: { color: "#2B3A52", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#1A2230" },
          horzLine: { color: "#2B3A52", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#1A2230" },
        },
        rightPriceScale: { borderColor: "#212B3A", scaleMargins: { top: 0.06, bottom: 0.24 } },
        timeScale: { borderColor: "#212B3A", timeVisible: timeframe !== "1d" && timeframe !== "1w", secondsVisible: false, rightOffset: 6 },
        localization: { priceFormatter: (p) => Number(p).toLocaleString("en-IN", { maximumFractionDigits: 2 }) },
      });
    } catch {
      return undefined;
    }
    chartRef.current = chart;

    candleRef.current = chart.addCandlestickSeries({
      upColor: UP, downColor: DOWN, borderVisible: false, wickUpColor: UP, wickDownColor: DOWN,
      priceLineStyle: LineStyle.Dotted, priceLineColor: "#38BDF8",
    });
    volumeRef.current = chart.addHistogramSeries({
      priceFormat: { type: "volume" }, priceScaleId: "vol", lastValueVisible: false, priceLineVisible: false,
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    lineRefs.current = {};
    for (const o of OVERLAYS) {
      if (o.id === "bb") {
        lineRefs.current.bbUpper = chart.addLineSeries({ color: o.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        lineRefs.current.bbLower = chart.addLineSeries({ color: o.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, lineStyle: LineStyle.Dotted });
      } else {
        lineRefs.current[o.id] = chart.addLineSeries({
          color: o.color, lineWidth: 1, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        });
      }
    }

    chart.subscribeCrosshairMove((param) => {
      if (!param?.time || !param.seriesData?.get(candleRef.current)) {
        setHover(null);
        return;
      }
      const c = param.seriesData.get(candleRef.current);
      const v = param.seriesData.get(volumeRef.current);
      setHover({ time: param.time, open: c.open, high: c.high, low: c.low, close: c.close, volume: v?.value });
    });

    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      if (!e) return;
      chart.applyOptions({ width: Math.floor(e.contentRect.width), height: Math.floor(e.contentRect.height) });
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
      lineRefs.current = {};
      subChartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTest]);

  // Main price / overlay data.
  useEffect(() => {
    if (isTest || !candleRef.current) return;
    chartRef.current?.applyOptions({
      timeScale: { timeVisible: timeframe !== "1d" && timeframe !== "1w", secondsVisible: false },
    });
    const times = rows.map((r) => r.time);
    candleRef.current.setData(rows);
    volumeRef.current?.setData(rows.map((r) => ({
      time: r.time, value: r.volume, color: r.close >= r.open ? "rgba(22,199,132,0.35)" : "rgba(234,57,67,0.35)",
    })));

    const closes = rows.map((r) => r.close);
    const seriesConfig = { ema9: ema(closes, 9), ema21: ema(closes, 21), ema50: ema(closes, 50), ema200: ema(closes, 200) };
    for (const [id, values] of Object.entries(seriesConfig)) {
      lineRefs.current[id]?.setData(toLineData(times, values));
      lineRefs.current[id]?.applyOptions({ visible: !!overlays[id] });
    }
    const bb = bollinger(closes, 20, 2);
    lineRefs.current.bbUpper?.setData(toLineData(times, bb.upper));
    lineRefs.current.bbLower?.setData(toLineData(times, bb.lower));
    lineRefs.current.bbUpper?.applyOptions({ visible: !!overlays.bb });
    lineRefs.current.bbLower?.applyOptions({ visible: !!overlays.bb });

    // Buy/sell markers from simulated paper orders (clearly labelled).
    const markers = [];
    const timeBySymbolOrder = new Map();
    for (const o of orders) {
      if (o.symbol !== symbol) continue;
      const t = chartTime(o.ts, timeframe);
      if (!t) continue;
      const key = `${t}-${o.side}`;
      if (timeBySymbolOrder.has(key)) continue;
      timeBySymbolOrder.set(key, true);
      markers.push({
        time: t,
        position: o.side === "BUY" ? "belowBar" : "aboveBar",
        color: o.side === "BUY" ? UP : DOWN,
        shape: o.side === "BUY" ? "arrowUp" : "arrowDown",
        text: `PAPER ${o.side}`,
      });
    }
    markers.sort((a, b) => (a.time > b.time ? 1 : -1));
    candleRef.current.setMarkers(markers);

    // Stop-loss / take-profit levels from the open simulated position.
    for (const line of priceLinesRef.current) {
      try { candleRef.current.removePriceLine(line); } catch { /* stale */ }
    }
    priceLinesRef.current = [];
    if (position && position.symbol === symbol) {
      if (position.stop_loss_price) {
        priceLinesRef.current.push(candleRef.current.createPriceLine({
          price: Number(position.stop_loss_price), color: DOWN, lineWidth: 1, lineStyle: LineStyle.Dashed,
          axisLabelVisible: true, title: "SL",
        }));
      }
      if (position.take_profit_price) {
        priceLinesRef.current.push(candleRef.current.createPriceLine({
          price: Number(position.take_profit_price), color: UP, lineWidth: 1, lineStyle: LineStyle.Dashed,
          axisLabelVisible: true, title: "TP",
        }));
      }
    }

    const visible = overlays;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, overlays, orders, position, symbol, timeframe, isTest]);

  // Sub-pane (volume is drawn on the main chart; RSI/MACD get their own pane).
  useEffect(() => {
    if (isTest || !shellRef.current) return undefined;
    if (sub === "volume") return undefined;
    const el = document.getElementById(`subchart-${symbol.replace(/[^a-z0-9]/gi, "")}`);
    if (!el) return undefined;
    let chart;
    try {
      chart = createChart(el, {
        width: el.clientWidth, height: 110,
        layout: { background: { type: ColorType.Solid, color: "#0F141D" }, textColor: "#7C8AA0", fontFamily: "'JetBrains Mono', monospace", fontSize: 9 },
        grid: { vertLines: { color: "#141B26" }, horzLines: { color: "#141B26" } },
        rightPriceScale: { borderColor: "#212B3A", scaleMargins: { top: 0.1, bottom: 0.1 } },
        timeScale: { borderColor: "#212B3A", timeVisible: timeframe !== "1d" && timeframe !== "1w", secondsVisible: false, visible: false },
        crosshair: { mode: CrosshairMode.Normal, vertLine: { color: "#2B3A52", style: LineStyle.Dashed }, horzLine: { color: "#2B3A52", style: LineStyle.Dashed } },
        handleScroll: false, handleScale: false,
      });
    } catch {
      return undefined;
    }
    subChartRef.current = chart;
    const times = rows.map((r) => r.time);
    const closes = rows.map((r) => r.close);

    if (sub === "rsi") {
      const s = chart.addLineSeries({ color: "#38BDF8", lineWidth: 1, priceLineVisible: false, lastValueVisible: true });
      s.setData(toLineData(times, rsi(closes, 14)));
      for (const level of [30, 70]) {
        s.createPriceLine({ price: level, color: level === 70 ? "#EA3943" : "#16C784", lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: String(level) });
      }
    } else {
      const m = macd(closes);
      const hist = chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });
      hist.setData(times.map((t, i) => ({ time: t, value: m.hist[i] ?? 0, color: (m.hist[i] ?? 0) >= 0 ? "rgba(22,199,132,0.5)" : "rgba(234,57,67,0.5)" })));
      chart.addLineSeries({ color: "#38BDF8", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }).setData(toLineData(times, m.line));
      chart.addLineSeries({ color: "#F0B90B", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }).setData(toLineData(times, m.signal));
    }

    // Sync visible time range with the main chart.
    const main = chartRef.current;
    if (main) {
      const handler = (range) => {
        if (!range || syncingRef.current) return;
        syncingRef.current = true;
        try { chart.timeScale().setVisibleLogicalRange(range); } finally { syncingRef.current = false; }
      };
      const subHandler = (range) => {
        if (!range || syncingRef.current) return;
        syncingRef.current = true;
        try { main.timeScale().setVisibleLogicalRange(range); } finally { syncingRef.current = false; }
      };
      main.timeScale().subscribeVisibleLogicalRangeChange(handler);
      chart.timeScale().subscribeVisibleLogicalRangeChange(subHandler);
      return () => {
        try { main.timeScale().unsubscribeVisibleLogicalRangeChange(handler); } catch { /* removed */ }
        chart.remove();
        subChartRef.current = null;
      };
    }

    return () => { chart.remove(); subChartRef.current = null; };
  }, [sub, rows, symbol, timeframe, isTest]);

  const resetView = () => {
    chartRef.current?.timeScale().fitContent();
  };

  const hoverPct = hover && latest ? ((hover.close / latest.close - 1) * 100) : null;

  return (
    <Panel
      className="h-full min-h-0"
      dense
      bodyClass="flex flex-col min-h-0"
      title={
        <span className="flex items-center gap-2">
          <span className="text-text normal-case tracking-normal font-semibold text-xs">{displayName(symbol, meta?.name)}</span>
          <span className="badge text-muted-2">{meta?.exchange || (symbol.endsWith(".BO") ? "BSE" : "NSE")}</span>
          <Badge status={meta?.status || (loading ? "LOADING" : "UNAVAILABLE")} />
          {streamState === "open" && <span className="badge badge-ai">WS SNAPSHOT</span>}
          {streamState === "reconnecting" && <span className="badge badge-amber">RECONNECTING</span>}
        </span>
      }
      actions={
        <span className="flex items-center gap-1">
          {TIMEFRAMES.map((t) => (
            <button key={t.id} onClick={() => setTimeframe(t.id)} className={`btn btn-xs ${timeframe === t.id ? "btn-ai" : "btn-ghost"}`}>
              {t.label}
            </button>
          ))}
          <span className="w-px h-4 bg-line mx-1" />
          {OVERLAYS.map((o) => (
            <button key={o.id} onClick={() => setOverlays((v) => ({ ...v, [o.id]: !v[o.id] }))}
              className={`btn btn-xs ${overlays[o.id] ? "text-text border-line" : "btn-ghost"}`}
              style={overlays[o.id] ? { borderColor: `${o.color}66`, color: o.color } : undefined}>
              {o.label}
            </button>
          ))}
          <button className="btn btn-xs btn-ghost" onClick={resetView} title="Reset view"><RotateCcw size={12} /></button>
        </span>
      }
    >
      <div className="flex items-center gap-3 px-3 py-2 border-b border-line-soft text-2xs">
        <div className="flex items-baseline gap-2">
          <span className="num text-lg text-text">{latest ? fmt(latest.close) : "—"}</span>
          <span className={`num ${pnlColor(periodChange)}`}>{periodChange == null ? "—" : signedPct(periodChange)}</span>
        </div>
        <div className="flex items-center gap-3 text-muted-2">
          <span>O <b className="num text-text/80">{hover ? fmt(hover.open) : latest ? fmt(latest.open) : "—"}</b></span>
          <span>H <b className="num text-text/80">{hover ? fmt(hover.high) : latest ? fmt(latest.high) : "—"}</b></span>
          <span>L <b className="num text-text/80">{hover ? fmt(hover.low) : latest ? fmt(latest.low) : "—"}</b></span>
          <span>C <b className="num text-text/80">{hover ? fmt(hover.close) : latest ? fmt(latest.close) : "—"}</b></span>
          <span>VOL <b className="num text-text/80">{fmtCompact(hover?.volume ?? latest?.volume)}</b></span>
        </div>
        <div className="ml-auto flex items-center gap-1">
          {["volume", "rsi", "macd"].map((id) => (
            <button key={id} onClick={() => setSub(id)} className={`btn btn-xs ${sub === id ? "btn-ai" : "btn-ghost"}`}>{id.toUpperCase()}</button>
          ))}
          <span className="badge text-muted-2 ml-1" title={meta?.source}>
            {meta?.source || "NO PROVIDER"} · {meta?.last_bar ? String(meta.last_bar).replace("T", " ").slice(0, 16) : "—"}
          </span>
          <Maximize2 size={12} className="text-muted-2 ml-1" />
        </div>
      </div>

      <div className="relative flex-1 min-h-[280px] chart-shell" ref={shellRef}>
        {isTest && (
          <div className="absolute inset-0 flex items-center justify-center text-muted text-xs">
            Chart canvas is available in the browser.
          </div>
        )}
        {!isTest && !loading && rows.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center px-6 bg-panel/80 z-10">
            <div className="text-xs text-text/80">No chart data</div>
            <div className="text-2xs text-muted max-w-sm">
              {error?.detail?.reason || error?.detail?.detail || meta?.data_quality?.issues?.[0] || "The configured provider returned no bars for this instrument/timeframe."}
            </div>
            <button className="btn btn-xs btn-ai" onClick={onRetry}>Retry</button>
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-panel/60 z-10">
            <div className="skeleton h-1 w-24" />
          </div>
        )}
      </div>

      <div id={`subchart-${symbol.replace(/[^a-z0-9]/gi, "")}`} className={`${sub === "volume" ? "hidden" : "block"} border-t border-line-soft`} style={{ height: 112 }} />
    </Panel>
  );
}
