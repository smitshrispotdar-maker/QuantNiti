import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownRight, ArrowUpRight, RefreshCw, Wallet } from "lucide-react";
import Panel from "../ui/Panel.jsx";
import { ErrorBox, fmt, signed, signedPct, pnlColor, paperApi } from "../../api.jsx";
import { displayName } from "../../market/instruments.js";

const NAME_KEY = "quantniti_paper_account";

const acctId = (a) => a?.id ?? a?.account?.id ?? null;
const acctName = (a) => a?.name || a?.account?.name || `Paper account ${acctId(a) || ""}`;

export default function PaperTicket({ symbol, price, onPaperData, onSelect }) {
  const [accounts, setAccounts] = useState([]);
  const [accountId, setAccountId] = useState(() => Number(localStorage.getItem(NAME_KEY)) || null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [side, setSide] = useState("BUY");
  const [qty, setQty] = useState("1");
  const [sl, setSl] = useState("");
  const [tp, setTp] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadAccounts = useCallback(async () => {
    setError(null);
    try {
      const data = await paperApi.accounts();
      const list = Array.isArray(data) ? data : [];
      setAccounts(list);
      const stillExists = list.some((a) => acctId(a) === accountId);
      if (!stillExists && list.length) {
        const next = acctId(list[0]);
        setAccountId(next);
        localStorage.setItem(NAME_KEY, String(next));
      }
      if (!list.length) setDetail(null);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  const loadDetail = useCallback(async (id) => {
    if (!id) return;
    setDetailLoading(true);
    try {
      const data = await paperApi.account(id);
      setDetail(data);
      onPaperData?.(data, id);
    } catch (e) {
      setError(e);
    } finally {
      setDetailLoading(false);
    }
  }, [onPaperData]);

  useEffect(() => {
    loadAccounts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (accountId) loadDetail(accountId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId]);

  const account = accounts.find((a) => acctId(a) === accountId) || detail;
  const accountInfo = detail?.account || account?.account || account || {};
  const positions = detail?.positions || account?.positions || [];
  const orders = detail?.orders || [];
  const symbolPosition = useMemo(
    () => positions.find((p) => p.symbol === symbol && Math.abs(p.qty) > 1e-9),
    [positions, symbol]
  );
  const symbolOrders = useMemo(
    () => orders.filter((o) => o.symbol === symbol).slice(0, 5),
    [orders, symbol]
  );

  // Surface chart context (markers + SL/TP lines) to the dashboard.
  useEffect(() => {
    if (detail) onPaperData?.(detail, accountId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail]);

  const refresh = async () => {
    await loadAccounts();
    if (accountId) await loadDetail(accountId);
  };

  const createAccount = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const created = await paperApi.create({ name: "Market terminal paper account", starting_cash: 500000 });
      localStorage.setItem(NAME_KEY, String(created.id));
      setAccountId(created.id);
      setNotice("Paper account created — simulated only.");
      await loadAccounts();
      await loadDetail(created.id);
    } catch (e) {
      setError(e);
    } finally {
      setSubmitting(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!accountId) return;
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const payload = {
        symbol,
        side,
        qty: Number(qty),
        stop_loss_price: sl === "" ? null : Number(sl),
        take_profit_price: tp === "" ? null : Number(tp),
      };
      if (!payload.qty || payload.qty <= 0) throw Object.assign(new Error("Quantity must be positive."), { detail: "Quantity must be positive." });
      if (payload.stop_loss_price != null && payload.take_profit_price != null && payload.stop_loss_price >= payload.take_profit_price) {
        throw Object.assign(new Error("Stop-loss must be below take-profit."), { detail: "Stop-loss must be below take-profit." });
      }
      const deploymentId = detail?.deployment?.id;
      const response = deploymentId
        ? await paperApi.deploymentOrder(deploymentId, payload)
        : await paperApi.order(accountId, payload);
      const fill = response?.order || response;
      const filled = fill?.side ? fill : { side, qty: payload.qty, symbol, fill_price: price };
      setNotice(`PAPER ${filled.side} ${filled.qty} ${displayName(filled.symbol)} submitted at ${fmt(filled.fill_price)} — simulated.`);
      setSl("");
      setTp("");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const metrics = detail?.metrics || account?.metrics;
  const equity = accountInfo.equity ?? account?.equity ?? metrics?.equity;
  const pnl = account?.pnl ?? detail?.pnl ?? metrics?.total_return;
  const startingCash = accountInfo.starting_cash ?? account?.starting_cash;
  const change = startingCash ? (pnl / startingCash) * 100 : null;

  return (
    <Panel
      className="h-full"
      title={<span className="flex items-center gap-1.5"><Wallet size={12} /> Paper trading</span>}
      dense
      bodyClass="flex flex-col min-h-0"
      actions={
        <span className="flex items-center gap-1 normal-case tracking-normal">
          <span className="badge badge-ai">SIMULATED</span>
          <button className="btn btn-xs btn-ghost" onClick={refresh} title="Refresh"><RefreshCw size={11} /></button>
        </span>
      }
    >
      <div className="flex-1 scroll-area min-h-0 p-2.5 space-y-2.5">
        {loading && <div className="space-y-1.5"><div className="skeleton h-6" /><div className="skeleton h-12" /></div>}
        {error && <ErrorBox err={error} onRetry={refresh} />}

        {!loading && accounts.length === 0 && (
          <div className="text-2xs text-muted leading-relaxed">
            No paper account yet. Create one to place simulated BUY/SELL orders. No real money is ever used.
            <button className="btn btn-xs btn-ai mt-2 w-full" disabled={submitting} onClick={createAccount}>
              Create paper account (₹5,00,000 simulated)
            </button>
          </div>
        )}

        {accounts.length > 0 && (
          <>
            <div className="flex items-center gap-1.5">
              <select
                className="select flex-1"
                value={accountId || ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setAccountId(id);
                  localStorage.setItem(NAME_KEY, String(id));
                }}
                aria-label="Paper account"
              >
                {accounts.map((a) => (
                  <option key={acctId(a)} value={acctId(a)}>{acctName(a)} #{acctId(a)}</option>
                ))}
              </select>
              {detailLoading && <span className="text-2xs text-muted-2">…</span>}
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <div className="text-2xs text-muted-2">Cash</div>
                <div className="num text-xs">{fmt(accountInfo.cash)}</div>
              </div>
              <div>
                <div className="text-2xs text-muted-2">Equity</div>
                <div className="num text-xs">{fmt(equity)}</div>
              </div>
              <div>
                <div className="text-2xs text-muted-2">P&L</div>
                <div className={`num text-xs ${pnlColor(pnl)}`}>
                  {signed(pnl)} <span className="text-2xs">({signedPct(change)})</span>
                </div>
              </div>
            </div>

            {metrics && (
              <div className="grid grid-cols-3 gap-2 border-t border-line-soft pt-2">
                <div><div className="text-2xs text-muted-2">Strategy return</div><div className={`num text-xs ${pnlColor(metrics.total_return_pct)}`}>{signedPct(metrics.total_return_pct)}</div></div>
                <div><div className="text-2xs text-muted-2">Win rate</div><div className="num text-xs">{(metrics.win_rate_pct ?? metrics.win_rate) == null ? "—" : `${fmt(metrics.win_rate_pct ?? metrics.win_rate, 1)}%`}</div></div>
                <div><div className="text-2xs text-muted-2">Max DD</div><div className="num text-xs text-down">{metrics.max_drawdown_pct == null ? "—" : `${fmt(metrics.max_drawdown_pct, 1)}%`}</div></div>
              </div>
            )}

            <form onSubmit={submit} className="border-t border-line-soft pt-2 space-y-2">
              <div className="flex items-center gap-1.5">
                <button type="button" onClick={() => setSide("BUY")} className={`btn btn-xs flex-1 ${side === "BUY" ? "btn-up" : "btn-ghost"}`}>
                  <ArrowUpRight size={11} /> BUY
                </button>
                <button type="button" onClick={() => setSide("SELL")} className={`btn btn-xs flex-1 ${side === "SELL" ? "btn-down" : "btn-ghost"}`}>
                  <ArrowDownRight size={11} /> SELL
                </button>
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <label className="block">
                  <span className="text-2xs text-muted-2">Qty</span>
                  <input className="input mt-0.5" type="number" min="0.0001" step="any" value={qty} onChange={(e) => setQty(e.target.value)} />
                </label>
                <label className="block">
                  <span className="text-2xs text-muted-2">Ref price</span>
                  <div className="input mt-0.5 num text-muted">{price == null ? "—" : fmt(price)}</div>
                </label>
                <label className="block">
                  <span className="text-2xs text-muted-2">Stop-loss</span>
                  <input className="input mt-0.5" type="number" min="0" step="any" placeholder="optional" value={sl} onChange={(e) => setSl(e.target.value)} />
                </label>
                <label className="block">
                  <span className="text-2xs text-muted-2">Take-profit</span>
                  <input className="input mt-0.5" type="number" min="0" step="any" placeholder="optional" value={tp} onChange={(e) => setTp(e.target.value)} />
                </label>
              </div>
              <button className={`btn w-full ${side === "BUY" ? "btn-up" : "btn-down"}`} disabled={submitting || !symbol}>
                {submitting ? "Placing…" : `PAPER ${side} · ${displayName(symbol)}`}
              </button>
              <div className="text-2xs text-muted-2 text-center">Fills at latest provider close · simulated, no real money</div>
            </form>

            {notice && <div className="text-2xs text-up bg-up/10 border border-up/30 rounded p-1.5">{notice}</div>}

            {positions.length > 0 && (
              <div className="border-t border-line-soft pt-2">
                <div className="text-2xs uppercase tracking-wider text-muted-2 mb-1">Open positions ({positions.length})</div>
                {positions.map((p) => {
                  const u = p.unrealized ?? p.unrealized_pnl;
                  return (
                    <button key={p.symbol} onClick={() => onSelect?.(p.symbol)}
                      className={`w-full flex items-center gap-1.5 text-2xs py-0.5 text-left hover:text-ai ${p.symbol === symbol ? "text-ai" : "text-muted"}`}>
                      <span className="flex-1 truncate">{displayName(p.symbol)}</span>
                      <span className="num">{fmt(p.qty, 4)}</span>
                      <span className={`num w-16 text-right ${pnlColor(u)}`}>{signed(u)}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {symbolPosition && (
              <div className="border-t border-line-soft pt-2">
                <div className="text-2xs uppercase tracking-wider text-muted-2 mb-1">Open position · {displayName(symbolPosition.symbol)}</div>
                <div className="grid grid-cols-3 gap-2 text-2xs">
                  <div><span className="text-muted-2">Qty</span><div className="num text-text">{fmt(symbolPosition.qty, 4)}</div></div>
                  <div><span className="text-muted-2">Avg</span><div className="num text-text">{fmt(symbolPosition.avg_price ?? symbolPosition.avg_entry_price)}</div></div>
                  <div><span className="text-muted-2">Unrealized</span><div className={`num ${pnlColor(symbolPosition.unrealized ?? symbolPosition.unrealized_pnl)}`}>{signed(symbolPosition.unrealized ?? symbolPosition.unrealized_pnl)}</div></div>
                </div>
                {(symbolPosition.stop_loss_price || symbolPosition.take_profit_price) && (
                  <div className="mt-1 text-2xs text-muted-2">
                    SL {symbolPosition.stop_loss_price ? fmt(symbolPosition.stop_loss_price) : "—"} · TP {symbolPosition.take_profit_price ? fmt(symbolPosition.take_profit_price) : "—"}
                  </div>
                )}
              </div>
            )}

            {symbolOrders.length > 0 && (
              <div className="border-t border-line-soft pt-2">
                <div className="text-2xs uppercase tracking-wider text-muted-2 mb-1">Recent paper orders</div>
                {symbolOrders.map((o) => (
                  <div key={o.id} className="flex items-center gap-1.5 text-2xs py-0.5">
                    <span className={o.side === "BUY" ? "text-up" : "text-down"}>{o.side}</span>
                    <span className="num text-muted">{fmt(o.qty, 4)}</span>
                    <span className="num text-text">{fmt(o.fill_price)}</span>
                    <span className="text-muted-2 ml-auto">{new Date(o.ts).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit" })}</span>
                  </div>
                ))}
              </div>
            )}

            {!detail?.orders && detailLoading && <div className="text-2xs text-muted-2">Loading orders…</div>}
          </>
        )}
      </div>
    </Panel>
  );
}
