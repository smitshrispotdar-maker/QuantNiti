export const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "quantniti_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export async function api(path, opts = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...opts.headers };
  if (token && !path.startsWith("/api/auth/login") && !path.startsWith("/api/auth/register")) {
    headers.Authorization = `Bearer ${token}`;
  }
  let res;
  try {
    res = await fetch(BASE + path, {
      ...opts,
      headers,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
  } catch (e) {
    throw Object.assign(new Error("Backend unreachable"), {
      detail: "Backend unreachable. Check the API server is running.",
      status: 0,
    });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw Object.assign(new Error(data.detail?.message || "Request failed"), {
      detail: data.detail || data,
      status: res.status,
    });
  }
  return data;
}

export const fmt = (n, d = 2) =>
  n == null ? "—" : Number(n).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });

export const fmtCompact = (n) => {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  if (Math.abs(v) >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
  if (Math.abs(v) >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return fmt(v, 0);
};

export const pnlColor = (n) => (Number(n) >= 0 ? "text-up" : "text-down");

export const signed = (n, d = 2) => (n == null ? "—" : `${Number(n) > 0 ? "+" : ""}${fmt(n, d)}`);

export const signedPct = (n, d = 2) => (n == null ? "—" : `${Number(n) > 0 ? "+" : ""}${fmt(n, d)}%`);

export function fmtDateTime(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short",
    });
  } catch {
    return String(ts);
  }
}

export function fmtTime(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    });
  } catch {
    return "—";
  }
}

export const STATUS_TONE = {
  LIVE: "badge-up",
  DELAYED: "badge-amber",
  SIMULATED: "badge-ai",
  CACHED: "badge",
  STALE: "badge-amber",
  HISTORICAL: "badge",
  UNAVAILABLE: "badge-down",
  OPEN: "badge-up",
  PRE_OPEN: "badge-amber",
  CLOSED: "badge",
};

export function Badge({ status }) {
  return <span className={`badge ${STATUS_TONE[status] || ""}`}>{status || "UNKNOWN"}</span>;
}

export function ErrorBox({ err, onRetry }) {
  if (!err) return null;
  const v = err.detail?.validation || err.detail;
  const message =
    typeof v === "string"
      ? v
      : v?.message
      ? v.message
      : v?.errors
      ? v.errors.join(" · ")
      : err.message || "Something went wrong. Check the backend is running.";
  return (
    <div className="border border-down/40 bg-down/10 text-down text-xs rounded-md p-2 my-2 flex items-start gap-2">
      <span className="mt-0.5">✕</span>
      <span className="flex-1">{message}</span>
      {onRetry && <button className="btn btn-xs btn-down" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function EmptyState({ title, hint, icon }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-8 px-4 text-muted">
      {icon && <div className="mb-2 opacity-60">{icon}</div>}
      <div className="text-xs font-medium text-text/80">{title}</div>
      {hint && <div className="text-2xs mt-1 max-w-[240px] leading-relaxed">{hint}</div>}
    </div>
  );
}

export const watchlistApi = {
  get: async () => {
    const data = await api("/api/watchlist");
    return Array.isArray(data) ? data : (data.items || []);
  },
  add: (symbol) => api("/api/watchlist", { method: "POST", body: { symbol } }),
  remove: (symbol) => api(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  reorder: (symbols) => api("/api/watchlist/reorder", { method: "PUT", body: { symbols } }),
  symbols: () => api("/api/watchlist/symbols"),
};

export const marketApi = {
  overview: (symbol) => api(`/api/market/overview/${encodeURIComponent(symbol)}`),
  bars: (symbol, timeframe, limit = 300) =>
    api(`/api/market/bars/${encodeURIComponent(symbol)}?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),
  research: (symbol, timeframe = "1d") =>
    api(`/api/market/research/${encodeURIComponent(symbol)}?timeframe=${timeframe}`),
  indices: () => api("/api/market/indices"),
  movers: (limit = 5) => api(`/api/market/movers?limit=${limit}`),
  tape: (symbol) => api(`/api/market/tape/${encodeURIComponent(symbol)}`),
  capabilities: () => api("/api/market/capabilities"),
  status: () => api("/api/market/status"),
  search: (q) => api(`/api/market/search?q=${encodeURIComponent(q)}`),
  symbols: () => api("/api/market/symbols"),
};

export const paperApi = {
  accounts: () => api("/api/paper/accounts"),
  account: (id) => api(`/api/paper/accounts/${id}`),
  create: (body) => api("/api/paper/accounts", { method: "POST", body }),
  order: (accountId, body) => api(`/api/paper/accounts/${accountId}/orders`, { method: "POST", body }),
  deploymentOrder: (deploymentId, body) =>
    api(`/api/paper/deployments/${deploymentId}/orders`, { method: "POST", body }),
  control: (accountId, action) => api(`/api/paper/accounts/${accountId}/control/${action}`, { method: "POST" }),
};

export function wsUrl(path) {
  const base = BASE.replace(/^http/, "ws");
  return `${base}${path}`;
}
