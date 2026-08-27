import { useState } from "react";
import { artifactsApi, certificatesApi } from "../api";
import { ApiError } from "../api";
import { DownloadLink } from "../components/DownloadLink";
import { useApi } from "../context";
import type { ArtifactRef, CertificateResult } from "../types";

const DEVICE = "f29h85x";
const SR_VERS = ["SR_10", "SR_11", "SR_12", "SR_20"];

export default function CertificatesPage() {
  const { token, session, rememberArtifact } = useApi();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // TI FEK
  const [fekFile, setFekFile] = useState<File | null>(null);
  const [fek, setFek] = useState<ArtifactRef | null>(null);

  // OTP cert form
  const [devSrVer, setDevSrVer] = useState("SR_20");
  const [msv, setMsv] = useState("0x1E22D");
  const [msvProtect, setMsvProtect] = useState(false);
  const [srSbl, setSrSbl] = useState("1");
  const [srHsmRT, setSrHsmRT] = useState("1");
  const [srApp, setSrApp] = useState("1");
  const [srSsu, setSrSsu] = useState("1");
  const [keycnt, setKeycnt] = useState(2);
  const [keyrev, setKeyrev] = useState(1);
  const [keycntProtect, setKeycntProtect] = useState(false);
  const [sProtect, setSProtect] = useState(false);
  const [bProtect, setBProtect] = useState(false);
  const [extValue, setExtValue] = useState("");
  const [extIndex, setExtIndex] = useState(0);
  const [extSize, setExtSize] = useState(128);

  // debug / recovery
  const [dbgKeyrev, setDbgKeyrev] = useState(1);
  const [dbgSwrv, setDbgSwrv] = useState(1);
  const [dbgType, setDbgType] = useState(4);
  const [dbgUid, setDbgUid] = useState("");
  const [recKeyrev, setRecKeyrev] = useState(1);
  const [recUid, setRecUid] = useState("");

  // results
  const [certResult, setCertResult] = useState<CertificateResult | null>(null);
  const [rotResult, setRotResult] = useState<ArtifactRef | null>(null);
  const [dbgResult, setDbgResult] = useState<ArtifactRef | null>(null);
  const [recResult, setRecResult] = useState<ArtifactRef | null>(null);

  if (!token || !session) {
    return (
      <div className="card">
        <h1>Certificates</h1>
        <p className="muted">
          Open a session on the Sessions page first (its token is required for
          certificate generation).
        </p>
      </div>
    );
  }

  async function uploadFek(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!fekFile) return;
    try {
      const a = await artifactsApi.upload(fekFile, "tifek", DEVICE);
      setFek(a);
      rememberArtifact(a);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function genCert(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (!fek) throw new Error("Upload the TI FEK public key first");
      const body: Record<string, unknown> = {
        devSrVer,
        tifek_artifact: fek,
        msv,
        msv_protect: msvProtect,
        sr_sbl: srSbl,
        sr_hsmRT: srHsmRT,
        sr_app: srApp,
        sr_ssu: srSsu,
        keycnt,
        keycnt_protect: keycntProtect,
        keyrev,
        s_protect: sProtect,
        b_protect: bProtect,
      };
      if (extValue) {
        body.ext_otp = { value: extValue, index: extIndex, size: extSize };
      }
      const result = await certificatesApi.generate(DEVICE, body, token);
      setCertResult(result);
      const bundle = result.certificates[0];
      [bundle?.primary_cert, bundle?.secondary_cert, bundle?.final_cert]
        .concat(result.keycert_headers)
        .forEach((a) => a && rememberArtifact(a));
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function genRot() {
    setError(null);
    setBusy(true);
    try {
      const r = await certificatesApi.rot(DEVICE, token);
      setRotResult(r.rot_switching_cert);
      rememberArtifact(r.rot_switching_cert);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function genDebug(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await certificatesApi.debug(DEVICE, {
        keyrev: dbgKeyrev,
        swrv: dbgSwrv,
        dev_dbg_type: dbgType,
        dev_uid: dbgUid,
      }, token);
      setDbgResult(r.debug_cert);
      rememberArtifact(r.debug_cert);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function genRecovery(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await certificatesApi.recovery(DEVICE, {
        keyrev: recKeyrev,
        dev_uid: recUid,
      }, token);
      setRecResult(r.recovery_cert);
      rememberArtifact(r.recovery_cert);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Certificates</h1>
      {error && <div className="error-box">{error}</div>}

      <section className="card">
        <h2>TI FEK public key</h2>
        <form onSubmit={uploadFek} className="form">
          <input
            type="file"
            accept=".pem"
            onChange={(e) => setFekFile(e.target.files?.[0] ?? null)}
          />
          <button>Upload</button>
        </form>
        {fek && (
          <p className="muted">
            uploaded: <DownloadLink artifact={fek} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>OTP key certificate</h2>
        <form onSubmit={genCert} className="cert-form">
          <div className="field-group">
            <h3>Revision</h3>
            <div className="fields">
              <label className="field">
                Silicon revision
                <select value={devSrVer} onChange={(e) => setDevSrVer(e.target.value)}>
                  {SR_VERS.map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                MSV
                <input value={msv} onChange={(e) => setMsv(e.target.value)} />
              </label>
            </div>
          </div>

          <div className="field-group">
            <h3>Software revisions</h3>
            <div className="fields">
              <label className="field">
                SBL
                <input value={srSbl} onChange={(e) => setSrSbl(e.target.value)} />
              </label>
              <label className="field">
                HSM runtime
                <input value={srHsmRT} onChange={(e) => setSrHsmRT(e.target.value)} />
              </label>
              <label className="field">
                App
                <input value={srApp} onChange={(e) => setSrApp(e.target.value)} />
              </label>
              <label className="field">
                SSU
                <input value={srSsu} onChange={(e) => setSrSsu(e.target.value)} />
              </label>
            </div>
          </div>

          <div className="field-group">
            <h3>Key slots</h3>
            <div className="fields">
              <label className="field">
                Key count
                <input
                  type="number"
                  value={keycnt}
                  onChange={(e) => setKeycnt(Number(e.target.value))}
                />
              </label>
              <label className="field">
                Key revision
                <input
                  type="number"
                  value={keyrev}
                  onChange={(e) => setKeyrev(Number(e.target.value))}
                />
              </label>
            </div>
            <div className="flags">
              <label className="flag">
                <input
                  type="checkbox"
                  checked={msvProtect}
                  onChange={(e) => setMsvProtect(e.target.checked)}
                />
                MSV protect
              </label>
              <label className="flag">
                <input
                  type="checkbox"
                  checked={keycntProtect}
                  onChange={(e) => setKeycntProtect(e.target.checked)}
                />
                Keycnt protect
              </label>
              <label className="flag">
                <input
                  type="checkbox"
                  checked={sProtect}
                  onChange={(e) => setSProtect(e.target.checked)}
                />
                SMPK/SMEK protect
              </label>
              <label className="flag">
                <input
                  type="checkbox"
                  checked={bProtect}
                  onChange={(e) => setBProtect(e.target.checked)}
                />
                BMPK/BMEK protect
              </label>
            </div>
          </div>

          <div className="field-group">
            <h3>Extended OTP</h3>
            <div className="fields">
              <label className="field">
                Value
                <input
                  value={extValue}
                  onChange={(e) => setExtValue(e.target.value)}
                  placeholder="0x80000001"
                />
              </label>
              <label className="field">
                Index
                <input
                  type="number"
                  value={extIndex}
                  onChange={(e) => setExtIndex(Number(e.target.value))}
                />
              </label>
              <label className="field">
                Size (bits)
                <input
                  type="number"
                  value={extSize}
                  onChange={(e) => setExtSize(Number(e.target.value))}
                />
              </label>
            </div>
          </div>

          <button disabled={busy}>Generate certificate</button>
        </form>

        {certResult && (
          <div className="box">
            {certResult.certificates[0] && (
              <ul>
                <li>
                  primary:{" "}
                  <DownloadLink artifact={certResult.certificates[0].primary_cert!} />
                </li>
                <li>
                  secondary:{" "}
                  <DownloadLink artifact={certResult.certificates[0].secondary_cert!} />
                </li>
                <li>
                  final:{" "}
                  <DownloadLink artifact={certResult.certificates[0].final_cert!} />
                </li>
              </ul>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2>ROT switching certificate</h2>
        <button className="ghost" onClick={genRot} disabled={busy}>
          Generate ROT cert
        </button>
        {rotResult && (
          <p>
            <DownloadLink artifact={rotResult} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Debug certificate</h2>
        <form onSubmit={genDebug} className="cert-form">
          <div className="field-group">
            <div className="fields">
              <label className="field">
                Key revision
                <input
                  type="number"
                  value={dbgKeyrev}
                  onChange={(e) => setDbgKeyrev(Number(e.target.value))}
                />
              </label>
              <label className="field">
                SW revision
                <input
                  type="number"
                  value={dbgSwrv}
                  onChange={(e) => setDbgSwrv(Number(e.target.value))}
                />
              </label>
              <label className="field">
                Debug type
                <input
                  type="number"
                  value={dbgType}
                  onChange={(e) => setDbgType(Number(e.target.value))}
                />
              </label>
            </div>
          </div>
          <div className="field-group">
            <div className="fields">
              <label className="field" style={{ minWidth: 320 }}>
                Device UID (128 hex chars)
                <input value={dbgUid} onChange={(e) => setDbgUid(e.target.value)} />
              </label>
            </div>
          </div>
          <button disabled={busy}>Generate</button>
        </form>
        {dbgResult && (
          <p>
            <DownloadLink artifact={dbgResult} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Device recovery certificate</h2>
        <form onSubmit={genRecovery} className="cert-form">
          <div className="field-group">
            <div className="fields">
              <label className="field">
                Key revision
                <input
                  type="number"
                  value={recKeyrev}
                  onChange={(e) => setRecKeyrev(Number(e.target.value))}
                />
              </label>
              <label className="field" style={{ minWidth: 320 }}>
                Device UID (128 hex chars)
                <input value={recUid} onChange={(e) => setRecUid(e.target.value)} />
              </label>
            </div>
          </div>
          <button disabled={busy}>Generate</button>
        </form>
        {recResult && (
          <p>
            <DownloadLink artifact={recResult} />
          </p>
        )}
      </section>
    </div>
  );
}