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

/** Extract failing field paths from a FastAPI validation error payload. */
function validationLocations(detail?: ErrorResponse): string {
  const details = detail?.error?.details as Record<string, unknown> | null | undefined;
  const errors = details?.errors;
  if (!Array.isArray(errors)) return "";
  return errors
    .map((e) => {
      const err = e as { loc?: unknown; msg?: unknown; type?: unknown };
      const loc = Array.isArray(err.loc) ? err.loc.join(".") : "";
      const msg = typeof err.msg === "string" ? err.msg : "";
      return loc && msg ? `${loc} (${msg})` : loc || msg;
    })
    .filter(Boolean)
    .join("; ");
}

// Optional static API key (sent as X-API-Key). Only needed if the services
// were started with CST_CRYPTO_API_KEY / CST_TARGET_API_KEY set.
let apiKey: string | null = null;
export function setApiKeyHeader(key: string | null): void {
  apiKey = key || null;
}
export function hasApiKey(): boolean {
  return apiKey !== null;
}

/** Merge the API key (if any) into a set of request headers. Every request,
 * including uploads, downloads and log streams, must go through this. */
function authHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  if (apiKey) headers.set("X-API-Key", apiKey);
  return headers;
}

async function toApiError(res: Response): Promise<ApiError> {
  let detail: ErrorResponse | undefined;
  try {
    detail = (await res.json()) as ErrorResponse;
  } catch {
    /* not JSON */
  }
  const baseMsg = detail?.error?.message ?? `HTTP ${res.status}`;
  const fields = validationLocations(detail);
  const message = fields ? `${baseMsg} — field(s): ${fields}` : baseMsg;
  return new ApiError(res.status, message, detail);
}

async function request<T>(
  base: string,
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(base + path, { ...init, headers: authHeaders(init?.headers) });
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function json(method: string, body?: unknown, token?: string | null): RequestInit {
  // Both headers must be merged here; overwriting `headers` after spreading
  // this object silently drops the Content-Type and makes the server receive
  // the body as unparsed bytes.
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["X-Session-Token"] = token;
  return {
    method,
    headers,
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
    // No Content-Type here: the browser sets the multipart boundary itself.
    const res = await fetch(`${CRYPTO_BASE}/artifacts`, {
      method: "POST",
      body: form,
      headers: authHeaders(),
    });
    if (!res.ok) throw await toApiError(res);
    return (await res.json()) as ArtifactRef;
  },
  downloadUrl: (id: string) => `${CRYPTO_BASE}/artifacts/${id}`,
  /** Download through fetch so the API key header is sent, then save the blob. */
  download: async (id: string, filename: string): Promise<void> => {
    const res = await fetch(artifactsApi.downloadUrl(id), { headers: authHeaders() });
    if (!res.ok) throw await toApiError(res);
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};

// ---------------------------------------------------------------------------
// Certificates
// ---------------------------------------------------------------------------
export const certificatesApi = {
  generate: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<CertificateResult>(
      CRYPTO_BASE,
      `/devices/${device}/certificates`,
      json("POST", body, token)
    ),
  rot: (device: string, token?: string | null) =>
    request<{ rot_switching_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/rot`,
      json("POST", undefined, token)
    ),
  debug: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<{ debug_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/debug`,
      json("POST", body, token)
    ),
  recovery: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<{ recovery_cert: ArtifactRef }>(
      CRYPTO_BASE,
      `/devices/${device}/certificates/recovery`,
      json("POST", body, token)
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
      json("POST", body, token)
    ),
  signSeccfg: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<SignedSecCfgResult>(
      CRYPTO_BASE,
      `/devices/${device}/images/sign-seccfg`,
      json("POST", body, token)
    ),
  encrypt: (device: string, body: Record<string, unknown>, token?: string | null) =>
    request<EncryptResult>(
      CRYPTO_BASE,
      `/devices/${device}/images/encrypt`,
      json("POST", body, token)
    ),
  signBatch: (
    device: string,
    body: { binaries?: string[]; ccs_path?: string },
    token?: string | null
  ) =>
    request<Job>(
      CRYPTO_BASE,
      `/devices/${device}/images/sign-batch`,
      json("POST", body, token)
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
  /**
   * Follow a job's SSE stream. Uses fetch instead of EventSource because
   * EventSource cannot send the X-API-Key header. Resolves when the stream
   * ends; abort via the signal.
   */
  stream: async (
    service: "crypto" | "target",
    id: string,
    onEvent: (event: string, data: unknown) => void,
    signal: AbortSignal
  ): Promise<void> => {
    const res = await fetch(jobsApi.streamUrl(service, id), {
      headers: authHeaders({ Accept: "text/event-stream" }),
      signal,
    });
    if (!res.ok || !res.body) throw await toApiError(res);
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) return;
      buf += value;
      let sep: number;
      while ((sep = buf.indexOf("\n\n")) >= 0) {
        const block = buf.slice(0, sep);
        buf = buf.slice(sep + 2);
        let event = "message";
        const data: string[] = [];
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
        }
        if (!data.length) continue;
        try {
          onEvent(event, JSON.parse(data.join("\n")));
        } catch {
          /* ignore malformed event */
        }
      }
    }
  },
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