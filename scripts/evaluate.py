"""Run the held-out eval set through an OpenAI-compatible endpoint (llama-server / Ollama) and score it.

python scripts/evaluate.py --url http://127.0.0.1:8080/v1 --name base-1.7b-q4_k_m
Writes eval/results/<name>.jsonl (every output) and eval/results/<name>.json (scores).
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import detect_script, split_output  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def chat(url, model, messages, max_tokens):
    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": max_tokens, "stream": False}
    req = urllib.request.Request(
        url.rstrip("/") + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.load(r)
    return data, time.monotonic() - t0


def score(rows):
    n = len(rows)
    agg = defaultdict(int)
    by_kind = defaultdict(lambda: [0, 0])
    by_lang = defaultdict(lambda: [0, 0])
    for r in rows:
        ref, meta, tag = r["ref_tag"], r["meta"], r["tag"]
        ok_tag = tag is not None
        ok_script = r["reply_script"] == meta["lang"]
        ok_intent = ok_tag and tag.get("intent") == ref["intent"]
        oid = tag.get("order_id") if ok_tag else None
        ok_oid = ok_tag and (str(oid).lstrip("#") if oid else None) == ref["order_id"]
        ok_handoff = ok_tag and tag.get("handoff") is ref["handoff"]
        ok_all = ok_script and ok_intent and ok_oid and ok_handoff
        for k, v in [("tag_valid", ok_tag), ("script_match", ok_script), ("intent", ok_intent),
                     ("order_id", ok_oid), ("handoff", ok_handoff), ("all_correct", ok_all)]:
            agg[k] += bool(v)
        agg["devanagari"] += r["reply_script"] == "devanagari"
        by_kind[meta["kind"]][0] += bool(ok_handoff)
        by_kind[meta["kind"]][1] += 1
        by_lang[meta["lang"]][0] += bool(ok_script)
        by_lang[meta["lang"]][1] += 1
    pct = {k: round(100 * v / n, 1) for k, v in agg.items()}
    return {
        "n": n,
        "percent": pct,
        "handoff_correct_by_kind": {k: f"{a}/{b}" for k, (a, b) in by_kind.items()},
        "script_match_by_lang": {k: f"{a}/{b}" for k, (a, b) in by_lang.items()},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8080/v1")
    p.add_argument("--model", default="local")
    p.add_argument("--name", required=True)
    p.add_argument("--eval", type=Path, default=ROOT / "recipe/data/eval.jsonl")
    p.add_argument("--max-tokens", type=int, default=300)
    a = p.parse_args()
    out_dir = ROOT / "eval/results"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, gen_tps, prompt_tps, latency = [], [], [], []
    for line in a.eval.read_text(encoding="utf-8").splitlines():
        ex = json.loads(line)
        data, secs = chat(a.url, a.model, ex["messages"][:-1], a.max_tokens)
        raw = data["choices"][0]["message"].get("content") or ""
        text = THINK_RE.sub("", raw).strip()
        reply, tag = split_output(text)
        t = data.get("timings") or {}
        if t.get("predicted_per_second"):
            gen_tps.append(t["predicted_per_second"])
        if t.get("prompt_per_second"):
            prompt_tps.append(t["prompt_per_second"])
        latency.append(secs)
        rows.append({
            "customer": ex["messages"][1]["content"].split("CUSTOMER:\n", 1)[1],
            "reference": ex["messages"][-1]["content"],
            "output": raw,
            "reply": reply,
            "tag": tag,
            "ref_tag": ex["tag"],
            "meta": ex["meta"],
            "reply_script": detect_script(reply),
        })
        print(f"[{len(rows)}] {secs:.1f}s script={rows[-1]['reply_script']}/{ex['meta']['lang']} tag={'ok' if tag else 'MISSING'}",
              flush=True)
    with open(out_dir / f"{a.name}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    result = score(rows)
    mean = lambda xs: round(sum(xs) / len(xs), 1) if xs else None  # noqa: E731
    result["speed"] = {"gen_tok_per_s": mean(gen_tps), "prompt_tok_per_s": mean(prompt_tps),
                       "mean_latency_s": mean(latency)}
    result["name"] = a.name
    (out_dir / f"{a.name}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
