import React, { useCallback, useEffect, useState } from "react";
import ReactFlow, { Background, Controls, addEdge, useNodesState, useEdgesState } from "reactflow";
import "reactflow/dist/style.css";
const KINDS = { data: "Market Data", indicator: "Indicator", condition: "Condition", entry: "Entry", exit: "Exit", risk: "Risk" };
const mk = (kind, n) => ({ id: `${kind}_${n}`, position: { x: 40 + (n % 4) * 200, y: 40 + Math.floor(n / 4) * 110 }, data: { kind, label: `${KINDS[kind]}`, p: kind === "data" ? { symbol: "BTC-USD", timeframe: "1d" } : kind === "indicator" ? { type: "EMA", period: 20 } : kind === "condition" ? { left: "ema_20", op: "crosses_above", right: "ema_50" } : kind === "risk" ? { stop_loss_pct: 5, max_position_pct: 25 } : {} },
  style: { background: "#121620", color: "#e2e8f0", border: `1px solid ${{ entry: "#00C853", exit: "#FF5252", indicator: "#00E5FF" }[kind] || "#1E222D"}`, fontSize: 12, width: 150 } });
// Serialise the graph → canonical StrategySpec. Entry/Exit nodes pull rules from Condition nodes wired into them.
export function toSpec(nodes, edges, name) {
  const by = (k) => nodes.filter((n) => n.data.kind === k), feeding = (id) => edges.filter((e) => e.target === id).map((e) => nodes.find((n) => n.id === e.source)).filter((n) => n?.data.kind === "condition");
  const data = by("data")[0]?.data.p || {}, risk = by("risk")[0]?.data.p || {};
  const rules = (k) => by(k).flatMap((n) => feeding(n.id)).map((c) => ({ left: c.data.p.left, op: c.data.p.op, right: isNaN(c.data.p.right) || c.data.p.right === "" ? c.data.p.right : Number(c.data.p.right) }));
  return { schema_version: "1.0", name, instruments: data.symbol ? [data.symbol] : [], timeframe: data.timeframe || "1d",
    indicators: by("indicator").map((n) => ({ id: `${n.data.p.type.toLowerCase()}_${n.data.p.period}`, type: n.data.p.type, params: { period: Number(n.data.p.period) } })),
    entry_rules: rules("entry"), exit_rules: rules("exit"), risk: { max_position_pct: Number(risk.max_position_pct ?? 25), stop_loss_pct: Number(risk.stop_loss_pct ?? 5), take_profit_pct: null, max_drawdown_pct: 25 } };
}
// Reverse binding: canonical spec → nodes/edges (so chat drafts show up on the canvas).
export function fromSpec(spec) {
  const nodes = [], edges = []; let n = 0; const add = (k, p) => { const nd = mk(k, n++); if (p) nd.data.p = p; nodes.push(nd); return nd.id; };
  add("data", { symbol: spec.instruments[0] || "BTC-USD", timeframe: spec.timeframe });
  spec.indicators.forEach((i) => add("indicator", { type: i.type, period: i.params.period ?? 14 }));
  add("risk", { stop_loss_pct: spec.risk.stop_loss_pct ?? 5, max_position_pct: spec.risk.max_position_pct });
  [["entry", spec.entry_rules], ["exit", spec.exit_rules]].forEach(([k, rs]) => { const t = add(k); rs.forEach((r) => { const c = add("condition", { left: r.left, op: r.op, right: String(r.right) }); edges.push({ id: `${c}-${t}`, source: c, target: t }); }); });
  return { nodes, edges };
}
export default function Builder({ draft, setDraft, setSaved }) {
  const [nodes, setNodes, onNodes] = useNodesState([]); const [edges, setEdges, onEdges] = useEdgesState([]); const [sel, setSel] = useState(null); const [name, setName] = useState("Canvas strategy");
  useEffect(() => { if (draft) { const g = fromSpec(draft); setNodes(g.nodes); setEdges(g.edges); setName(draft.name); } }, []); // load chat draft once
  const onConnect = useCallback((c) => setEdges((e) => addEdge(c, e)), []);
  const node = nodes.find((n) => n.id === sel);
  const setP = (k, v) => setNodes((ns) => ns.map((n) => (n.id === sel ? { ...n, data: { ...n.data, p: { ...n.data.p, [k]: v } } } : n)));
  const sync = () => setDraft(toSpec(nodes, edges, name));
  return (
    <div className="grid grid-cols-12 gap-3 h-[80vh]">
      <div className="col-span-9 card"><div className="flex gap-1 p-2 border-b border-line flex-wrap">{Object.keys(KINDS).map((k) => <button key={k} className="btn" onClick={() => setNodes((ns) => [...ns, mk(k, ns.length)])}>+ {KINDS[k]}</button>)}
        <button className="btn btn-ai ml-auto" onClick={sync}>Sync to strategy</button></div>
        <div style={{ height: "calc(100% - 44px)" }}><ReactFlow nodes={nodes.map((n) => ({ ...n, data: { ...n.data, label: `${n.data.label}${n.data.p?.type ? ` · ${n.data.p.type} ${n.data.p.period}` : ""}` } }))} edges={edges} onNodesChange={onNodes} onEdgesChange={onEdges} onConnect={onConnect} onNodeClick={(_, n) => setSel(n.id)} colorMode="dark" fitView><Background color="#1E222D" /><Controls /></ReactFlow></div></div>
      <div className="col-span-3 card p-3 overflow-auto text-sm"><input className="w-full bg-ink border border-line rounded px-2 py-1 mb-3" value={name} onChange={(e) => setName(e.target.value)} />
        {node ? Object.entries(node.data.p).map(([k, v]) => <label key={k} className="block mb-2 text-xs text-slate-400">{k}<input className="w-full bg-ink border border-line rounded px-2 py-1 text-slate-200 num" value={v} onChange={(e) => setP(k, e.target.value)} /></label>) : <p className="text-slate-500">Select a node to edit it. Wire Condition nodes into Entry/Exit nodes.</p>}
        <pre className="num text-[10px] text-slate-500 mt-3">{JSON.stringify(toSpec(nodes, edges, name), null, 1)}</pre></div>
    </div>);
}
