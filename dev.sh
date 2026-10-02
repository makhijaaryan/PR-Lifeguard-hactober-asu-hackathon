#!/usr/bin/env bash
# Starts the FastAPI backend (:8000) and the Next.js frontend (:3000). Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "Creating .venv and installing Python dependencies..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
if [ ! -d web/node_modules ]; then
  echo "Installing web dependencies..."
  (cd web && npm install --no-audit --no-fund)
fi

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

"$PY" -m uvicorn api.server:app --port 8000 --log-level warning &
(cd web && npm run dev -- --port 3000) &

sleep 3
echo
echo "  PR Lifeguard is running:  http://localhost:3000      (landing page)"
echo "  Triage app:               http://localhost:3000/app"
echo "  API:                      http://localhost:8000/api/health"
echo "  Streamlit backup:         .venv/bin/streamlit run app.py"
echo
wait
