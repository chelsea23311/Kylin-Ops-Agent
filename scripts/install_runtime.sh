#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/venv}"

if [[ ! -f "$ROOT_DIR/requirements.txt" ]]; then
  echo "requirements.txt not found: $ROOT_DIR/requirements.txt" >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"

if [[ ! -f "$ROOT_DIR/operations-and-maintenance/dist/index.html" ]]; then
  cat >&2 <<'EOF'
warning: operations-and-maintenance/dist/index.html not found.
The release package normally includes frontend dist. If you are deploying
from source, install Node.js dependencies and run npm run build in
operations-and-maintenance.
EOF
fi

echo "runtime installed: $VENV_DIR"
