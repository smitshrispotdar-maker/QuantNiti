// India-only fallback catalogue. The backend is authoritative; this list keeps
// the UI usable (and searchable) while /api/market/symbols is loading.
export const INDIAN_INDICES = [
  { symbol: "^NSEI", name: "NIFTY 50", exchange: "NSE", kind: "index", available: true },
  { symbol: "^NSEBANK", name: "BANK NIFTY", exchange: "NSE", kind: "index", available: true },
  { symbol: "NIFTY_FIN_SERVICE.NS", name: "FINNIFTY", exchange: "NSE", kind: "index", available: true },
  { symbol: "NIFTY_NEXT_50", name: "NIFTY NEXT 50", exchange: "NSE", kind: "index", available: false },
  { symbol: "^NSMIDCP", name: "NIFTY MIDCAP 100", exchange: "NSE", kind: "index", available: true },
  { symbol: "^INDIAVIX", name: "INDIA VIX", exchange: "NSE", kind: "index", available: true },
];

export const DEFAULT_WATCHLIST = [
  "^NSEI", "^NSEBANK", "NIFTY_FIN_SERVICE.NS", "RELIANCE.NS", "TCS.NS",
  "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "^INDIAVIX",
];

export const TIMEFRAMES = [
  { id: "1m", label: "1m" },
  { id: "5m", label: "5m" },
  { id: "15m", label: "15m" },
  { id: "30m", label: "30m" },
  { id: "1h", label: "1H" },
  { id: "4h", label: "4H" },
  { id: "1d", label: "1D" },
  { id: "1w", label: "1W" },
];

export const DEFAULT_SYMBOL = "^NSEI";

const NAME_OVERRIDES = {
  "^NSEI": "NIFTY 50",
  "^NSEBANK": "BANK NIFTY",
  "NIFTY_FIN_SERVICE.NS": "FINNIFTY",
  "NIFTY_NEXT_50": "NIFTY NEXT 50",
  "^NSMIDCP": "NIFTY MIDCAP 100",
  "^INDIAVIX": "INDIA VIX",
};

export function displayName(symbol, fallback) {
  if (NAME_OVERRIDES[symbol]) return NAME_OVERRIDES[symbol];
  if (fallback) return fallback;
  return String(symbol || "").replace(/\.(NS|BO)$/, "");
}

export function exchangeOf(symbol) {
  return String(symbol || "").endsWith(".BO") ? "BSE" : "NSE";
}

export function shortSymbol(symbol) {
  return String(symbol || "").replace(/\.(NS|BO)$/, "").replace(/^\^/, "");
}

export function isIndex(symbol) {
  return String(symbol || "").startsWith("^") || String(symbol || "").includes("NIFTY");
}

// Local guard for persisted selections. The backend remains authoritative;
// this only prevents a stale legacy (e.g. US/crypto) ticker from being
// restored into the India-only terminal from localStorage.
export function isIndianSymbol(symbol) {
  const s = String(symbol || "").toUpperCase();
  return s.startsWith("^") || s.startsWith("NIFTY_") || s.endsWith(".NS") || s.endsWith(".BO");
}
