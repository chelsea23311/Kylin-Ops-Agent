#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT_DIR/scripts/start_inference.sh" &
INFERENCE_PID=$!

"$ROOT_DIR/scripts/start_backend.sh" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$INFERENCE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "$BACKEND_PID" "$INFERENCE_PID"
