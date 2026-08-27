// Models mirror the service OpenAPI contract (docs/api/openapi.yaml).

export interface ArtifactRef {
  id: string;
  filename?: string | null;
  content_type?: string | null;
  size?: number | null;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

export interface SessionSummary {
  name: string;
  description?: string | null;
  hsm?: boolean | null;
  smpk_algorithm?: string | null;
  bmpk_algorithm?: string | null;
  created_at?: string | null;
}

export interface SessionToken {
  token: string;
  expires_at: string;
}

export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface Job {
  id: string;
  service: "crypto" | "target";
  type: string;
  status: JobStatus;
  progress: number;
  exit_code?: number | null;
  result?: Record<string, unknown> | null;
  error?: ErrorResponse | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  logs_url?: string | null;
  stream_url?: string | null;
}

export interface LogLine {
  seq: number;
  timestamp: string;
  level: string;
  message: string;
}

export interface CertificateBundle {
  primary_cert?: ArtifactRef | null;
  secondary_cert?: ArtifactRef | null;
  final_cert?: ArtifactRef | null;
}

export interface CertificateResult {
  certificates: CertificateBundle[];
  keycert_headers: ArtifactRef[];
}

export interface SignedImageResult {
  signed_image: ArtifactRef;
}

export interface SignedSecCfgResult {
  seccfg_bin: ArtifactRef;
}

export interface EncryptResult {
  encrypted_image: ArtifactRef;
}

export interface SignBatchResult {
  total: number;
  succeeded: number;
  failed: number;
  results: Array<Record<string, unknown>>;
}

export interface PortInfo {
  name: string;
  description: string;
  hwid?: string | null;
}

export interface DeviceInfo {
  name: string;
  family: string;
  boot_modes: string[];
  addon_version?: string | null;
}