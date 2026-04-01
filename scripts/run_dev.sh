#!/usr/bin/env bash
# Sobe API + UI em paralelo. Linux/macOS.
# Uso: na raiz do repo: ./scripts/run_dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec python scripts/run_dev.py "$@"
