#!/usr/bin/env bash
# Convert an untouched base model to GGUF (BF16, Q8_0, Q4_K_M) with the same non-thinking
# chat template the fine-tuned export uses, so base-vs-tuned comparisons are like for like.
# Usage (inside WSL, training venv active): bash scripts/make_gguf.sh <hf-id or local merged dir> <name>
set -euo pipefail
HF_ID=$1; NAME=$2
LLAMA=${LLAMA_CPP:-$HOME/.unsloth/llama.cpp}
OUT=${RUNS:-$HOME/qwen-hackathon/runs}/gguf
mkdir -p "$OUT" && TMP=$(mktemp -d)
if [ -d "$HF_ID" ]; then SNAP=$HF_ID; else
  SNAP=$(python -c "from huggingface_hub import snapshot_download as s; print(s('$HF_ID'))"); fi
cp -rL "$SNAP"/. "$TMP"/ && chmod -R u+w "$TMP"
python - "$TMP" <<'PY'
import sys
from transformers import AutoTokenizer
d = sys.argv[1]
t = AutoTokenizer.from_pretrained(d, local_files_only=True)
p = "{% set enable_thinking = false %}\n"
if not t.chat_template.startswith(p):
    t.chat_template = p + t.chat_template
t.save_pretrained(d)
PY
python "$LLAMA/convert_hf_to_gguf.py" "$TMP" --outtype bf16 --outfile "$OUT/$NAME-bf16.gguf"
for q in Q8_0 Q4_K_M; do
  "$LLAMA/llama-quantize" "$OUT/$NAME-bf16.gguf" "$OUT/$NAME-${q,,}.gguf" "$q"
done
rm -rf "$TMP"
ls -la "$OUT" | grep "$NAME"
