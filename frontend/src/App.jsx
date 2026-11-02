import React, { useState } from "react";
import { LineChart as Chart, MessageSquare, Workflow, FlaskConical, Wallet, BookOpen, PanelLeft, Microscope } from "lucide-react";
import Dashboard from "./pages/Dashboard.jsx"; import Studio from "./pages/Studio.jsx"; import Builder from "./pages/Builder.jsx";
import Backtest from "./pages/Backtest.jsx"; import Paper from "./pages/Paper.jsx"; import Journal from "./pages/Journal.jsx";
import Research from "./pages/Research.jsx";
const NAV = [["dash", "Market", Chart, Dashboard], ["studio", "AI Studio", MessageSquare, Studio], ["builder", "Builder", Workflow, Builder],
  ["bt", "Backtest", FlaskConical, Backtest], ["paper", "Paper trading", Wallet, Paper], ["journal", "Journal", BookOpen, Journal],
  ["research", "Research", Microscope, Research]];
export default function App() {
  const [tab, setTab] = useState("dash"); const [open, setOpen] = useState(true);
  const [draft, setDraft] = useState(null);       // shared canonical StrategySpec (chat ⇄ builder ⇄ backtest)
  const [saved, setSaved] = useState(null);       // last saved strategy {id, version, spec}
  const Page = NAV.find((n) => n[0] === tab)[3];
  return (
    <div className="watermark flex h-screen">
      <aside className={`${open ? "w-48" : "w-12"} border-r border-line bg-panel transition-all shrink-0`}>
        <button className="p-3 text-slate-400" onClick={() => setOpen(!open)}><PanelLeft size={16} /></button>
        {NAV.map(([k, label, Icon]) => (
          <button key={k} onClick={() => setTab(k)} className={`flex items-center gap-2 w-full px-3 py-2 text-sm ${tab === k ? "text-ai bg-ai/10" : "text-slate-400 hover:text-slate-200"}`}>
            <Icon size={16} />{open && label}</button>))}
      </aside>
      <main className="flex-1 overflow-auto p-4">
        <div className="flex justify-between items-center mb-3"><h1 className="text-lg font-semibold">QuantNiti</h1><span className="badge text-ai border-ai/50">PAPER/SIMULATED · NO REAL MONEY</span></div>
        <Page draft={draft} setDraft={setDraft} saved={saved} setSaved={setSaved} />
      </main>
    </div>);
}
