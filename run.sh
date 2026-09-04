#!/usr/bin/env bash
# NEXUS — one-command dev runner. Starts backend (:8000) and frontend (:3000).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Starting NEXUS backend on :8000 ..."
cd "$ROOT/backend"
uv run uvicorn nexus.api.main:app --port 8000 --reload &
BACK=$!

echo "▶ Starting NEXUS frontend on :3000 ..."
cd "$ROOT/frontend"
[ -d node_modules ] || npm install
npm run dev &
FRONT=$!

trap "echo; echo 'stopping...'; kill $BACK $FRONT 2>/dev/null" INT TERM
echo ""
echo "  NEXUS is starting. Open http://localhost:3000"
echo "  (backend API at http://localhost:8000/api/overview)"
echo "  Press Ctrl+C to stop both."
wait
