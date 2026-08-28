#!/bin/bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -x "$ROOT/venv/bin/pip" ]]; then
  echo "ERROR: $ROOT/venv/bin/pip not found." >&2
  exit 1
fi

"$ROOT/venv/bin/pip" install "$HERE"
"$ROOT/venv/bin/mlb-scoreboard-configurator-setup" --root "$ROOT"
