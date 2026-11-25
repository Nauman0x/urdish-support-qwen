#!/usr/bin/env bash
# Choose epochs on the VALIDATION businesses only. Each candidate: train -> Q4_K_M -> CPU eval on valid.
# Usage (inside WSL, venv active): bash scripts/sweep.sh unsloth/Qwen3-1.7B s17 1 2 3
set -uo pipefail
HF_ID=$1; TAG=$2; shift 2
RUNS=${RUNS:-$HOME/qwen-hackathon/runs}; LLAMA=${LLAMA_CPP:-$HOME/.unsloth/llama.cpp}
cd "$(dirname "$0")/.."
for ep in "$@"; do
  NAME=$TAG-e$ep; OUT=$RUNS/sweep/$NAME; mkdir -p "$OUT"
  python3 scripts/train_qlora.py --model "$HF_ID" --epochs "$ep" --output "$OUT" > "$OUT/train.log" 2>&1 || { echo "$NAME train failed"; continue; }
  python3 "$LLAMA/convert_hf_to_gguf.py" "$OUT/merged" --outtype bf16 --outfile "$OUT/bf16.gguf" > "$OUT/convert.log" 2>&1
  "$LLAMA/llama-quantize" "$OUT/bf16.gguf" "$OUT/q4_k_m.gguf" Q4_K_M >> "$OUT/convert.log" 2>&1
  rm -rf "$OUT/bf16.gguf" "$OUT/merged" "$OUT/checkpoints"
  bash scripts/run_eval.sh "$OUT/q4_k_m.gguf" "valid-$NAME" 8 > "$OUT/eval.log" 2>&1 || true
  echo "$NAME done"
done
