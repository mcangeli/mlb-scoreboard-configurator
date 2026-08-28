#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PYTHONPATH="$HERE" python3 -m unittest discover -s "$HERE/tests"
