#!/usr/bin/env bash
# One-command launcher for macOS / Linux / WSL / Codespaces: installs the locked
# dependencies, then opens the Streamlit app. Windows users: Start_AI_STOCK_ANALYZER.bat.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/ and re-run." >&2
  exit 1
fi

# Same flags as the Dockerfile: only prebuilt wheels from uv.lock (no package build scripts
# run), runtime dependencies only. The app imports first-party code from this folder, so the
# project itself does not need installing. Use `make install` for the full dev environment.
uv sync --locked --no-dev --no-install-project --no-build
exec uv run --no-sync streamlit run app.py "$@"
