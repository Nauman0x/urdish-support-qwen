#!/usr/bin/env bash
# Start base and fine-tuned GGUFs on CPU with llama-server, then the demo page on http://127.0.0.1:7860
# Usage: bash demo/run_demo.sh <base.gguf> <tuned.gguf> [threads]
set -euo pipefail
BASE=$1; TUNED=$2; THREADS=${3:-4}
LLAMA=${LLAMA_CPP:-$HOME/.unsloth/llama.cpp}
cd "$(dirname "$0")/.."
serve() {  # gguf port
  "$LLAMA/llama-server" -m "$1" --port "$2" --ctx-size 2048 --threads "$THREADS" \
    --n-gpu-layers 0 --jinja --temp 0 --n-predict 320 > "/tmp/demo-$2.log" 2>&1 &
}
serve "$BASE" 8091; P1=$!
serve "$TUNED" 8092; P2=$!
trap 'kill $P1 $P2 2>/dev/null' EXIT
for port in 8091 8092; do
  for _ in $(seq 1 120); do
    curl -sf "http://127.0.0.1:$port/health" >/dev/null && continue 2
    kill -0 $P1 2>/dev/null && kill -0 $P2 2>/dev/null || { echo "llama-server failed, see /tmp/demo-$port.log"; exit 1; }
    sleep 1
  done
  echo "llama-server on $port not ready after 120 s"; exit 1
done
python3 demo/server.py --base http://127.0.0.1:8091 --tuned http://127.0.0.1:8092 --port 7860
