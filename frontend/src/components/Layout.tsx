import { useEffect, useState } from "react";
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
  const [state, setState] = useState<{ crypto: boolean; target: boolean }>({
    crypto: false,
    target: false,
  });
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const [crypto, target] = await Promise.allSettled([
        healthApi.crypto(),
        healthApi.target(),
      ]);
      if (cancelled) return;
      setState({
        crypto: crypto.status === "fulfilled",
        target: target.status === "fulfilled",
      });
    };
    poll();
    const timer = window.setInterval(poll, 3000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);
  return state;
}

export function Layout({ children }: { children: ReactNode }) {
  const { session, clearSession, apiKey, setApiKey } = useApi();
  const backends = useBackends();

  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">TI CyberShield Toolkit</span>
        <span className="spacer" />
        <span
          className={`health ${backends.crypto ? "ok" : "err"}`}
          title={`crypto service ${backends.crypto ? "up" : "DOWN"}`}
        >
          crypto {backends.crypto ? "up" : "down"}
        </span>
        <span
          className={`health ${backends.target ? "ok" : "err"}`}
          title={`target service ${backends.target ? "up" : "DOWN"}`}
        >
          target {backends.target ? "up" : "down"}
        </span>
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