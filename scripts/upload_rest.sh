#!/usr/bin/env bash
# Upload the model cards now, then (after any running 4B upload) the remaining 1.7B files.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from huggingface_hub import HfApi
api = HfApi()
for repo, card in [("Nauman0x/Urdish-Support-Qwen3-4B", "hf/model_card_4b.md"),
                   ("Nauman0x/Urdish-Support-Qwen3-1.7B", "hf/model_card_1.7b.md")]:
    api.upload_file(path_or_fileobj=card, path_in_repo="README.md", repo_id=repo, commit_message="Full model card")
    print("card uploaded", repo, flush=True)
PY
while pgrep -f "publish_hf.py --repo Nauman0x/Urdish-Support-Qwen3-4B" >/dev/null; do sleep 30; done
echo "4B upload finished; starting 1.7B Q8 + merged"
python3 scripts/publish_hf.py --repo Nauman0x/Urdish-Support-Qwen3-1.7B --name urdish-v2-1.7b --card hf/model_card_1.7b.md 2>&1 | grep -v "%|"
