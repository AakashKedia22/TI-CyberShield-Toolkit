import { artifactsApi } from "../api";
import type { ArtifactRef } from "../types";

/** A download link for an artifact stored on the crypto service. */
export function DownloadLink({ artifact }: { artifact: ArtifactRef }) {
  if (!artifact?.id) return null;
  return (
    <a
      className="download"
      href={artifactsApi.downloadUrl(artifact.id)}
      title={artifact.id}
    >
      {artifact.filename || artifact.id}
    </a>
  );
}