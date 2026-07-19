#!/usr/bin/env bash
# Run the whole Aletheia demo locally on a Mac — no GPU, no AWS.
# Starts the MLX backend (base + tuned, 4-bit) and the web dev server, then serves the
# real UI at http://localhost:5173. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=finetune/.venv
[[ -d "$VENV" ]] || { echo "missing $VENV — see finetune/README.md"; exit 1; }
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -c "import fastapi, uvicorn" 2>/dev/null || pip install -q fastapi "uvicorn[standard]" pydantic

echo "==> starting MLX backend on :8080 (loads two 4-bit models, ~30s) ..."
python serving/local_mlx_server.py > serving/local_mlx_server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT

# wait for the backend to be ready
for _ in $(seq 1 60); do
  curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1 && break
  sleep 2
done
curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1 \
  || { echo "backend did not come up — see serving/local_mlx_server.log"; exit 1; }
echo "==> backend ready."

echo "==> starting web UI — open the URL it prints (http://localhost:5173)"
cd web
[[ -d node_modules ]] || npm install
VITE_API_TARGET=http://127.0.0.1:8080 npm run dev
