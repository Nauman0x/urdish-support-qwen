"""Build recipe/data/{train,valid,eval}.jsonl (chat format) from data/src/*.jsonl and data/businesses.json.

train/valid rows contain only "messages". eval rows also keep "meta" and the reference "tag" for scoring.
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import SYSTEM_PROMPT, user_content  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "recipe" / "data"


def assistant_text(row):
    return row["reply"].strip() + "\nTAG: " + json.dumps(row["tag"], ensure_ascii=False)


def main():
    cards = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    for split in sys.argv[1:] or ("train", "valid", "eval"):
        rows = []
        for biz in cards[split]:
            src = ROOT / "data/src" / f"{biz['id']}.jsonl"
            for raw in src.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                r = json.loads(raw)
                msgs = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content(biz["card"], r["customer"])},
                    {"role": "assistant", "content": assistant_text(r)},
                ]
                row = {"messages": msgs}
                if split == "eval":
                    row["meta"] = r["meta"]
                    row["tag"] = r["tag"]
                rows.append(row)
        if split != "eval":
            rng.shuffle(rows)
        with open(OUT / f"{split}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{split}: {len(rows)} rows")


if __name__ == "__main__":
    main()
