import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { ArtifactRef } from "./types";
import { setApiKeyHeader } from "./api";

interface ApiState {
  /** Session name the active token was issued for. */
  session: string | null;
  /** Short-lived token used for session-scoped crypto operations. */
  token: string | null;
  setSession: (name: string, token: string) => void;
  clearSession: () => void;
  /** Optional static API key (only needed if services enforce one). */
  apiKey: string | null;
  setApiKey: (key: string | null) => void;
  /** Artifacts produced/uploaded in this browser session (for download links). */
  artifacts: ArtifactRef[];
  rememberArtifact: (a: ArtifactRef) => void;
  clearArtifacts: () => void;
}

const ApiContext = createContext<ApiState | null>(null);

const API_KEY_STORAGE = "cst-api-key";

export function ApiProvider({ children }: { children: ReactNode }) {
  const [session, setSessionName] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [apiKey, setApiKeyState] = useState<string | null>(() =>
    localStorage.getItem(API_KEY_STORAGE)
  );
  const [artifacts, setArtifacts] = useState<ArtifactRef[]>([]);

  const value = useMemo<ApiState>(
    () => ({
      session,
      token,
      setSession: (name, tok) => {
        setSessionName(name);
        setToken(tok);
      },
      clearSession: () => {
        setSessionName(null);
        setToken(null);
      },
      apiKey,
      setApiKey: (key) => {
        setApiKeyState(key);
        setApiKeyHeader(key);
        if (key) localStorage.setItem(API_KEY_STORAGE, key);
        else localStorage.removeItem(API_KEY_STORAGE);
      },
      artifacts,
      rememberArtifact: (a) =>
        setArtifacts((prev) =>
          prev.some((p) => p.id === a.id) ? prev : [a, ...prev]
        ),
      clearArtifacts: () => setArtifacts([]),
    }),
    [session, token, apiKey, artifacts]
  );

  // Apply a persisted API key to the client on startup.
  if (apiKey) setApiKeyHeader(apiKey);

  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApi(): ApiState {
  const ctx = useContext(ApiContext);
  if (!ctx) throw new Error("useApi must be used within ApiProvider");
  return ctx;
}