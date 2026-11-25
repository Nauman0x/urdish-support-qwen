#!/usr/bin/env bash
# QLoRA fine-tune with the finetune-anywhere starter trainer (Unsloth), then GGUF BF16/Q8_0/Q4_K_M.
# Usage (inside WSL): bash scripts/train.sh starter tuned-1.7b     # or: larger tuned-4b
set -euo pipefail
ALIAS=$1; NAME=$2
STARTER=${STARTER:-$HOME/qwen-hackathon/finetune-anywhere}
RUNS=${RUNS:-$HOME/qwen-hackathon/runs}
cd "$(dirname "$0")/.."
python3 scripts/build_data.py
python3 "$STARTER/paths/nvidia-gpu/train_unsloth.py" --config recipe/config.yaml --model "$ALIAS" --output "$RUNS/$NAME"
bash scripts/make_gguf.sh "$RUNS/$NAME/merged" "$NAME"
cp "$RUNS/$NAME/run.json" "eval/run-$NAME.json"
