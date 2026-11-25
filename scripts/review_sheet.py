"""Export all drafted chats to data/review.csv (UTF-8 with BOM, opens cleanly in Excel / Google Sheets)."""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cards = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
split_of = {b["id"]: s for s in ("train", "valid", "eval") for b in cards[s]}
with open(ROOT / "data/review.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["file", "line", "split", "business", "lang", "kind", "customer", "reply",
                "intent", "order_id", "handoff", "reviewer", "ok (y/n)", "what to fix"])
    for src in sorted((ROOT / "data/src").glob("*.jsonl")):
        for n, raw in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            r = json.loads(raw)
            m, t = r["meta"], r["tag"]
            w.writerow([src.name, n, split_of[m["business"]], m["business"], m["lang"], m["kind"],
                        r["customer"], r["reply"], t["intent"], t["order_id"] or "", t["handoff"], "", "", ""])
print("wrote data/review.csv")
