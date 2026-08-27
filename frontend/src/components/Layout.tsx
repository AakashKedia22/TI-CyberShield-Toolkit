import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { healthApi } from "../api";
import { useApi } from "../context";

const NAV = [
  { to: "/", label: "Sessions", end: true },
  { to: "/certificates", label: "Certificates", end: false },
  { to: "/images", label: "Images", end: false },
  { to: "/artifacts", label: "Artifacts", end: false },
  { to: "/jobs", label: "Jobs", end: false },
];

function useBackends() {
  const [crypto, setCrypto] = useState<boolean>(false);
  const [checking, setChecking] = useState(true);
  const check = useCallback(async () => {
    setChecking(true);
    try {
      await healthApi.crypto();
      setCrypto(true);
    } catch {
      setCrypto(false);
    } finally {
      setChecking(false);
    }
  }, []);
  // Check once on mount, and only re-check when the user clicks the pill.
  // A repeated timer would otherwise spam the Vite proxy with ECONNREFUSED
  // log lines whenever a service is stopped.
  useEffect(() => {
    void check();
  }, [check]);
  return { crypto, checking, recheck: check };
}

export function Layout({ children }: { children: ReactNode }) {
  const { session, clearSession, apiKey, setApiKey } = useApi();
  const { crypto, checking, recheck } = useBackends();

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">TI CyberShield Toolkit</span>
        <span className="spacer" />
        <button
          className={`health ${crypto ? "ok" : "err"}`}
          onClick={() => void recheck()}
          title={`crypto service ${crypto ? "up" : "DOWN"} — click to re-check`}
        >
          {checking ? "checking…" : `crypto ${crypto ? "up" : "down"}`}
        </button>
        <input
          className="apikey"
          placeholder="API key (optional)"
          value={apiKey ?? ""}
          onChange={(e) => setApiKey(e.target.value || null)}
        />
        {session ? (
          <>
            <span className="active-session">session: {session}</span>
            <button className="ghost" onClick={clearSession}>
              Clear
            </button>
          </>
        ) : (
          <span className="muted">no session opened</span>
        )}
      </header>
      <div className="body">
        <nav className="sidebar">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}