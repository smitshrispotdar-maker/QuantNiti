import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import {
  BookOpen, FlaskConical, LayoutDashboard, LogOut, MessageSquare, Microscope,
  PanelLeft, PieChart, User, Wallet, Workflow,
} from "lucide-react";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProtectedRoute, PublicRoute } from "./components/ProtectedRoute.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Studio from "./pages/Studio.jsx";
import Builder from "./pages/Builder.jsx";
import Backtest from "./pages/Backtest.jsx";
import Paper from "./pages/Paper.jsx";
import Portfolio from "./pages/Portfolio.jsx";
import Journal from "./pages/Journal.jsx";
import Research from "./pages/Research.jsx";
import { AuthPage } from "./pages/Auth.jsx";

const NAV = [
  { id: "dash", label: "Market", icon: LayoutDashboard, page: Dashboard },
  { id: "studio", label: "AI Studio", icon: MessageSquare, page: Studio },
  { id: "builder", label: "Strategy Builder", icon: Workflow, page: Builder },
  { id: "bt", label: "Backtesting", icon: FlaskConical, page: Backtest },
  { id: "paper", label: "Paper Trading", icon: Wallet, page: Paper },
  { id: "portfolio", label: "Portfolio", icon: PieChart, page: Portfolio },
  { id: "journal", label: "Trade Journal", icon: BookOpen, page: Journal },
  { id: "research", label: "Research", icon: Microscope, page: Research },
];

function IndiaClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <span className="num text-2xs text-muted-2">
      {now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false })} IST
    </span>
  );
}

function BrandMark({ open }) {
  return (
    <div className="flex items-center gap-2 px-3 h-12 border-b border-line shrink-0">
      <div className="h-7 w-7 rounded-md bg-gradient-to-br from-ai/30 to-up/20 border border-ai/40 flex items-center justify-center text-ai text-xs font-bold">
        QN
      </div>
      {open && (
        <div className="min-w-0">
          <div className="text-xs font-semibold tracking-wide text-text leading-tight">QuantNiti</div>
          <div className="text-2xs text-muted-2 leading-tight">India market terminal</div>
        </div>
      )}
    </div>
  );
}

function AppContent() {
  const { user, isAuthenticated, logout } = useAuth();
  const [tab, setTab] = useState("dash");
  const [open, setOpen] = useState(true);
  const [draft, setDraft] = useState(null);
  const [saved, setSaved] = useState(null);

  const active = NAV.find((n) => n.id === tab) || NAV[0];
  const Page = active.page;

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="watermark flex h-screen bg-ink">
      <aside className={`${open ? "w-48" : "w-14"} relative flex flex-col border-r border-line bg-panel transition-[width] duration-150 shrink-0`}>
        <BrandMark open={open} />
        <button
          className="absolute -right-2.5 top-3 z-20 h-5 w-5 rounded-full border border-line bg-surface text-muted hover:text-ai flex items-center justify-center"
          onClick={() => setOpen(!open)}
          aria-label="Toggle sidebar"
        >
          <PanelLeft size={11} />
        </button>

        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              title={label}
              className={`relative flex items-center gap-2.5 w-full px-3 py-2 text-xs transition-colors ${
                tab === id
                  ? "text-ai bg-ai/10 before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-0.5 before:bg-ai before:rounded-r"
                  : "text-muted hover:text-text hover:bg-surface/60"
              }`}
            >
              <Icon size={15} className="shrink-0" />
              {open && <span className="truncate">{label}</span>}
            </button>
          ))}
        </nav>

        {isAuthenticated && (
          <div className="border-t border-line p-2 shrink-0">
            {open ? (
              <>
                <div className="flex items-center gap-2 px-1.5 py-1 text-2xs text-muted">
                  <User size={12} className="text-muted-2 shrink-0" />
                  <span className="truncate">{user?.email || "Signed in"}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full mt-1.5 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded border border-line bg-surface hover:bg-raised text-2xs text-muted hover:text-down"
                >
                  <LogOut size={12} /> Sign out
                </button>
              </>
            ) : (
              <button onClick={handleLogout} className="w-full flex justify-center p-2 text-muted hover:text-down" title="Sign out">
                <LogOut size={14} />
              </button>
            )}
          </div>
        )}
      </aside>

      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <header className="h-10 shrink-0 flex items-center gap-3 px-3 border-b border-line bg-panel/80">
          <span className="text-2xs uppercase tracking-[0.14em] text-muted-2">{active.label}</span>
          <span className="badge badge-ai">NSE · BSE</span>
          <span className="badge text-muted-2">PAPER / SIMULATED</span>
          <span className="text-2xs text-muted-2 hidden md:inline">India-only instruments</span>
          <div className="ml-auto flex items-center gap-3">
            <span className="badge badge-amber">DELAYED / SIMULATED</span>
            <IndiaClock />
          </div>
        </header>

        <div className={`flex-1 min-h-0 ${tab === "dash" ? "overflow-hidden" : "overflow-auto p-4"}`}>
          <Page draft={draft} setDraft={setDraft} saved={saved} setSaved={setSaved} />
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <AuthPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <AuthPage />
              </PublicRoute>
            }
          />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <AppContent />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
