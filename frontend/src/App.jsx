import React, { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LineChart as Chart, MessageSquare, Workflow, FlaskConical, Wallet, BookOpen, PanelLeft, Microscope, LogOut, User } from "lucide-react";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import { ProtectedRoute, PublicRoute } from "./components/ProtectedRoute.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Studio from "./pages/Studio.jsx";
import Builder from "./pages/Builder.jsx";
import Backtest from "./pages/Backtest.jsx";
import Paper from "./pages/Paper.jsx";
import Journal from "./pages/Journal.jsx";
import Research from "./pages/Research.jsx";
import { AuthPage } from "./pages/Auth.jsx";

const NAV = [
  ["dash", "Market", Chart, Dashboard],
  ["studio", "AI Studio", MessageSquare, Studio],
  ["builder", "Builder", Workflow, Builder],
  ["bt", "Backtest", FlaskConical, Backtest],
  ["paper", "Paper trading", Wallet, Paper],
  ["journal", "Journal", BookOpen, Journal],
  ["research", "Research", Microscope, Research],
];

function AppContent() {
  const { user, isAuthenticated, logout } = useAuth();
  const [tab, setTab] = useState("dash");
  const [open, setOpen] = useState(true);
  const [draft, setDraft] = useState(null);
  const [saved, setSaved] = useState(null);

  const Page = NAV.find((n) => n[0] === tab)?.[3] || Dashboard;

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="watermark flex h-screen">
      <aside className={`${open ? "w-48" : "w-12"} border-r border-line bg-panel transition-all shrink-0`}>
        <button className="p-3 text-slate-400" onClick={() => setOpen(!open)}>
          <PanelLeft size={16} />
        </button>
        {NAV.map(([k, label, Icon]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`flex items-center gap-2 w-full px-3 py-2 text-sm ${tab === k ? "text-ai bg-ai/10" : "text-slate-400 hover:text-slate-200"}`}
          >
            <Icon size={16} />{open && label}
          </button>
        ))}

        {/* User info & logout */}
        {isAuthenticated && open && (
          <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-line">
            <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-slate-300">
              <User size={14} className="text-slate-400" />
              <span className="truncate">{user?.email}</span>
            </div>
            <button
              onClick={handleLogout}
              className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-1.5 rounded border border-line bg-line/40 hover:bg-line text-sm text-slate-400 hover:text-down hover:border-down/50"
            >
              <LogOut size={14} /> Sign out
            </button>
          </div>
        )}
      </aside>
      <main className="flex-1 overflow-auto p-4">
        <div className="flex justify-between items-center mb-3">
          <h1 className="text-lg font-semibold">QuantNiti</h1>
          <span className="badge text-ai border-ai/50">PAPER/SIMULATED · NO REAL MONEY</span>
        </div>
        <Page draft={draft} setDraft={setDraft} saved={saved} setSaved={setSaved} />
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