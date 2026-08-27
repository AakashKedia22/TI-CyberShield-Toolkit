#!/usr/bin/env bash
# Start the CyberShield Toolkit stack: crypto service + target service + web UI.
# Ctrl-C stops everything. Storage is stable under ~/.local/share + ~/.cache,
# so sessions and artifacts survive restarts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT/host/venv/bin/python"
SESSION_DIR="${TISECPROV_SESSION_DIR:-$HOME/.local/share/tisecprov/sessions}"
ARTIFACT_DIR="${CST_ARTIFACT_DIR:-$HOME/.cache/tisecprov/artifacts}"
mkdir -p "$SESSION_DIR" "$ARTIFACT_DIR"

echo "crypto service  → http://127.0.0.1:8000"
TISECPROV_SESSION_DIR="$SESSION_DIR" CST_ARTIFACT_DIR="$ARTIFACT_DIR" \
    "$PY" -m services.crypto &
CRYPTO_PID=$!

echo "target service  → http://127.0.0.1:8001"
TISECPROV_SESSION_DIR="$SESSION_DIR" CST_ARTIFACT_DIR="$ARTIFACT_DIR" \
    "$PY" -m services.target &
TARGET_PID=$!

echo "web app         → http://localhost:5173"
(cd "$ROOT/frontend" && npm run dev) &
WEB_PID=$!

trap 'kill $CRYPTO_PID $TARGET_PID $WEB_PID 2>/dev/null' EXIT INT TERM
wait