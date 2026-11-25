"""Side-by-side demo: base vs fine-tuned Qwen3, both served by llama-server on CPU.

Standard library only. Serves demo/index.html, the policy cards and the system prompt, and forwards
chat requests to two llama-server endpoints so the page needs no CORS setup.

python demo/server.py --base http://127.0.0.1:8091 --tuned http://127.0.0.1:8092 --port 7860
"""

import argparse
import json
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import SYSTEM_PROMPT, split_output, user_content  # noqa: E402


def load_cards():
    data = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
    # Held-out businesses first: the model never saw them in training.
    return [{**b, "split": s} for s in ("eval", "valid", "train") for b in data[s]]


class Handler(BaseHTTPRequestHandler):
    endpoints = {}

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (Path(__file__).parent / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/cards":
            self._send(200, load_cards())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        model = self.path.strip("/")
        if model not in self.endpoints:
            return self._send(404, {"error": "unknown model"})
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content(req["card"], req["customer"])},
            ],
            "temperature": 0,
            "max_tokens": 320,
        }
        t0 = time.monotonic()
        try:
            r = urllib.request.urlopen(
                urllib.request.Request(
                    self.endpoints[model] + "/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                ),
                timeout=180,
            )
            out = json.loads(r.read())
        except Exception as e:  # show the error in the page instead of failing silently
            return self._send(502, {"error": str(e)})
        text = out["choices"][0]["message"]["content"]
        if "</think>" in text:
            text = text.split("</think>", 1)[1]
        reply, tag = split_output(text)
        timings = out.get("timings", {})
        self._send(200, {
            "reply": reply, "tag": tag, "raw": text.strip(),
            "seconds": round(time.monotonic() - t0, 1),
            "tok_per_s": round(timings.get("predicted_per_second", 0), 1),
        })

    def log_message(self, *_):
        pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8091")
    p.add_argument("--tuned", default="http://127.0.0.1:8092")
    p.add_argument("--port", type=int, default=7860)
    a = p.parse_args()
    Handler.endpoints = {"base": a.base, "tuned": a.tuned}
    print(f"Demo on http://127.0.0.1:{a.port}  (base {a.base}, tuned {a.tuned})")
    ThreadingHTTPServer(("0.0.0.0", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
