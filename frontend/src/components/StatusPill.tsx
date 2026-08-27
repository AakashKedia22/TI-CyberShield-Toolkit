import type { JobStatus } from "../types";

const CLASS: Record<JobStatus, string> = {
  queued: "pill queued",
  running: "pill running",
  succeeded: "pill ok",
  failed: "pill err",
  cancelled: "pill cancel",
};

export function StatusPill({ status }: { status: JobStatus }) {
  return <span className={CLASS[status] ?? "pill"}>{status}</span>;
}