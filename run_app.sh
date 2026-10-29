#!/usr/bin/env bash
# One-command launcher for macOS / Linux / WSL / Codespaces: installs the locked
# dependencies, then opens the Streamlit app. Windows users: Start_AI_STOCK_ANALYZER.bat.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/ and re-run." >&2
  exit 1
fi

uv sync --locked
exec uv run streamlit run app.py "$@"
