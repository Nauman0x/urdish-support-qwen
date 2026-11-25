#!/usr/bin/env bash
# v2 final models (settings chosen on the validation set): train on data v2, export, score Q4 + Q8 on held-out eval.
# Usage (inside WSL, venv active): bash scripts/final_v2.sh
set -euo pipefail
RUNS=${RUNS:-$HOME/qwen-hackathon/runs}
cd "$(dirname "$0")/.."
train() {  # hf_id epochs name
  python3 scripts/train_qlora.py --model "$1" --epochs "$2" --output "$RUNS/$3" > "$RUNS/train-$3.log" 2>&1
  bash scripts/make_gguf.sh "$RUNS/$3/merged" "$3" >> "$RUNS/train-$3.log" 2>&1
  cp "$RUNS/$3/run.json" "eval/run-$3.json"
  echo "trained $3"
}
train unsloth/Qwen3-1.7B 3 urdish-v2-1.7b
train unsloth/Qwen3-4B 1 urdish-v2-4b
bash scripts/eval_many.sh urdish-v2-1.7b-q4_k_m urdish-v2-4b-q4_k_m urdish-v2-1.7b-q8_0
