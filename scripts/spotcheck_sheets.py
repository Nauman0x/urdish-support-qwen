"""Write two human spot-check sheets: 40 random rows (20 Roman Urdu, 10 Urdu, 10 English), 20 per reviewer.

Each row shows the policy card next to the customer message and reply, so a reviewer can check facts,
language and the handoff decision. Seeded, so the sample is reproducible.
python scripts/spotcheck_sheets.py
"""

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
    cards = {b["id"]: b["card"] for s in ("train", "valid", "eval") for b in data[s]}
    rows = []
    for f in sorted((ROOT / "data/src").glob("*.jsonl")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                rows.append((f.name, n, json.loads(line)))
    rng = random.Random(2026)
    rng.shuffle(rows)
    want, pick = {"roman": 20, "urdu": 10, "english": 10}, []
    for row in rows:
        lang = row[2]["meta"]["lang"]
        if want[lang] > 0:
            pick.append(row)
            want[lang] -= 1
        if not any(want.values()):
            break
    rng.shuffle(pick)
    header = ["#", "business", "language", "policy card (the only facts the reply may use)", "customer message",
              "reply", "handed to team?", "OK? (y/n)", "what is wrong / better wording"]
    for name, part in [("esha", pick[:20]), ("khadija", pick[20:])]:
        out = ROOT / f"data/spotcheck_{name}.csv"
        if out.exists():  # never overwrite a sheet a reviewer may have filled in
            print(f"{out.name} exists, skipped (delete it to regenerate)")
            continue
        with open(out, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            for i, (_, _, r) in enumerate(part, 1):
                w.writerow([i, r["meta"]["business"], r["meta"]["lang"], cards[r["meta"]["business"]], r["customer"],
                            r["reply"], "yes" if r["tag"]["handoff"] else "no", "", ""])
        print(f"data/spotcheck_{name}.csv: {len(part)} rows")


if __name__ == "__main__":
    main()
