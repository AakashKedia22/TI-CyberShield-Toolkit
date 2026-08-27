import { useState } from "react";
import { Link } from "react-router-dom";
import { artifactsApi, imagesApi } from "../api";
import { ApiError } from "../api";
import { DownloadLink } from "../components/DownloadLink";
import { useApi } from "../context";
import type { ArtifactRef } from "../types";

const DEVICE = "f29h85x";

export default function ImagesPage() {
  const { token, session, rememberArtifact } = useApi();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [image, setImage] = useState<ArtifactRef | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [key, setKey] = useState<ArtifactRef | null>(null);

  // sign form
  const [core, setCore] = useState("C29");
  const [boot, setBoot] = useState("FLASH");
  const [loadaddr, setLoadaddr] = useState("0x10001000");
  const [swrv, setSwrv] = useState("1");
  const [keyrev, setKeyrev] = useState("1");
  const [debug, setDebug] = useState("");
  const [sblEnc, setSblEnc] = useState(false);
  const [tifsEnc, setTifsEnc] = useState(false);
  const [fwEnc, setFwEnc] = useState(false);

  // seccfg
  const [secCfgImage, setSecCfgImage] = useState<ArtifactRef | null>(null);
  const [secCfgSwrv, setSecCfgSwrv] = useState("1");
  const [secCfgKeyrev, setSecCfgKeyrev] = useState("1");
  const [ccsPath, setCcsPath] = useState("");

  // encrypt
  const [encMode, setEncMode] = useState("sbl_enc");

  const [signed, setSigned] = useState<ArtifactRef | null>(null);
  const [seccfg, setSeccfg] = useState<ArtifactRef | null>(null);
  const [encrypted, setEncrypted] = useState<ArtifactRef | null>(null);
  const [batchJob, setBatchJob] = useState<string | null>(null);

  if (!token || !session) {
    return (
      <div className="card">
        <h1>Images</h1>
        <p className="muted">
          Open a session on the Sessions page first (required for signing).
        </p>
      </div>
    );
  }

  async function upload(file: File, purpose: string) {
    const a = await artifactsApi.upload(file, purpose, DEVICE);
    rememberArtifact(a);
    return a;
  }

  async function uploadImage(e: React.FormEvent) {
    e.preventDefault();
    if (!imageFile) return;
    setError(null);
    try {
      setImage(await upload(imageFile, "image"));
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function sign(e: React.FormEvent) {
    e.preventDefault();
    if (!image) return;
    setError(null);
    setBusy(true);
    try {
      const r = await imagesApi.sign(
        DEVICE,
        {
          image_artifact: image,
          input_format: "BIN",
          core,
          boot,
          loadaddr,
          swrv,
          keyrev,
          debug: debug || null,
          sbl_enc: sblEnc,
          tifs_enc: tifsEnc,
          fw_enc: fwEnc,
        },
        token
      );
      setSigned(r.signed_image);
      rememberArtifact(r.signed_image);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadSeccfg(e: React.FormEvent) {
    e.preventDefault();
    if (!secCfgImage) {
      setError("Upload a seccfg image first");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const r = await imagesApi.signSeccfg(
        DEVICE,
        {
          image_artifact: secCfgImage,
          swrv: secCfgSwrv,
          keyrev: secCfgKeyrev,
          boot: "FLASH",
          ccs_path: ccsPath,
        },
        token
      );
      setSeccfg(r.seccfg_bin);
      rememberArtifact(r.seccfg_bin);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadKey(e: React.FormEvent) {
    e.preventDefault();
    if (!keyFile) return;
    setError(null);
    try {
      setKey(await upload(keyFile, "aes_key"));
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  async function encrypt(e: React.FormEvent) {
    e.preventDefault();
    if (!image) return;
    setError(null);
    setBusy(true);
    try {
      const r = await imagesApi.encrypt(
        DEVICE,
        { image_artifact: image, key: key ?? null, encryption_mode: encMode },
        token
      );
      setEncrypted(r.encrypted_image);
      rememberArtifact(r.encrypted_image);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  async function batchSign() {
    setError(null);
    try {
      const job = await imagesApi.signBatch(DEVICE, {}, token);
      setBatchJob(job.id);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }

  return (
    <div>
      <h1>Images</h1>
      {error && <div className="error-box">{error}</div>}

      <section className="card">
        <h2>Upload image</h2>
        <form onSubmit={uploadImage} className="form row">
          <input
            type="file"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
          />
          <button>Upload</button>
        </form>
        {image && (
          <p className="muted">
            image: <DownloadLink artifact={image} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Sign application (signapp)</h2>
        <form onSubmit={sign} className="form grid2">
          <label>
            Core{" "}
            <select value={core} onChange={(e) => setCore(e.target.value)}>
              <option>C29</option>
              <option>HSM</option>
            </select>
          </label>
          <label>
            Boot{" "}
            <select value={boot} onChange={(e) => setBoot(e.target.value)}>
              <option>FLASH</option>
              <option>RAM</option>
            </select>
          </label>
          <label>
            Load addr <input value={loadaddr} onChange={(e) => setLoadaddr(e.target.value)} />
          </label>
          <label>
            SW rev <input value={swrv} onChange={(e) => setSwrv(e.target.value)} />
          </label>
          <label>
            Key rev{" "}
            <select value={keyrev} onChange={(e) => setKeyrev(e.target.value)}>
              <option>1</option>
              <option>2</option>
            </select>
          </label>
          <label>
            Debug <input value={debug} onChange={(e) => setDebug(e.target.value)} placeholder="DBG_SOC_DEFAULT" />
          </label>
          <label className="check">
            <input type="checkbox" checked={sblEnc} onChange={(e) => setSblEnc(e.target.checked)} /> SBL enc
          </label>
          <label className="check">
            <input type="checkbox" checked={tifsEnc} onChange={(e) => setTifsEnc(e.target.checked)} /> TIFS enc
          </label>
          <label className="check">
            <input type="checkbox" checked={fwEnc} onChange={(e) => setFwEnc(e.target.checked)} /> FW enc
          </label>
          <button disabled={busy}>Sign</button>
        </form>
        {signed && (
          <p>
            signed: <DownloadLink artifact={signed} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Sign Sec-Cfg (needs CCS)</h2>
        <form onSubmit={uploadSeccfg} className="form grid2">
          <label>
            Sec-Cfg image{" "}
            <input
              type="file"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (f) setSecCfgImage(await upload(f, "seccfg"));
              }}
            />
          </label>
          <label>
            CCS path{" "}
            <input value={ccsPath} onChange={(e) => setCcsPath(e.target.value)} placeholder="/path/to/ccs" />
          </label>
          <label>
            SW rev <input value={secCfgSwrv} onChange={(e) => setSecCfgSwrv(e.target.value)} />
          </label>
          <label>
            Key rev{" "}
            <select value={secCfgKeyrev} onChange={(e) => setSecCfgKeyrev(e.target.value)}>
              <option>1</option>
              <option>2</option>
            </select>
          </label>
          <button disabled={busy}>Sign Sec-Cfg</button>
        </form>
        {seccfg && (
          <p>
            seccfg: <DownloadLink artifact={seccfg} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Encrypt binary</h2>
        <form onSubmit={uploadKey} className="form row">
          <input
            type="file"
            onChange={(e) => setKeyFile(e.target.files?.[0] ?? null)}
          />
          <button className="ghost">Upload key</button>
        </form>
        <form onSubmit={encrypt} className="form row">
          <label>
            Mode{" "}
            <select value={encMode} onChange={(e) => setEncMode(e.target.value)}>
              <option>sbl_enc</option>
              <option>tifs_enc</option>
              <option>fw_enc</option>
            </select>
          </label>
          <button disabled={busy}>Encrypt</button>
        </form>
        {encrypted && (
          <p>
            encrypted: <DownloadLink artifact={encrypted} />
          </p>
        )}
      </section>

      <section className="card">
        <h2>Batch sign prebuilt binaries</h2>
        <button className="ghost" onClick={batchSign}>
          Start batch sign (async job)
        </button>
        {batchJob && (
          <p>
            job started:{" "}
            <Link to={`/jobs/crypto/${batchJob}`}>{batchJob}</Link>
          </p>
        )}
      </section>
    </div>
  );
}