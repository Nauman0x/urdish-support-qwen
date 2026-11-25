"""Check drafted source files in data/src/*.jsonl against the spec.

Each line: {"customer": str, "reply": str, "tag": {intent, order_id, handoff}, "meta": {business, lang, kind}}
Usage: python scripts/check_src.py [files...]   (default: all data/src/*.jsonl)
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import INTENTS, detect_script  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"answerable", "silent", "lookup", "human", "injection", "smalltalk"}
HANDOFF_KINDS = {"silent", "lookup", "human"}


def check(path, business_ids):
    errs, warns, langs, kinds = [], [], Counter(), Counter()
    seen = set()
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        p = f"{path.name}:{n}"
        try:
            r = json.loads(raw)
        except json.JSONDecodeError as e:
            errs.append(f"{p} bad JSON: {e}")
            continue
        c, rep, tag, meta = r.get("customer"), r.get("reply"), r.get("tag"), r.get("meta")
        if not (isinstance(c, str) and c.strip() and isinstance(rep, str) and rep.strip()):
            errs.append(f"{p} customer/reply must be non-empty strings")
            continue
        if "TAG:" in rep:
            errs.append(f"{p} reply must not contain the TAG line (it is added by the build)")
        if c in seen:
            errs.append(f"{p} duplicate customer message")
        seen.add(c)
        if not isinstance(tag, dict) or set(tag) != {"intent", "order_id", "handoff"}:
            errs.append(f"{p} tag must have exactly intent, order_id, handoff")
            continue
        if tag["intent"] not in INTENTS:
            errs.append(f"{p} bad intent {tag['intent']!r}")
        if not (tag["order_id"] is None or isinstance(tag["order_id"], str)):
            errs.append(f"{p} order_id must be string or null")
        elif tag["order_id"] and tag["order_id"] not in c:
            errs.append(f"{p} order_id {tag['order_id']!r} not found in customer text")
        if not isinstance(tag["handoff"], bool):
            errs.append(f"{p} handoff must be boolean")
        if not isinstance(meta, dict) or meta.get("business") not in business_ids:
            errs.append(f"{p} meta.business must be one of the card ids")
            continue
        if meta.get("lang") not in {"roman", "urdu", "english"} or meta.get("kind") not in KINDS:
            errs.append(f"{p} meta.lang/meta.kind invalid")
            continue
        if (meta["kind"] in HANDOFF_KINDS) != tag["handoff"]:
            errs.append(f"{p} kind {meta['kind']} but handoff={tag['handoff']}")
        got_c, got_r = detect_script(c), detect_script(rep)
        if got_r != meta["lang"]:
            warns.append(f"{p} reply looks {got_r}, meta.lang={meta['lang']}")
        if got_c != meta["lang"]:
            warns.append(f"{p} customer looks {got_c}, meta.lang={meta['lang']}")
        langs[meta["lang"]] += 1
        kinds[meta["kind"]] += 1
    return errs, warns, langs, kinds


def main():
    cards = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
    ids = {b["id"] for split in ("train", "valid", "eval") for b in cards[split]}
    files = [Path(f) for f in sys.argv[1:]] or sorted((ROOT / "data/src").glob("*.jsonl"))
    bad = 0
    for f in files:
        errs, warns, langs, kinds = check(f, ids)
        print(f"{f.name}: {sum(langs.values())} rows | langs {dict(langs)} | kinds {dict(kinds)}")
        for e in errs:
            print("  ERROR", e)
        for w in warns:
            print("  warn ", w)
        bad += len(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
