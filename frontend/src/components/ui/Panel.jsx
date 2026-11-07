import React from "react";

export default function Panel({ title, icon, actions, children, className = "", bodyClass = "", dense = false, scroll = false }) {
  return (
    <section className={`card flex flex-col min-h-0 ${className}`}>
      {(title || actions) && (
        <header className="panel-head min-w-0">
          {icon && <span className="text-muted-2 shrink-0">{icon}</span>}
          <span className="truncate min-w-0">{title}</span>
          {actions && (
            <div className="ml-auto flex items-center gap-1 normal-case tracking-normal font-normal shrink-0 max-w-[78%] overflow-x-auto no-scrollbar">
              {actions}
            </div>
          )}
        </header>
      )}
      <div className={`${dense ? "p-0" : "panel-body"} flex-1 min-h-0 ${scroll ? "scroll-area" : ""} ${bodyClass}`}>
        {children}
      </div>
    </section>
  );
}

export function Stat({ label, value, hint, className = "", valueClass = "" }) {
  return (
    <div className={`min-w-0 ${className}`}>
      <div className="text-2xs uppercase tracking-wider text-muted-2">{label}</div>
      <div className={`num text-xs mt-0.5 truncate ${valueClass}`}>{value ?? "—"}</div>
      {hint && <div className="text-2xs text-muted-2 mt-0.5 truncate">{hint}</div>}
    </div>
  );
}

export function LoadingRows({ rows = 4 }) {
  return (
    <div className="space-y-2 p-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-6 w-full" style={{ opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function StatusDot({ status }) {
  const tone =
    status === "OPEN" || status === "LIVE"
      ? "text-up"
      : status === "PRE_OPEN" || status === "DELAYED"
      ? "text-amber"
      : "text-muted";
  return <span className={`inline-block h-1.5 w-1.5 rounded-full bg-current ${tone} ${status === "OPEN" ? "pulse-dot" : ""}`} />;
}
