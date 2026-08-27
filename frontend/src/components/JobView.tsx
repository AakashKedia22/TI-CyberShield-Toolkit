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
  const [status, setStatus] = useState<JobStatus>(job.status);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [live, setLive] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);

  // Poll the stored log tail on mount (covers already-emitted lines).
  useEffect(() => {
    let cancelled = false;
    jobsApi
      .logs(job.service, job.id)
      .then(({ lines: ls }) => {
        if (cancelled) return;
        setLines(ls);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [job.service, job.id]);

  // Live SSE stream.
  useEffect(() => {
    if (!live) return;
    const es = new EventSource(jobsApi.streamUrl(job.service, job.id));
    es.addEventListener("status", (e) => {
      try {
        const d = JSON.parse((e as MessageEvent).data);
        setStatus(d.status as JobStatus);
      } catch {
        /* ignore */
      }
    });
    es.addEventListener("log", (e) => {
      try {
        const line = JSON.parse((e as MessageEvent).data) as LogLine;
        setLines((prev) => {
          const next = prev.filter((l) => l.seq !== line.seq);
          next.push(line);
          return next.sort((a, b) => a.seq - b.seq);
        });
      } catch {
        /* ignore */
      }
    });
    const close = () => es.close();
    es.addEventListener("error", close);
    es.addEventListener("result", close);
    return close;
  }, [live, job.service, job.id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [lines, live]);

  const terminal = ["succeeded", "failed", "cancelled"].includes(status);

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
        <div className="progress-fill" style={{ width: `${job.progress}%` }} />
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