#!/usr/bin/env bash
# NEXUS — health check: regenerate data, run eval, run tests.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
echo "▶ Regenerating synthetic worlds ..."
uv run python -m nexus.generator.build_dataset >/dev/null
echo "▶ Running held-out evaluation ..."
uv run python -m nexus.eval.run_eval | tail -9
echo ""
echo "▶ Running test suite ..."
uv run pytest tests/ -q
