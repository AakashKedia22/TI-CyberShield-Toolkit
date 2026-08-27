import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { jobsApi } from "../api";
import { ApiError } from "../api";
import { JobView } from "../components/JobView";
import type { Job } from "../types";

export default function JobDetailPage() {
  const { service, id } = useParams<{ service: "crypto" | "target"; id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!service || !id) return;
    let cancelled = false;
    const load = () =>
      jobsApi
        .get(service, id)
        .then((j) => {
          if (!cancelled) setJob(j);
        })
        .catch((e: unknown) => setError((e as ApiError).message));
    load();
    const timer = window.setInterval(load, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [service, id]);

  if (error) return <div className="error-box">{error}</div>;
  if (!job) return <p className="muted">Loading job…</p>;

  return (
    <div>
      <p>
        <Link to="/jobs">← jobs</Link>
      </p>
      <JobView
        job={job}
        onCancel={async () => {
          try {
            await jobsApi.cancel(job.service, job.id);
            setJob({ ...job, status: "cancelled" });
          } catch (e) {
            setError((e as ApiError).message);
          }
        }}
      />
    </div>
  );
}