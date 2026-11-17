import { useState } from "react";
import { artifactsApi, hasApiKey } from "../api";
import type { ArtifactRef } from "../types";

/** A download link for an artifact stored on the crypto service.
 *
 * Without an API key this is a plain link. With one, a plain link would be
 * rejected (browsers can't add X-API-Key to navigation), so the click is
 * handled with fetch + blob instead.
 */
export function DownloadLink({ artifact }: { artifact: ArtifactRef }) {
  const [error, setError] = useState<string | null>(null);
  if (!artifact?.id) return null;
  const name = artifact.filename || artifact.id;
  return (
    <>
      <a
        className="download"
        href={artifactsApi.downloadUrl(artifact.id)}
        download={name}
        title={artifact.id}
        onClick={(e) => {
          if (!hasApiKey()) return;
          e.preventDefault();
          setError(null);
          artifactsApi
            .download(artifact.id, name)
            .catch((err: unknown) => setError((err as Error).message));
        }}
      >
        {name}
      </a>
      {error && <span className="muted"> (download failed: {error})</span>}
    </>
  );
}
