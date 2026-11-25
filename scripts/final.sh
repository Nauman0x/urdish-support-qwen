#!/usr/bin/env bash
# Final models (settings chosen on the validation set): train, export BF16/Q8_0/Q4_K_M, score on held-out eval.
# Usage (inside WSL, venv active): bash scripts/final.sh
set -euo pipefail
RUNS=${RUNS:-$HOME/qwen-hackathon/runs}
cd "$(dirname "$0")/.."
train() {  # hf_id epochs name
  python3 scripts/train_qlora.py --model "$1" --epochs "$2" --output "$RUNS/$3" > "$RUNS/train-$3.log" 2>&1
  bash scripts/make_gguf.sh "$RUNS/$3/merged" "$3" >> "$RUNS/train-$3.log" 2>&1
  cp "$RUNS/$3/run.json" "eval/run-$3.json"
  echo "trained $3"
}
train unsloth/Qwen3-4B 1 urdish-4b
train unsloth/Qwen3-1.7B 3 urdish-1.7b
bash scripts/eval_many.sh urdish-4b-q4_k_m urdish-1.7b-q4_k_m urdish-4b-q8_0 urdish-1.7b-q8_0 \
  urdish-4b-bf16 urdish-1.7b-bf16 base-4b-q8_0 base-1.7b-q8_0 base-4b-bf16 base-1.7b-bf16
