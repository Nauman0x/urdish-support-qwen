#!/usr/bin/env bash
# Evaluate several GGUFs from $RUNS/gguf one after another (CPU only) and print a summary.
# Usage (inside WSL): bash scripts/eval_many.sh base-1.7b-q4_k_m base-4b-q4_k_m ...
set -uo pipefail
RUNS=${RUNS:-$HOME/qwen-hackathon/runs}
cd "$(dirname "$0")/.."
for m in "$@"; do
  bash scripts/run_eval.sh "$RUNS/gguf/$m.gguf" "$m" "${THREADS:-8}" > "$RUNS/eval-$m.log" 2>&1
  echo "$m exit=$?"
done
for m in "$@"; do
  python3 -c "import json,sys; d=json.load(open('eval/results/'+sys.argv[1]+'.json')); print(d['name'], d['percent'], d['speed'])" "$m"
done
