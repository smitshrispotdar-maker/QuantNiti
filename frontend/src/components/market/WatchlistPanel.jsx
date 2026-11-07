import React, { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Plus, Search, Star, X } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { api, fmt, signedPct, pnlColor, ErrorBox, EmptyState } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

export default function WatchlistPanel({
  items = [], selected, onSelect, onAdd, onRemove, onReorder, loading, error, onRetry,
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => {
    const q = query.trim();
    if (!q) { setResults([]); setSearching(false); return undefined; }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const data = await api(`/api/market/search?q=${encodeURIComponent(q)}`);
        setResults(Array.isArray(data) ? data.slice(0, 8) : []);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 220);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const close = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setShowResults(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const add = async (symbol) => {
    setShowResults(false);
    setQuery("");
    setResults([]);
    await onAdd?.(symbol);
  };

  const move = (index, delta) => {
    const next = [...items];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    onReorder?.(next.map((i) => i.symbol));
  };

  return (
    <Panel
      className="h-full"
      title={<span className="flex items-center gap-1.5"><Star size={12} /> Watchlist</span>}
      actions={<span className="badge text-muted-2">{items.length}</span>}
      dense
      bodyClass="flex flex-col min-h-0"
    >
      <div className="p-2 border-b border-line-soft relative" ref={boxRef}>
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-2" />
          <input
            className="input pl-7 pr-7"
            placeholder="Search NSE/BSE instruments"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setShowResults(true); }}
            onFocus={() => setShowResults(true)}
            aria-label="Search instruments"
          />
          {query && (
            <button className="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-2 hover:text-text" onClick={() => { setQuery(""); setResults([]); }}>
              <X size={12} />
            </button>
          )}
        </div>
        {showResults && query && (
          <div className="absolute left-2 right-2 top-full z-30 mt-1 card overflow-hidden max-h-64 scroll-area fade-in">
            {searching && <div className="p-2 text-2xs text-muted">Searching…</div>}
            {!searching && results.length === 0 && <div className="p-2 text-2xs text-muted">No Indian instruments found.</div>}
            {results.map((r) => {
              const inList = items.some((i) => i.symbol === r.symbol);
              return (
                <button key={r.symbol} disabled={inList || r.available === false}
                  onClick={() => add(r.symbol)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-surface disabled:opacity-40 text-left">
                  <span className="text-xs text-text flex-1 truncate">{r.name || displayName(r.symbol)}</span>
                  <span className="text-2xs text-muted-2">{r.exchange || (r.symbol.endsWith(".BO") ? "BSE" : "NSE")}</span>
                  {r.available === false ? <span className="text-2xs text-down">N/A</span> : inList ? <span className="text-2xs text-muted-2">added</span> : <Plus size={11} className="text-ai" />}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {error && <div className="px-2"><ErrorBox err={error} onRetry={onRetry} /></div>}

      <div className="flex-1 scroll-area min-h-0">
        {loading && items.length === 0 && (
          <div className="p-2 space-y-1.5">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton h-8" />)}</div>
        )}
        {!loading && items.length === 0 && (
          <EmptyState title="Watchlist is empty" hint="Search NIFTY 50, BANK NIFTY, RELIANCE or any NSE/BSE instrument." icon={<Star size={18} />} />
        )}
        {items.map((item, idx) => {
          const active = item.symbol === selected;
          return (
            <div key={item.symbol}
              className={`group relative flex items-center gap-2 px-2 py-1.5 border-b border-line-soft/60 cursor-pointer hover:bg-surface/70 ${active ? "bg-ai/10 border-l-2 border-l-ai" : "border-l-2 border-l-transparent"}`}
              onClick={() => onSelect?.(item.symbol)}>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className={`text-xs truncate ${active ? "text-ai" : "text-text"}`}>{displayName(item.symbol, item.name)}</span>
                  <span className="text-2xs text-muted-2">{item.exchange || (item.symbol.endsWith(".BO") ? "BSE" : "NSE")}</span>
                </div>
                <div className="flex items-center gap-1.5 text-2xs text-muted-2">
                  <span className="truncate">{item.symbol.replace(/\.(NS|BO)$/, "")}</span>
                  {item.status && item.status !== "DELAYED" && <span className={item.status === "UNAVAILABLE" ? "text-down" : "text-ai"}>{item.status}</span>}
                </div>
              </div>
              <div className="text-right">
                <div className="num text-xs">{item.price == null ? "—" : fmt(item.price)}</div>
                <div className={`num text-2xs ${pnlColor(item.change_pct)}`}>{item.change_pct == null ? "—" : signedPct(item.change_pct)}</div>
              </div>
              <div className="flex flex-col items-center opacity-40 group-hover:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                <button className="text-muted-2 hover:text-text" title="Move up" onClick={(e) => { e.stopPropagation(); move(idx, -1); }}><ArrowUp size={10} /></button>
                <button className="text-muted-2 hover:text-text" title="Move down" onClick={(e) => { e.stopPropagation(); move(idx, 1); }}><ArrowDown size={10} /></button>
              </div>
              <button className="opacity-60 group-hover:opacity-100 sm:opacity-0 sm:group-hover:opacity-100 text-muted-2 hover:text-down p-0.5 transition-opacity" title="Remove"
                onClick={(e) => { e.stopPropagation(); onRemove?.(item.symbol); }}><X size={12} /></button>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
