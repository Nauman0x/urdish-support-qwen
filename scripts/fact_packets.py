"""Write blind fact-check packets: each held-out chat with the policy card and every model's reply in shuffled order.

Grading question per reply: does it state anything that contradicts or goes beyond the policy card?
The key file (which reply came from which model) is kept separate so grading is blind.

python scripts/fact_packets.py base-1.7b-q4_k_m urdish-v2-1.7b-q4_k_m base-4b-q4_k_m urdish-v2-4b-q4_k_m
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = sys.argv[1:]
    cards = {b["id"]: b["card"] for b in json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))["eval"]}
    runs = {n: [json.loads(l) for l in (ROOT / f"eval/results/{n}.jsonl").read_text(encoding="utf-8").splitlines()] for n in names}
    rng = random.Random(7)
    packets, key = [], []
    for i in range(len(runs[names[0]])):
        rows = [runs[n][i] for n in names]
        assert len({r["customer"] for r in rows}) == 1
        order = names[:]
        rng.shuffle(order)
        packets.append({
            "id": i,
            "policy": cards[rows[0]["meta"]["business"]],
            "customer": rows[0]["customer"],
            "replies": {chr(65 + k): runs[n][i]["reply"] for k, n in enumerate(order)},
        })
        key.append({"id": i, **{chr(65 + k): n for k, n in enumerate(order)}})
    out = ROOT / "eval/facts"
    out.mkdir(parents=True, exist_ok=True)
    (out / "packets.json").write_text(json.dumps(packets, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(f"{len(packets)} packets x {len(names)} replies -> {out}")


if __name__ == "__main__":
    main()
