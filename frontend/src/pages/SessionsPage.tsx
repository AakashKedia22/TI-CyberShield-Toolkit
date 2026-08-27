import { useCallback, useEffect, useState } from "react";
import { sessionsApi } from "../api";
import { ApiError } from "../api";
import { DownloadLink } from "../components/DownloadLink";
import { useApi } from "../context";
import type { SessionSummary } from "../types";

const ALGOS = ["rsa4k", "secp256r1", "secp384r1", "secp521r1"];

export default function SessionsPage() {
  const { token, session, setSession, clearSession, rememberArtifact } = useApi();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Create form
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [hsm, setHsm] = useState(false);
  const [smpk, setSmpk] = useState("rsa4k");
  const [bmpk, setBmpk] = useState("rsa4k");

  // Open form
  const [openName, setOpenName] = useState("");
  const [openPassword, setOpenPassword] = useState("");

  const [publicKeys, setPublicKeys] = useState<
    Record<string, { id: string; filename?: string | null }> | null
  >(null);

  const refresh = useCallback(() => {
    sessionsApi
      .list()
      .then(setSessions)
      .catch((e: unknown) => setError((e as Error).message));
  }, []);

  useEffect(refresh, [refresh]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await sessionsApi.create({
        name,
        password,
        hsm,
        smpk_signing_algorithm: smpk,
        bmpk_signing_algorithm: bmpk,
      });
      // Auto-open so the session is immediately usable.
      const t = await sessionsApi.open(name, password);
      setSession(name, t.token);
      setNotice(
        `Session "${name}" created and opened. Token expires at ${new Date(
          t.expires_at
        ).toLocaleTimeString()}.`
      );
      setName("");
      setPassword("");
      refresh();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function open(sessionName: string, pw: string) {
    setError(null);
    setNotice(null);
    try {
      const t = await sessionsApi.open(sessionName, pw);
      setSession(sessionName, t.token);
      setOpenName("");
      setOpenPassword("");
      setNotice(`Session "${sessionName}" opened.`);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function openWithPrompt(sessionName: string) {
    const pw = window.prompt(`Password for session "${sessionName}"`);
    if (pw === null) return;
    await open(sessionName, pw);
  }

  async function remove(sessionName: string) {
    setError(null);
    try {
      await sessionsApi.remove(sessionName);
      if (session === sessionName) {
        clearSession(); // token is now invalid
      }
      refresh();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function loadPublicKeys(sessionName: string) {
    setError(null);
    setNotice(null);
    try {
      const keys = await sessionsApi.publicKeys(sessionName, token);
      setPublicKeys(keys);
      Object.values(keys).forEach((a) => a && rememberArtifact(a));
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function makeDevelopment() {
    setError(null);
    setNotice(null);
    try {
      await sessionsApi.development("Development", {
        smpk_signing_algorithm: smpk,
        bmpk_signing_algorithm: bmpk,
      });
      setNotice(
        'F29 Development session created. Open it with name "Development", password "develop123#".'
      );
      refresh();
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <div>
      <h1>Sessions &amp; keys</h1>
      {error && <div className="error-box">{error}</div>}
      {notice && <div className="notice-box">{notice}</div>}

      <section className="card">
        <h2>Create session (generates keys, then opens it)</h2>
        <form onSubmit={create} className="form">
          <label>
            Name{" "}
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Password{" "}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <div className="row">
            <label>
              SMPK{" "}
              <select value={smpk} onChange={(e) => setSmpk(e.target.value)}>
                {ALGOS.map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label>
              BMPK{" "}
              <select value={bmpk} onChange={(e) => setBmpk(e.target.value)}>
                {ALGOS.map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={hsm}
                onChange={(e) => setHsm(e.target.checked)}
              />
              HSM
            </label>
          </div>
          <button disabled={busy}>Generate &amp; open</button>
        </form>
        <div className="row" style={{ marginTop: 12 }}>
          <button className="ghost" onClick={makeDevelopment}>
            Create F29 Development session
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Open an existing session</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            open(openName, openPassword);
          }}
          className="form row"
        >
          <label>
            Name{" "}
            <input
              value={openName}
              onChange={(e) => setOpenName(e.target.value)}
              required
            />
          </label>
          <label>
            Password{" "}
            <input
              type="password"
              value={openPassword}
              onChange={(e) => setOpenPassword(e.target.value)}
              required
            />
          </label>
          <button>Open</button>
        </form>
      </section>

      <section className="card">
        <h2>Existing sessions</h2>
        {sessions.length === 0 && <p className="muted">No sessions yet.</p>}
        <table>
          <thead>
            <tr>
              <th>name</th>
              <th>hsm</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.name}>
                <td>
                  {s.name}
                  {session === s.name && <span className="pill ok">active</span>}
                </td>
                <td>{s.hsm ? "yes" : "no"}</td>
                <td className="row">
                  <button className="ghost" onClick={() => openWithPrompt(s.name)}>
                    Open
                  </button>
                  <button className="ghost" onClick={() => loadPublicKeys(s.name)}>
                    Public keys
                  </button>
                  <button className="ghost" onClick={() => remove(s.name)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {publicKeys && (
          <div className="box">
            <h3>Public keys ({Object.keys(publicKeys).length})</h3>
            <ul>
              {Object.entries(publicKeys).map(([k, a]) => (
                <li key={k}>
                  {k}: <DownloadLink artifact={a} />
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}