import React, { useEffect, useState } from "react";
import { api, fmt, pnlColor, ErrorBox, Badge } from "../api.jsx";

export default function Paper() {
  const [accts, setAccts] = useState([]);
  const [aid, setAid] = useState(null);
  const [account, setAccount] = useState(null);
  const [deployment, setDeployment] = useState(null);
  const [strats, setStrats] = useState([]);
  const [err, setErr] = useState(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // overview, trades, settings

  // New deployment form state
  const [newDep, setNewDep] = useState({
    strategy_id: "",
    initial_cash: 100000,
    transaction_cost_bps: 0,
    slippage_bps: 0,
  });

  const loadAccounts = async () => {
    const accounts = await api("/api/paper/accounts");
    setAccts(accounts);
  };

  const loadAccount = async (id) => {
    setAid(id);
    const data = await api(`/api/paper/accounts/${id}`);
    setAccount(data);
    // If account has active deployment, load deployment details
    if (data.deployment?.id) {
      const dep = await api(`/api/paper/deployments/${data.deployment.id}`);
      setDeployment(dep);
    } else {
      setDeployment(null);
    }
  };

  const loadStrategies = async () => {
    const strategies = await api("/api/strategies");
    setStrats(strategies);
  };

  useEffect(() => {
    loadAccounts().catch(() => {});
    loadStrategies().catch(() => {});
  }, []);

  const act = (fn) => async () => {
    setErr(null);
    setLoading(true);
    try {
      const r = await fn();
      if (r?.action) setNote(`Strategy signal: ${r.action}`);
      if (aid) await loadAccount(aid);
      else await loadAccounts();
    } catch (e) {
      setErr(e);
    } finally {
      setLoading(false);
    }
  };

  const P = (p, b) => api(p, { method: "POST", body: b });

  const createAccount = async () => {
    const n = await P("/api/paper/accounts", { name: "Paper account", starting_cash: 500000 });
    await loadAccount(n.id);
  };

  const createDeployment = async () => {
    const dep = await P(`/api/paper/accounts/${aid}/deployments`, newDep);
    setDeployment(dep);
    await loadAccount(aid);
  };

  const handleDeploy = (e) => {
    e.preventDefault();
    if (!newDep.strategy_id) {
      setErr({ detail: { validation: { passed: false, errors: ["Please select a strategy"] } } });
      return;
    }
    act(() => P(`/api/paper/accounts/${aid}/deployments`, newDep))();
  };

  const runStep = () => act(() => P(`/api/paper/deployments/${deployment.id}/step`));
  const pauseDeployment = () => act(() => P(`/api/paper/deployments/${deployment.id}/control/pause`));
  const resumeDeployment = () => act(() => P(`/api/paper/deployments/${deployment.id}/control/resume`));
  const stopDeployment = () => act(() => P(`/api/paper/deployments/${deployment.id}/control/stop`));
  const closeDeployment = () => {
    if (!window.confirm("Close deployment? This will liquidate all positions and cannot be undone.")) return;
    act(() => P(`/api/paper/deployments/${deployment.id}/control/close`))();
  };

  const placeOrder = () => act(() => P(`/api/paper/deployments/${deployment.id}/orders`, {
    symbol: newDep.symbol || "RELIANCE.NS",
    side: newDep.side || "BUY",
    qty: newDep.qty || 0.1,
  }));

  return (
    <div className="grid grid-cols-12 gap-3">
      {/* Sidebar - Accounts & Deployments */}
      <div className="card col-span-3 p-2">
        <button className="btn btn-ai w-full mb-2" onClick={createAccount}>
          New paper account (₹5,00,000 simulated)
        </button>
        {accts.map((x) => (
          <button
            key={x.id}
            onClick={() => loadAccount(x.id)}
            className={`w-full text-left px-2 py-1.5 text-sm rounded ${aid === x.id ? "bg-line" : ""}`}
          >
            #{x.id} <span className="badge text-ai border-ai/40">{x.status}</span>
            {x.deployment && <span className="ml-1 badge text-up">{x.deployment.status}</span>}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="col-span-9">
        {account ? (
          <>
            {/* Deployment Creation / Selection */}
            {!deployment && account.status === "RUNNING" && (
              <div className="card p-3 mb-3">
                <h3 className="font-medium mb-2">Create New Deployment</h3>
                <form onSubmit={handleDeploy} className="space-y-2">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Strategy</label>
                    <select
                      className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                      value={newDep.strategy_id}
                      onChange={(e) => setNewDep({ ...newDep, strategy_id: e.target.value })}
                    >
                      <option value="">Select validated strategy…</option>
                      {strats.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} v{s.version}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Initial Capital</label>
                      <input
                        type="number"
                        className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                        value={newDep.initial_cash}
                        onChange={(e) => setNewDep({ ...newDep, initial_cash: Number(e.target.value) })}
                        min="1000"
                        step="1000"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Tx Cost (bps)</label>
                      <input
                        type="number"
                        className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                        value={newDep.transaction_cost_bps}
                        onChange={(e) => setNewDep({ ...newDep, transaction_cost_bps: Number(e.target.value) })}
                        min="0"
                        max="10000"
                        step="1"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Slippage (bps)</label>
                      <input
                        type="number"
                        className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                        value={newDep.slippage_bps}
                        onChange={(e) => setNewDep({ ...newDep, slippage_bps: Number(e.target.value) })}
                        min="0"
                        max="10000"
                        step="1"
                      />
                    </div>
                  </div>
                  <ErrorBox err={err} />
                  <button className="btn btn-ai w-full" disabled={!newDep.strategy_id || loading} type="submit">
                    {loading ? "Creating..." : "Create Deployment"}
                  </button>
                </form>
              </div>
            )}

            {/* Active Deployment View */}
            {deployment && (
              <>
                {/* Deployment Header */}
                <div className="card p-3 mb-3">
                  <div className="flex flex-wrap gap-4 items-center mb-3">
                    <div>
                      <div className="text-xs text-slate-400">DEPLOYMENT #{deployment.deployment.id}</div>
                      <div className="font-medium">{deployment.deployment.strategy_spec?.name || "Unknown Strategy"}</div>
                      <div className="text-xs text-slate-400">v{deployment.deployment.strategy_version} · {deployment.deployment.strategy_spec?.timeframe}</div>
                    </div>
                    <div className="ml-auto flex items-center gap-2">
                      <Badge status={deployment.deployment.status} />
                      <span className="text-xs text-slate-400">PAPER TRADING ONLY</span>
                    </div>
                  </div>

                  {/* Config Summary */}
                  <div className="grid grid-cols-4 gap-2 text-sm mb-3">
                    <div className="card p-2"><div className="text-[10px] text-slate-500">Initial Capital</div><div className="font-medium">${fmt(deployment.deployment.initial_cash)}</div></div>
                    <div className="card p-2"><div className="text-[10px] text-slate-500">Tx Cost</div><div className="font-medium">{deployment.deployment.transaction_cost_bps} bps</div></div>
                    <div className="card p-2"><div className="text-[10px] text-slate-500">Slippage</div><div className="font-medium">{deployment.deployment.slippage_bps} bps</div></div>
                    <div className="card p-2"><div className="text-[10px] text-slate-500">Max Pos</div><div className="font-medium">{deployment.deployment.max_position_pct}%</div></div>
                  </div>

                  {/* Controls */}
                  <div className="flex gap-2 mb-3 flex-wrap">
                    <button className="btn" onClick={runStep} disabled={deployment.deployment.status !== "ACTIVE" || loading}>Run Step</button>
                    <button className="btn" onClick={pauseDeployment} disabled={deployment.deployment.status !== "ACTIVE" || loading}>Pause</button>
                    <button className="btn" onClick={resumeDeployment} disabled={deployment.deployment.status !== "PAUSED" || loading}>Resume</button>
                    <button className="btn" onClick={stopDeployment} disabled={deployment.deployment.status === "STOPPED" || deployment.deployment.status === "CLOSED" || loading}>Stop</button>
                    <button className="btn border-down text-down" onClick={closeDeployment} disabled={deployment.deployment.status === "CLOSED" || loading}>Close</button>
                  </div>
                  <ErrorBox err={err} />
                  {note && <div className="text-sm text-ai mb-2">{note}</div>}

                  {/* Tabs */}
                  <div className="border-t border-line pt-3">
                    <div className="flex gap-2 mb-2">
                      {["overview", "trades", "settings"].map((t) => (
                        <button
                          key={t}
                          onClick={() => setActiveTab(t)}
                          className={`px-3 py-1 text-sm rounded ${activeTab === t ? "bg-ai/10 text-ai" : "text-slate-400 hover:text-slate-200"}`}
                        >
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                      ))}
                    </div>

                    {/* Overview Tab */}
                    {activeTab === "overview" && (
                      <>
                        {/* Portfolio Summary */}
                        <div className="grid grid-cols-4 gap-2 mb-3">
                          {[
                            ["Cash", fmt(deployment.account.cash), null],
                            ["Equity", fmt(deployment.account.equity), null],
                            ["P&L", fmt(deployment.metrics.total_return), deployment.metrics.total_return],
                            ["Return %", fmt(deployment.metrics.total_return_pct) + "%", deployment.metrics.total_return_pct],
                          ].map(([l, v, s]) => (
                            <div key={l} className="card p-2">
                              <div className="text-[10px] text-slate-500">{l}</div>
                              <div className={`num text-lg ${s != null ? pnlColor(s) : ""}`}>{v}</div>
                            </div>
                          ))}
                        </div>

                        {/* Metrics Grid */}
                        <div className="grid grid-cols-4 gap-2 mb-3">
                          {[
                            ["Max DD", deployment.metrics.max_drawdown_pct + "%", -1],
                            ["Win Rate", deployment.metrics.win_rate_pct + "%", 1],
                            ["Profit Factor", deployment.metrics.profit_factor ?? "—", 1],
                            ["Total Trades", deployment.metrics.total_trades, 1],
                          ].map(([l, v, s]) => (
                            <div key={l} className="card p-2">
                              <div className="text-[10px] text-slate-500">{l}</div>
                              <div className={`num text-lg ${pnlColor(s)}`}>{v}</div>
                            </div>
                          ))}
                        </div>

                        {/* Positions */}
                        <div className="mb-3">
                          <h4 className="text-sm font-medium mb-2">Positions</h4>
                          {deployment.positions.length > 0 ? (
                            <table className="w-full text-sm num card">
                              <thead className="text-slate-500 text-left">
                                <tr>
                                  <th className="p-2">Symbol</th>
                                  <th className="p-2">Qty</th>
                                  <th className="p-2">Avg Entry</th>
                                  <th className="p-2">Current</th>
                                  <th className="p-2">Unrealized</th>
                                  <th className="p-2">Realized</th>
                                  <th className="p-2">Stop Loss</th>
                                  <th className="p-2">Take Profit</th>
                                </tr>
                              </thead>
                              <tbody>
                                {deployment.positions.map((p) => (
                                  <tr key={p.symbol} className="border-t border-line">
                                    <td className="p-2">{p.symbol}</td>
                                    <td className="p-2">{p.qty}</td>
                                    <td className="p-2">{fmt(p.avg_entry_price)}</td>
                                    <td className="p-2">{fmt(p.current_price)}</td>
                                    <td className="p-2"><span className={pnlColor(p.unrealized_pnl)}>{fmt(p.unrealized_pnl)}</span></td>
                                    <td className="p-2"><span className={pnlColor(p.realized_pnl)}>{fmt(p.realized_pnl)}</span></td>
                                    <td className="p-2">{p.stop_loss_price ? fmt(p.stop_loss_price) : "—"}</td>
                                    <td className="p-2">{p.take_profit_price ? fmt(p.take_profit_price) : "—"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          ) : (
                            <p className="text-slate-500 text-sm">No open positions</p>
                          )}
                        </div>
                      </>
                    )}

                    {/* Trades Tab */}
                    {activeTab === "trades" && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Trade History ({deployment.trades?.length || 0} trades)</h4>
                        {deployment.trades && deployment.trades.length > 0 ? (
                          <table className="w-full text-sm num card">
                            <thead className="text-slate-500 text-left">
                              <tr>
                                <th className="p-2">Time</th>
                                <th className="p-2">Symbol</th>
                                <th className="p-2">Side</th>
                                <th className="p-2">Qty</th>
                                <th className="p-2">Entry</th>
                                <th className="p-2">Exit</th>
                                <th className="p-2">P&L</th>
                                <th className="p-2">Return</th>
                                <th className="p-2">Reason</th>
                                <th className="p-2">Fees</th>
                                <th className="p-2">Slippage</th>
                              </tr>
                            </thead>
                            <tbody>
                              {deployment.trades.map((t, i) => (
                                <tr key={i} className="border-t border-line">
                                  <td className="p-2">{t.entry_ts?.slice(5, 16)}</td>
                                  <td className="p-2">{t.symbol}</td>
                                  <td className="p-2"><span className={t.side === "BUY" ? "text-up" : "text-down"}>{t.side}</span></td>
                                  <td className="p-2">{t.qty}</td>
                                  <td className="p-2">{fmt(t.entry_price)}</td>
                                  <td className="p-2">{fmt(t.exit_price)}</td>
                                  <td className="p-2"><span className={pnlColor(t.pnl)}>{fmt(t.pnl)}</span></td>
                                  <td className="p-2">{fmt(t.ret * 100)}%</td>
                                  <td className="p-2 text-xs text-slate-400">{t.reason}</td>
                                  <td className="p-2">{fmt(t.fees)}</td>
                                  <td className="p-2">{fmt(t.slippage)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p className="text-slate-500 text-sm">No trades yet</p>
                        )}
                      </div>
                    )}

                    {/* Settings Tab */}
                    {activeTab === "settings" && (
                      <div className="space-y-3">
                        <div className="card p-3">
                          <h4 className="text-sm font-medium mb-2">Execution Settings</h4>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Transaction Cost (bps)</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.transaction_cost_bps}
                                readOnly
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Slippage (bps)</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.slippage_bps}
                                readOnly
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Max Position %</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.max_position_pct}
                                readOnly
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Stop Loss %</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.stop_loss_pct ?? "—"}
                                readOnly
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Take Profit %</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.take_profit_pct ?? "—"}
                                readOnly
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-slate-400 mb-1">Max Drawdown %</label>
                              <input
                                type="number"
                                className="w-full bg-ink border border-line rounded px-2 py-1 text-sm"
                                value={deployment.deployment.max_drawdown_pct}
                                readOnly
                              />
                            </div>
                          </div>
                        </div>

                        <div className="card p-3">
                          <h4 className="text-sm font-medium mb-2">Strategy Specification (Snapshot)</h4>
                          <pre className="num text-[10px] text-slate-400 overflow-auto max-h-64">
                            {JSON.stringify(deployment.deployment.strategy_spec, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Manual Order (for active deployments) */}
                {deployment.deployment.status === "ACTIVE" && (
                  <div className="card p-3 mt-3">
                    <h4 className="text-sm font-medium mb-2">Manual Order</h4>
                    <div className="flex gap-2 mb-3 flex-wrap">
                      <input
                        className="bg-panel border border-line rounded px-2 w-28 text-sm"
                        value={newDep.symbol || "RELIANCE.NS"}
                        onChange={(e) => setNewDep({ ...newDep, symbol: e.target.value })}
                        placeholder="Symbol"
                      />
                      <select className="bg-panel border border-line rounded text-sm" value={newDep.side || "BUY"} onChange={(e) => setNewDep({ ...newDep, side: e.target.value })}>
                        <option value="BUY">BUY</option>
                        <option value="SELL">SELL</option>
                      </select>
                      <input
                        type="number"
                        step="0.000001"
                        className="bg-panel border border-line rounded px-2 w-24 num text-sm"
                        value={newDep.qty || 0.1}
                        onChange={(e) => setNewDep({ ...newDep, qty: Number(e.target.value) })}
                        placeholder="Qty"
                      />
                      <button className="btn" onClick={placeOrder} disabled={loading}>Place Order</button>
                    </div>
                    <ErrorBox err={err} />
                  </div>
                )}
              </>
            )}

            {/* Legacy Account View (no deployment) */}
            {!deployment && (
              <>
                <div className="grid grid-cols-4 gap-2 mb-3">
                  {[
                    ["Cash", fmt(account.cash)],
                    ["Equity", fmt(account.equity)],
                    ["P&L", fmt(account.pnl), account.pnl],
                    ["Status", account.status],
                  ].map(([l, v, s]) => (
                    <div key={l} className="card p-2">
                      <div className="text-[10px] text-slate-500">{l} · PAPER/SIMULATED</div>
                      <div className={`num text-lg ${s != null ? pnlColor(s) : ""}`}>{v}</div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 mb-3 flex-wrap">
                  <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/pause`))}>Pause</button>
                  <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/resume`))}>Resume</button>
                  <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/control/stop`))}>Stop</button>
                  <button className="btn border-down text-down" onClick={act(() => P(`/api/paper/accounts/${aid}/control/kill`))}>KILL SWITCH</button>
                </div>
                <ErrorBox err={err} />
                {note && <div className="text-sm text-ai mb-2">{note}</div>}

                <div className="flex gap-2 mb-3 text-sm">
                  <input className="bg-panel border border-line rounded px-2 w-28" value={newDep.symbol || "RELIANCE.NS"} onChange={(e) => setNewDep({ ...newDep, symbol: e.target.value })} placeholder="Symbol" />
                  <select className="bg-panel border border-line rounded" value={newDep.side || "BUY"} onChange={(e) => setNewDep({ ...newDep, side: e.target.value })}><option>BUY</option><option>SELL</option></select>
                  <input type="number" step="0.000001" className="bg-panel border border-line rounded px-2 w-24 num" value={newDep.qty || 0.1} onChange={(e) => setNewDep({ ...newDep, qty: Number(e.target.value) })} placeholder="Qty" />
                  <button className="btn" onClick={act(() => P(`/api/paper/accounts/${aid}/orders`, { symbol: newDep.symbol, side: newDep.side, qty: newDep.qty }))}>Place Simulated Order</button>
                </div>

                <table className="w-full text-sm num card">
                  <thead className="text-slate-500 text-left">
                    <tr><th className="p-2">Symbol</th><th className="p-2">Qty</th><th className="p-2">Avg</th><th className="p-2">Last</th><th className="p-2">Unrealized</th><th className="p-2">Realized</th></tr>
                  </thead>
                  <tbody>
                    {account.positions?.map((p) => (
                      <tr key={p.symbol} className="border-t border-line">
                        <td className="p-2">{p.symbol}</td>
                        <td className="p-2">{p.qty}</td>
                        <td className="p-2">{fmt(p.avg_price)}</td>
                        <td className="p-2">{fmt(p.last)}</td>
                        <td className="p-2"><span className={pnlColor(p.unrealized)}>{fmt(p.unrealized)}</span></td>
                        <td className="p-2"><span className={pnlColor(p.realized)}>{fmt(p.realized)}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="text-xs text-slate-500 mt-3 mb-1">FILLS</div>
                {account.orders?.map((x) => (
                  <div key={x.id} className="num text-xs">
                    <span className={x.side === "BUY" ? "text-up" : "text-down"}>{x.side}</span> {x.qty} {x.symbol} @ {fmt(x.fill_price)} · {x.reason} · {x.label}
                  </div>
                ))}
              </>
            )}
          </>
        ) : (
          <p className="text-slate-500 text-sm">Create or select a simulated account.</p>
        )}
      </div>
    </div>
  );
}