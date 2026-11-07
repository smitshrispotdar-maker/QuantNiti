import React, { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import MarketOverview from "../components/market/MarketOverview.jsx";
import WatchlistPanel from "../components/market/WatchlistPanel.jsx";
import ChartPanel from "../components/market/ChartPanel.jsx";
import MarketIndices from "../components/market/MarketIndices.jsx";
import MarketMovers from "../components/market/MarketMovers.jsx";
import TradeTape from "../components/market/TradeTape.jsx";
import AIInsights from "../components/market/AIInsights.jsx";
import PaperTicket from "../components/market/PaperTicket.jsx";
import useMarketStream from "../hooks/useMarketStream.js";
import { api, marketApi, watchlistApi } from "../api.jsx";
import { DEFAULT_SYMBOL, TIMEFRAMES, isIndianSymbol } from "../market/instruments.js";

// Backwards-compatible named export retained for the data-quality test suite
// and for consumers of the previous dashboard.
export { DataQualityPanel } from "../components/DataQualityPanel.jsx";

const SYMBOL_KEY = "quantniti_selected_symbol";
const TF_KEY = "quantniti_timeframe";
const LEFT_KEY = "quantniti_left_width";
const RIGHT_KEY = "quantniti_right_width";

function useResizable(initial, key, min = 210, max = 420, invert = false) {
  const [width, setWidth] = useState(() => {
    const saved = Number(localStorage.getItem(key));
    return saved > min && saved < max ? saved : initial;
  });
  const dragging = useRef(false);
  const widthRef = useRef(width);
  const startRef = useRef({ x: 0, w: initial });

  useEffect(() => {
    widthRef.current = width;
  }, [width]);

  useEffect(() => {
    const onMove = (e) => {
      if (!dragging.current) return;
      const delta = e.clientX - startRef.current.x;
      const next = Math.max(min, Math.min(max, startRef.current.w + (invert ? -delta : delta)));
      setWidth(next);
    };
    const onUp = () => {
      if (!dragging.current) return;
      dragging.current = false;
      document.body.style.cursor = "";
      localStorage.setItem(key, String(widthRef.current));
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [min, max, key, invert]);

  const start = (e) => {
    dragging.current = true;
    startRef.current = { x: e.clientX, w: width };
    document.body.style.cursor = "col-resize";
  };

  return { width, setWidth, start };
}

export default function Dashboard() {
  const [symbol, setSymbol] = useState(() => {
    const saved = localStorage.getItem(SYMBOL_KEY);
    return isIndianSymbol(saved) ? saved : DEFAULT_SYMBOL;
  });
  const [timeframe, setTimeframeState] = useState(() => {
    const saved = localStorage.getItem(TF_KEY);
    return TIMEFRAMES.some((t) => t.id === saved) ? saved : "1d";
  });
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(true);
  const [bars, setBars] = useState([]);
  const [meta, setMeta] = useState(null);
  const [barsLoading, setBarsLoading] = useState(true);
  const [barsError, setBarsError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [watchLoading, setWatchLoading] = useState(true);
  const [watchError, setWatchError] = useState(null);
  const [indices, setIndices] = useState([]);
  const [indicesLoading, setIndicesLoading] = useState(true);
  const [session, setSession] = useState(null);
  const [movers, setMovers] = useState(null);
  const [moversLoading, setMoversLoading] = useState(true);
  const [tape, setTape] = useState(null);
  const [tapeLoading, setTapeLoading] = useState(true);
  const [research, setResearch] = useState(null);
  const [researchLoading, setResearchLoading] = useState(true);
  const [researchError, setResearchError] = useState(null);
  const [paperDetail, setPaperDetail] = useState(null);
  const [toast, setToast] = useState(null);

  const left = useResizable(Number(localStorage.getItem(LEFT_KEY)) || 250, LEFT_KEY, 210, 380);
  const right = useResizable(Number(localStorage.getItem(RIGHT_KEY)) || 330, RIGHT_KEY, 280, 460, true);
  const stream = useMarketStream(symbol, timeframe);

  const setTimeframe = (tf) => {
    setTimeframeState(tf);
    localStorage.setItem(TF_KEY, tf);
  };

  const selectSymbol = useCallback((next) => {
    if (!next) return;
    setSymbol(next);
    localStorage.setItem(SYMBOL_KEY, next);
  }, []);

  const loadQuote = useCallback(async (sym) => {
    setQuoteLoading(true);
    try {
      const data = await marketApi.overview(sym);
      setQuote(data);
    } catch (e) {
      setQuote((prev) => (prev?.symbol === sym ? { ...prev, status: "UNAVAILABLE", available: false, reason: e.detail?.detail || String(e.detail || e.message) } : null));
    } finally {
      setQuoteLoading(false);
    }
  }, []);

  const loadBars = useCallback(async (sym, tf) => {
    setBarsLoading(true);
    setBarsError(null);
    try {
      const data = await marketApi.bars(sym, tf, 500);
      setBars(Array.isArray(data?.bars) ? data.bars : []);
      setMeta(data?.meta || null);
    } catch (e) {
      setBars([]);
      setMeta(null);
      setBarsError(e);
    } finally {
      setBarsLoading(false);
    }
  }, []);

  const loadWatchlist = useCallback(async () => {
    setWatchLoading(true);
    setWatchError(null);
    try {
      const list = await watchlistApi.get();
      setWatchlist(Array.isArray(list) ? list : []);
    } catch (e) {
      setWatchError(e);
    } finally {
      setWatchLoading(false);
    }
  }, []);

  const loadIndices = useCallback(async () => {
    setIndicesLoading(true);
    try {
      const data = await api("/api/market/indices");
      setIndices(Array.isArray(data?.items) ? data.items : []);
      if (data?.session) setSession(data.session);
    } catch {
      setIndices([]);
    } finally {
      setIndicesLoading(false);
    }
  }, []);

  const loadSession = useCallback(async () => {
    try {
      const data = await api("/api/market/status");
      setSession(data?.exchanges?.NSE || data);
    } catch {
      /* status remains unknown */
    }
  }, []);

  const loadMovers = useCallback(async () => {
    setMoversLoading(true);
    try {
      setMovers(await marketApi.movers(5));
    } catch (e) {
      setMovers({ available: false, reason: e.detail?.detail || String(e.detail || e.message), gainers: [], losers: [], volume: [] });
    } finally {
      setMoversLoading(false);
    }
  }, []);

  const loadTape = useCallback(async (sym) => {
    setTapeLoading(true);
    try {
      setTape(await marketApi.tape(sym));
    } catch (e) {
      setTape({ available: false, reason: e.detail?.detail || String(e.detail || e.message), items: [] });
    } finally {
      setTapeLoading(false);
    }
  }, []);

  const loadResearch = useCallback(async (sym) => {
    setResearchLoading(true);
    setResearchError(null);
    try {
      const data = await marketApi.research(sym, "1d");
      setResearch(data);
    } catch (e) {
      setResearch(null);
      setResearchError(e);
    } finally {
      setResearchLoading(false);
    }
  }, []);

  // Symbol/timeframe-driven requests.
  useEffect(() => {
    loadBars(symbol, timeframe);
  }, [symbol, timeframe, loadBars]);

  useEffect(() => {
    loadQuote(symbol);
    loadTape(symbol);
    loadResearch(symbol);
  }, [symbol, loadQuote, loadTape, loadResearch]);

  // Initial + periodically refreshed market context.
  useEffect(() => {
    loadWatchlist();
    loadIndices();
    loadMovers();
    loadSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      loadWatchlist();
      loadIndices();
      loadMovers();
      loadSession();
      loadQuote(symbol);
      loadBars(symbol, timeframe);
    }, 60000);
    return () => clearInterval(timer);
  }, [symbol, timeframe, loadWatchlist, loadIndices, loadMovers, loadSession, loadQuote, loadBars]);

  // Merge the server WebSocket snapshot (clearly delayed, not a provider live feed).
  useEffect(() => {
    const snap = stream.snapshot;
    if (!snap || snap.symbol !== symbol) return;
    if (snap.timeframe && snap.timeframe !== timeframe) return;
    setQuote((prev) => ({
      ...(prev || {}),
      ...snap,
      capabilities: prev?.capabilities,
      name: prev?.name,
      exchange: prev?.exchange,
      kind: prev?.kind,
      fetched_at: snap.fetched_at || prev?.fetched_at,
    }));

    // Keep the latest candle in sync with the snapshot stream. This is a
    // polled provider snapshot, so it is still labelled DELAYED in the UI.
    if (snap.price == null) return;
    setBars((prev) => {
      if (!prev.length || !snap.last_bar) return prev;
      const stamp = (v) => String(v || "").replace(" ", "T").slice(0, 16);
      const key = stamp(snap.last_bar);
      const idx = prev.findIndex((b) => stamp(b.ts) === key);
      if (idx >= 0) {
        const next = [...prev];
        const row = next[idx];
        next[idx] = {
          ...row,
          close: snap.price,
          high: Math.max(Number(row.high), Number(snap.high ?? snap.price)),
          low: Math.min(Number(row.low), Number(snap.low ?? snap.price)),
          volume: snap.volume ?? row.volume,
        };
        return next;
      }
      if (stamp(snap.last_bar) > stamp(prev[prev.length - 1]?.ts)) {
        return [...prev, {
          ts: snap.last_bar,
          open: snap.open ?? snap.price,
          high: snap.high ?? snap.price,
          low: snap.low ?? snap.price,
          close: snap.price,
          volume: snap.volume ?? 0,
        }];
      }
      return prev;
    });
  }, [stream.snapshot, symbol, timeframe]);

  // Watchlist mutations.
  const addSymbol = async (next) => {
    setToast(null);
    try {
      await watchlistApi.add(next);
      await loadWatchlist();
      selectSymbol(next);
    } catch (e) {
      const msg = e.detail?.detail || e.detail || e.message;
      if (String(msg).toLowerCase().includes("already")) selectSymbol(next);
      else setToast({ kind: "error", text: String(msg) });
    }
  };

  const removeSymbol = async (next) => {
    setToast(null);
    try {
      await watchlistApi.remove(next);
      await loadWatchlist();
      if (next === symbol) selectSymbol(DEFAULT_SYMBOL);
    } catch (e) {
      setToast({ kind: "error", text: String(e.detail?.detail || e.detail || e.message) });
    }
  };

  const reorder = async (symbols) => {
    const map = new Map(watchlist.map((i) => [i.symbol, i]));
    setWatchlist(symbols.map((s) => map.get(s)).filter(Boolean));
    try {
      await watchlistApi.reorder(symbols);
    } catch {
      loadWatchlist();
    }
  };

  const onPaperData = useCallback((detail) => setPaperDetail(detail), []);
  const paperOrders = Array.isArray(paperDetail?.orders) ? paperDetail.orders : [];
  const rawPaperPosition =
    (paperDetail?.positions || []).find((p) => p.symbol === symbol && Math.abs(p.qty) > 1e-9) || null;
  // Deployment positions carry percentage risk settings rather than absolute
  // price levels. Derive chart SL/TP lines from the entry price for display.
  const paperPosition = (() => {
    if (!rawPaperPosition) return null;
    const deployment = paperDetail?.deployment;
    const entry = Number(rawPaperPosition.avg_entry_price ?? rawPaperPosition.avg_price ?? 0);
    const slPct = Number(deployment?.stop_loss_pct || 0);
    const tpPct = Number(deployment?.take_profit_pct || 0);
    return {
      ...rawPaperPosition,
      stop_loss_price: rawPaperPosition.stop_loss_price ?? (entry && slPct > 0 ? entry * (1 - slPct / 100) : null),
      take_profit_price: rawPaperPosition.take_profit_price ?? (entry && tpPct > 0 ? entry * (1 + tpPct / 100) : null),
    };
  })();

  return (
    <div className="h-full flex flex-col gap-2 p-2 overflow-hidden">
      <MarketOverview
        quote={quote}
        symbol={symbol}
        session={session}
        loading={quoteLoading && !quote}
        error={null}
        onRetry={() => { loadQuote(symbol); loadBars(symbol, timeframe); }}
      />

      {toast && (
        <div className={`text-2xs px-2 py-1 rounded border ${toast.kind === "error" ? "border-down/40 bg-down/10 text-down" : "border-up/40 bg-up/10 text-up"}`}>
          {toast.text}
        </div>
      )}

      <div className="flex-1 min-h-0 flex flex-col xl:flex-row gap-2 overflow-y-auto xl:overflow-hidden">
        <div className="w-full xl:w-[var(--left-w)] h-[340px] xl:h-auto xl:min-h-0 shrink-0 xl:shrink flex flex-col" style={{ "--left-w": `${left.width}px` }}>
          <WatchlistPanel
            items={watchlist}
            selected={symbol}
            onSelect={selectSymbol}
            onAdd={addSymbol}
            onRemove={removeSymbol}
            onReorder={reorder}
            loading={watchLoading}
            error={watchError}
            onRetry={loadWatchlist}
          />
        </div>

        <div className="resizer-x hidden xl:block" onMouseDown={left.start} />

        <div className="w-full xl:flex-1 min-w-0 min-h-0 flex flex-col gap-2 shrink-0 xl:shrink">
          <div className="h-[460px] xl:h-auto xl:flex-1 xl:min-h-[330px] flex flex-col">
            <ChartPanel
              symbol={symbol}
              timeframe={timeframe}
              setTimeframe={setTimeframe}
              bars={bars}
              meta={meta}
              loading={barsLoading}
              error={barsError}
              onRetry={() => loadBars(symbol, timeframe)}
              orders={paperOrders}
              position={paperPosition}
              streamState={stream.state}
            />
          </div>
          <div className="h-[280px] xl:h-[250px] xl:min-h-[220px] shrink-0">
            <AIInsights
              symbol={symbol}
              data={research}
              bars={bars}
              loading={researchLoading}
              error={researchError}
              onRetry={() => loadResearch(symbol)}
            />
          </div>
        </div>

        <div className="resizer-x hidden xl:block" onMouseDown={right.start} />

        <div
          className="w-full xl:w-[var(--right-w)] min-h-0 flex flex-col gap-2 xl:overflow-y-auto xl:scroll-area shrink-0 xl:shrink"
          style={{ "--right-w": `${right.width}px` }}
        >
          <div className="h-[225px] shrink-0"><MarketIndices items={indices} session={session} selected={symbol} onSelect={selectSymbol} loading={indicesLoading} /></div>
          <div className="h-[235px] shrink-0"><MarketMovers data={movers} loading={moversLoading} onSelect={selectSymbol} /></div>
          <div className="h-[170px] shrink-0"><TradeTape symbol={symbol} tape={tape} loading={tapeLoading} /></div>
          <div className="h-[430px] shrink-0"><PaperTicket symbol={symbol} price={quote?.price} onPaperData={onPaperData} onSelect={selectSymbol} /></div>
        </div>
      </div>

      <div className="hidden xl:flex items-center gap-3 px-1 text-2xs text-muted-2">
        <span>Provider: {quote?.provider || "Yahoo Finance"} · delayed NSE/BSE data</span>
        <span>·</span>
        <span>Quotes never labelled LIVE unless a licensed realtime feed is connected.</span>
        <span className="ml-auto flex items-center gap-1"><RefreshCw size={10} /> auto-refresh 60s</span>
      </div>
    </div>
  );
}
