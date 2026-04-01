#!/usr/bin/env bash
# Executa o setup de desenvolvimento (venv + pip + npm). Linux/macOS.
# Uso: na raiz do repo: ./scripts/setup_dev.sh   ou   bash scripts/setup_dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec python scripts/setup_dev.py "$@"
