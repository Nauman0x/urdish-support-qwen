"""Upload a fine-tuned model to Hugging Face: GGUF files first (what people run), then merged weights.

python scripts/publish_hf.py --repo Nauman0x/Urdish-Support-Qwen3-1.7B --name urdish-v2-1.7b \
    --card hf/model_card_1.7b.md [--no-merged]
Needs a token with write access (hf auth login).
"""

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi

RUNS = Path(os.environ.get("RUNS", Path.home() / "qwen-hackathon/runs"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--name", required=True, help="run name, e.g. urdish-v2-1.7b")
    p.add_argument("--card", type=Path, required=True)
    p.add_argument("--no-merged", action="store_true")
    a = p.parse_args()
    api = HfApi()
    api.create_repo(a.repo, repo_type="model", exist_ok=True)
    api.upload_file(path_or_fileobj=str(a.card), path_in_repo="README.md", repo_id=a.repo)
    for quant in ["q4_k_m", "q8_0"]:
        f = RUNS / "gguf" / f"{a.name}-{quant}.gguf"
        print("uploading", f.name, flush=True)
        api.upload_file(path_or_fileobj=str(f), path_in_repo=f.name, repo_id=a.repo)
    if not a.no_merged:
        print("uploading merged 16-bit weights", flush=True)
        api.upload_folder(folder_path=str(RUNS / a.name / "merged"), repo_id=a.repo, path_in_repo="merged")
    print("done https://huggingface.co/" + a.repo)


if __name__ == "__main__":
    main()
