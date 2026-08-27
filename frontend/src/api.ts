// Typed client for the crypto (Backend #1) and target (Backend #2) services.
// All requests go through the Vite dev proxy (same origin), so no CORS.

import type {
  ArtifactRef,
  CertificateResult,
  DeviceInfo,
  EncryptResult,
  ErrorResponse,
  Job,
  PortInfo,
  SessionSummary,
  SessionToken,
  SignedImageResult,
  SignedSecCfgResult,
} from "./types";

export const CRYPTO_BASE = "/api/crypto";
export const TARGET_BASE = "/api/target";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: ErrorResponse
  ) {
    super(message);
  }
}

// Optional static API key (sent as X-API-Key). Only needed if the services
// were started with CST_CRYPTO_API_KEY / CST_TARGET_API_KEY set.
let apiKey: string | null = null;
export function setApiKeyHeader(key: string | null): void {
  apiKey = key || null;
}

async function request<T>(
  base: string,
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (apiKey) headers.set("X-API-Key", apiKey);
  const res = await fetch(base + path, { ...init, headers });
  if (!res.ok) {
    let detail: ErrorResponse | undefined;
    try {
      detail = (await res.json()) as ErrorResponse;
    } catch {
      /* not JSON */
    }
    throw new ApiError(
      res.status,
      detail?.error?.message ?? `HTTP ${res.status}`,
      detail
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function json(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function tokenHeader(token?: string | null): Record<string, string> {
  return token ? { "X-Session-Token": token } : {};
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------
export const sessionsApi = {
  list: () => request<SessionSummary[]>(CRYPTO_BASE, "/sessions"),
  create: (body: Record<string, unknown>) =>
    request<SessionSummary>(CRYPTO_BASE, "/sessions", json("POST", body)),
  remove: (name: string) =>
    request<void>(CRYPTO_BASE, `/sessions/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
  open: (name: string, password: string) =>
    request<SessionToken>(
      CRYPTO_BASE,
      `/sessions/${encodeURIComponent(name)}/open`,
      json("POST", { password })
    ),
  development: (name: string, body: Record<string, unknown>) =>
    request<SessionSummary>(
      CRYPTO_BASE,
      `/sessions/${encodeURIComponent(name)}/development`,
      json("POST", body)
    ),
  publicKeys: (name: string, token?: string | null) =>
    request<Record<string, ArtifactRef>>(
      CRYPTO_BASE,
      `/sessions/${encodeURIComponent(name)}/public-keys`,
      { headers: tokenHeader(token) }
    ),
};

// ---------------------------------------------------------------------------
// Artifacts
// ---------------------------------------------------------------------------
export const artifactsApi = {
  upload: async (
    file: File,
    purpose?: string,
    device?: string
  ): Promise<ArtifactRef> => {
    const form = new FormData();
    form.append("file", file);
    if (purpose) form.append("purpose", purpose);
    if (device) form.append("device", device);
    const res = await fetch(`${CRYPTO_BASE}/artifacts`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let detail: ErrorResponse | undefined;
      try {
        detail = (await res.json()) as ErrorResponse;
      } catch {
        /* ignore */
      }
      throw new ApiError(
        res.status,
        detail?.error?.message ?? `HTTP ${res.status}`,
        detail
      );
    }
    return (await res.json()) as ArtifactRef;
  },
  downloadUrl: (id: string) => `${CRYPTO_BASE}/artifacts/${id}`,
};

// ---------------------------------------------------------------------------
// Certificates
// ---------------------------------------------------------------------------
export const certificatesApi = {
  generate: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<CertificateResult>(
      CRYPTO_BASE,
      `/devices/${device}/certificates`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
  rot: (device: string, token?: string | null) =>
    request<{ rot_switching_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/rot`,
      { method: "POST", headers: tokenHeader(token) }
    ),
  debug: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<{ debug_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/debug`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
  recovery: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<{ recovery_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/recovery`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
};

// ---------------------------------------------------------------------------
// Images
// ---------------------------------------------------------------------------
export const imagesApi = {
  sign: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<SignedImageResult>(
      CRYPTO_BASE,
      `/devices/${device}/images/sign`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
  signSeccfg: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<SignedSecCfgResult>(
      CRYPTO_BASE,
      `/devices/${device}/images/sign-seccfg`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
  encrypt: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<EncryptResult>(
      CRYPTO_BASE,
      `/devices/${device}/images/encrypt`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
  signBatch: (
    device: string,
    body: { binaries?: string[]; ccs_path?: string },
    token?: string | null
  ) =>
    request<Job>(
      CRYPTO_BASE,
      `/devices/${device}/images/sign-batch`,
      { ...json("POST", body), headers: tokenHeader(token) }
    ),
};

// ---------------------------------------------------------------------------
// Jobs (shared between services)
// ---------------------------------------------------------------------------
export const jobsApi = {
  base: (service: "crypto" | "target") =>
    service === "target" ? TARGET_BASE : CRYPTO_BASE,
  list: (service?: "crypto" | "target") => {
    const base = service ? jobsApi.base(service) : CRYPTO_BASE;
    return request<Job[]>(base, `/jobs${service ? `?service=${service}` : ""}`);
  },
  get: (service: "crypto" | "target", id: string) =>
    request<Job>(jobsApi.base(service), `/jobs/${id}`),
  logs: (service: "crypto" | "target", id: string) =>
    request<{ lines: Array<{ seq: number; timestamp: string; level: string; message: string }>; next_offset: number }>(
      jobsApi.base(service),
      `/jobs/${id}/logs`
    ),
  cancel: (service: "crypto" | "target", id: string) =>
    request<void>(jobsApi.base(service), `/jobs/${id}`, { method: "DELETE" }),
  streamUrl: (service: "crypto" | "target", id: string) =>
    `${jobsApi.base(service)}/jobs/${id}/stream`,
};

// ---------------------------------------------------------------------------
// Target discovery
// ---------------------------------------------------------------------------
export const targetApi = {
  ports: () => request<PortInfo[]>(TARGET_BASE, "/ports"),
  devices: () => request<DeviceInfo[]>(TARGET_BASE, "/devices"),
};

export const healthApi = {
  crypto: () => request<{ crypto: string }>(CRYPTO_BASE, "/health"),
  target: () => request<{ target: string }>(TARGET_BASE, "/health"),
};