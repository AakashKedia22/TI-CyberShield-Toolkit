import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { jobsApi } from "../api";
import { StatusPill } from "../components/StatusPill";
import type { Job } from "../types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setRefreshKey((k) => k + 1), 1500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([jobsApi.list("crypto"), jobsApi.list("target")])
      .then(([cryptoRes, targetRes]) => {
        if (cancelled) return;
        const cryptoJobs = cryptoRes.status === "fulfilled" ? cryptoRes.value : [];
        const targetJobs = targetRes.status === "fulfilled" ? targetRes.value : [];
        setJobs([...cryptoJobs, ...targetJobs]);
      })
      .catch((e: unknown) => setError((e as Error).message));
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <div>
      <h1>Jobs</h1>
      {error && <div className="error-box">{error}</div>}
      {jobs.length === 0 && <p className="muted">No jobs yet.</p>}
      <table>
        <thead>
          <tr>
            <th>status</th>
            <th>service</th>
            <th>type</th>
            <th>progress</th>
            <th>created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => (
            <tr key={`${j.service}:${j.id}`}>
              <td>
                <StatusPill status={j.status} />
              </td>
              <td>{j.service}</td>
              <td>{j.type}</td>
              <td>{j.progress}%</td>
              <td className="muted">{j.created_at ? new Date(j.created_at).toLocaleTimeString() : ""}</td>
              <td>
                <Link to={`/jobs/${j.service}/${j.id}`}>view</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}