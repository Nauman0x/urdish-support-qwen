"""Build submission/pixie/README.md and hf/model_card_*.md from README.md (absolute links)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://github.com/Nauman0x/urdish-support-qwen/blob/main/"

s = (ROOT / "README.md").read_text(encoding="utf-8")
s = re.sub(r"\]\((?!https?://)([^)#]+)\)", lambda m: f"]({BASE}{m.group(1)})", s)
s = s.replace("# Urdish Support Agent\n\n", "# Urdish Support Agent\n\nCode, data and evaluation: "
              "https://github.com/Nauman0x/urdish-support-qwen\n\n## What it does\n\n", 1)
(ROOT / "submission/pixie/README.md").write_text(s, encoding="utf-8", newline="\n")

body = s.split("\n", 1)[1]
files = {
    "4B": "`urdish-v2-4b-q4_k_m.gguf` (2.5 GB, recommended), `urdish-v2-4b-q8_0.gguf` (4.3 GB), `merged/` (16-bit safetensors)",
    "1.7B": "`urdish-v2-1.7b-q8_0.gguf` (1.8 GB, recommended for this size), `urdish-v2-1.7b-q4_k_m.gguf` (1.1 GB, weaker, see results), `merged/` (16-bit safetensors)",
}
for size, rec in files.items():
    head = (f"---\nlicense: apache-2.0\nbase_model: Qwen/Qwen3-{size}\nlanguage: [ur, en]\npipeline_tag: text-generation\n"
            f"tags: [qwen3, gguf, customer-support, urdu, roman-urdu, qlora, unsloth, llama.cpp]\n---\n\n"
            f"# Urdish Support Agent: Qwen3-{size}\n\n**Files in this repo:** {rec}.\n")
    if size == "1.7B":
        head += ("\n> The 4B model is the recommended one: it is much better on facts (82% vs 53% in our blind check). "
                 "Use this 1.7B where memory is very tight, ideally the Q8_0 file.\n")
    (ROOT / f"hf/model_card_{size.lower()}.md").write_text(head + body, encoding="utf-8", newline="\n")
print("built submission README and model cards")
