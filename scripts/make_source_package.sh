#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${PYTHON_BIN:-python3}" "$ROOT_DIR/scripts/package_project.py" source "${1:-$(date +%Y%m%d)}"
