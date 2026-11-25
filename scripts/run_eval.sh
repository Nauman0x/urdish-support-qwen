#!/usr/bin/env bash
# Serve one GGUF with llama-server on CPU only and run the held-out eval against it.
# Usage (inside WSL): bash scripts/run_eval.sh <model.gguf> <result-name> [threads]
set -euo pipefail
GGUF=$1; NAME=$2; THREADS=${3:-8}; PORT=${PORT:-8090}
LLAMA=${LLAMA_CPP:-$HOME/.unsloth/llama.cpp}
cd "$(dirname "$0")/.."
"$LLAMA/llama-server" -m "$GGUF" --port "$PORT" --ctx-size 2048 --threads "$THREADS" \
  --n-gpu-layers 0 --jinja --temp 0 --n-predict 320 > "/tmp/llama-server-$NAME.log" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break
  sleep 1
done
python3 scripts/evaluate.py --url "http://127.0.0.1:$PORT/v1" --name "$NAME" ${EVAL_FILE:+--eval "$EVAL_FILE"}
