const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
export async function api(path, opts = {}) {
  const res = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error("Request failed"), { detail: data.detail || data });
  return data;
}
export const fmt = (n, d = 2) => (n == null ? "—" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const pnlColor = (n) => (n >= 0 ? "text-up" : "text-down");
export function Badge({ status }) {
  const c = { "LIVE DATA": "text-up border-up/50", DELAYED: "text-amber-400 border-amber-400/50", SIMULATED: "text-ai border-ai/50", CACHED: "text-slate-400 border-slate-400/50", HISTORICAL: "text-slate-400 border-slate-400/50", UNAVAILABLE: "text-down border-down/50" }[status] || "text-slate-400 border-line";
  return <span className={`badge ${c}`}>{status}</span>;
}
export function ErrorBox({ err }) {
  if (!err) return null; const v = err.detail?.validation || err.detail;
  return <div className="border border-down/50 bg-down/10 text-down text-sm rounded p-2 my-2">{v?.errors ? v.errors.map((e, i) => <div key={i}>✕ {e}</div>) : "Something went wrong. Check the backend is running."}</div>;
}

// Watchlist API helpers
export const watchlistApi = {
  get: async () => {
    const data = await api("/api/watchlist");
    // Handle both array response and { items: [] } response
    return Array.isArray(data) ? data : (data.items || []);
  },
  add: (symbol) => api("/api/watchlist", { method: "POST", body: { symbol } }),
  remove: (symbol) => api(`/api/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  symbols: () => api("/api/watchlist/symbols"),
};
