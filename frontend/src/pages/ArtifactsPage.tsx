import { useState } from "react";
import { artifactsApi } from "../api";
import { ApiError } from "../api";
import { DownloadLink } from "../components/DownloadLink";
import { useApi } from "../context";
import type { ArtifactRef } from "../types";

const PURPOSES = [
  "tifek",
  "uart_kernel",
  "jtag_kernel",
  "otp_kw",
  "hsm_image",
  "certificate",
  "image",
  "seccfg",
  "aes_key",
];

export default function ArtifactsPage() {
  const { artifacts, rememberArtifact, clearArtifacts } = useApi();
  const [file, setFile] = useState<File | null>(null);
  const [purpose, setPurpose] = useState("image");
  const [device, setDevice] = useState("f29h85x");
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<ArtifactRef | null>(null);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    try {
      const a = await artifactsApi.upload(file, purpose, device);
      rememberArtifact(a);
      setLast(a);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <div>
      <h1>Artifacts</h1>
      {error && <div className="error-box">{error}</div>}

      <section className="card">
        <h2>Upload file</h2>
        <form onSubmit={upload} className="form row">
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <label>
            Purpose{" "}
            <select value={purpose} onChange={(e) => setPurpose(e.target.value)}>
              {PURPOSES.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <label>
            Device{" "}
            <input value={device} onChange={(e) => setDevice(e.target.value)} />
          </label>
          <button>Upload</button>
        </form>
        {last && (
          <p className="muted">
            uploaded: <DownloadLink artifact={last} />
          </p>
        )}
      </section>

      <section className="card">
        <div className="row">
          <h2>Known artifacts (this browser session)</h2>
          <span className="spacer" />
          <button className="ghost" onClick={clearArtifacts}>
            Clear
          </button>
        </div>
        {artifacts.length === 0 && <p className="muted">Nothing yet.</p>}
        <table>
          <thead>
            <tr>
              <th>filename</th>
              <th>size</th>
              <th>download</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((a) => (
              <tr key={a.id}>
                <td>{a.filename ?? a.id}</td>
                <td>{a.size ?? "?"}</td>
                <td>
                  <DownloadLink artifact={a} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}