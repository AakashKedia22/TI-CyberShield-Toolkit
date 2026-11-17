import { useEffect, useRef, useState } from "react";
import { jobsApi } from "../api";
import type { Job, JobStatus, LogLine } from "../types";
import { StatusPill } from "./StatusPill";

interface Props {
  job: Job;
  onCancel?: () => void;
}

/** Live job view: status, progress, and a streamable log (SSE). */
export function JobView({ job, onCancel }: Props) {
  // Status/progress come from the parent's polled job, overridden by the
  // live stream while it is running. Keep the local copy in sync with props,
  // otherwise a job that finishes between polls stays "running" forever.
  const [status, setStatus] = useState<JobStatus>(job.status);
  const [progress, setProgress] = useState<number>(job.progress);
  useEffect(() => setStatus(job.status), [job.status]);
  useEffect(() => setProgress(job.progress), [job.progress]);

  const [lines, setLines] = useState<LogLine[]>([]);
  const [live, setLive] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);
  const terminal = ["succeeded", "failed", "cancelled"].includes(status);

  const mergeLine = (line: LogLine) =>
    setLines((prev) => {
      if (prev.some((l) => l.seq === line.seq)) return prev;
      return [...prev, line].sort((a, b) => a.seq - b.seq);
    });

  // Fetch the stored log; re-fetch whenever the polled status changes so the
  // log is complete once the job finishes, even without streaming.
  useEffect(() => {
    let cancelled = false;
    jobsApi
      .logs(job.service, job.id)
      .then(({ lines: ls }) => {
        if (!cancelled) setLines(ls);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [job.service, job.id, job.status, job.progress]);

  // Live stream (fetch-based so the API key header is sent).
  useEffect(() => {
    if (!live) return;
    const ctrl = new AbortController();
    jobsApi
      .stream(
        job.service,
        job.id,
        (event, data) => {
          if (event === "status") {
            const d = data as { status: JobStatus; progress?: number };
            setStatus(d.status);
            if (typeof d.progress === "number") setProgress(d.progress);
          } else if (event === "log") {
            mergeLine(data as LogLine);
          }
        },
        ctrl.signal
      )
      .catch(() => undefined)
      .finally(() => {
        if (!ctrl.signal.aborted) setLive(false);
      });
    return () => ctrl.abort();
  }, [live, job.service, job.id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines, live]);

  return (
    <div className="jobview">
      <div className="row">
        <StatusPill status={status} />
        <span className="muted">
          {job.service} / {job.type} / {job.id}
        </span>
        <span className="spacer" />
        {!terminal && (
          <button
            className="ghost"
            onClick={() => {
              if (onCancel) onCancel();
            }}
          >
            Cancel
          </button>
        )}
        <button className="ghost" onClick={() => setLive((v) => !v)}>
          {live ? "Stop stream" : "Stream live"}
        </button>
      </div>
      <div className="progress">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <pre ref={logRef} className="log">
        {lines.map((l) => `${l.message}`).join("\n") || "(no log output yet)"}
      </pre>
      {status === "failed" && job.error && (
        <div className="error-box">{job.error.error.message}</div>
      )}
    </div>
  );
}