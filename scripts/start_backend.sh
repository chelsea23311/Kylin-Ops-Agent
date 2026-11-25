#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

cd "$ROOT_DIR/program2"
ENV_ARGS=()
if [[ -f "$ROOT_DIR/.env" ]]; then
  ENV_ARGS=(--env-file "$ROOT_DIR/.env")
fi
exec "$PYTHON_BIN" -m uvicorn main:app \
  "${ENV_ARGS[@]}" \
  --host "${BACKEND_HOST:-127.0.0.1}" \
  --port "${BACKEND_PORT:-8000}"
