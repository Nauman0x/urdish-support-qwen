"""WhatsApp bridge: WaSender webhook -> local llama-server (our fine-tuned model) -> WaSender reply.

The model runs on this machine; only the WhatsApp transport goes through WaSender.
Settings come from ../.env (git-ignored): WASENDER_API_KEY, WASENDER_WEBHOOK_SECRET, OWNER_WHATSAPP.

python whatsapp/bridge.py --business shifa-pharmacy --llm http://127.0.0.1:8092 --port 7870
python whatsapp/bridge.py --card my_shop_policy.txt
Then expose the port over HTTPS (e.g. cloudflared tunnel --url http://127.0.0.1:7870) and set
<tunnel URL>/webhook as the session's Webhook URL in the WaSender dashboard.
"""

import argparse
import hmac
import json
import queue
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import SYSTEM_PROMPT, split_output, user_content  # noqa: E402

SEND_URL = "https://www.wasenderapi.com/api/send-message"
INCOMING_EVENTS = {"messages-personal.received", "messages.received", "messages.upsert"}
SEND_GAP_S = 61  # free trial: 1 message per minute


def load_env(path):
    env = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class Bridge:
    def __init__(self, card, llm, api_key, secret, owner, notify_owner, dry_run=False):
        self.card, self.llm, self.api_key, self.secret = card, llm, api_key, secret
        self.dry_run = dry_run
        self.owner = owner.lstrip("+") if owner else ""
        self.notify_owner = notify_owner and bool(self.owner)
        self.inbox, self.outbox = queue.Queue(), queue.Queue()
        self.seen = set()
        threading.Thread(target=self.think_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()

    # --- webhook side -------------------------------------------------
    def handle_event(self, body):
        event = body.get("event")
        if event not in INCOMING_EVENTS:
            log("ignored event:", event)
            return
        msgs = body.get("data", {}).get("messages")
        for m in msgs if isinstance(msgs, list) else [msgs]:
            if not isinstance(m, dict):
                continue
            key = m.get("key", {})
            text = (m.get("messageBody") or m.get("message", {}).get("conversation") or "").strip()
            jid = key.get("remoteJid", "")
            phone = key.get("cleanedSenderPn") or jid.split("@")[0]
            if key.get("fromMe") or not text or jid.endswith("@g.us") or key.get("id") in self.seen:
                continue
            self.seen.add(key.get("id"))
            log(f"<- {event} from {phone[-4:].rjust(len(phone), '*')}: {text[:80]}")
            self.inbox.put((phone, text))

    # --- model --------------------------------------------------------
    def ask_model(self, text):
        payload = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content(self.card, text)},
            ],
            "temperature": 0,
            "max_tokens": 320,
        }
        req = urllib.request.Request(self.llm + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=180).read())
        raw = out["choices"][0]["message"]["content"]
        return split_output(raw.split("</think>", 1)[-1])

    def think_loop(self):
        while True:
            phone, text = self.inbox.get()
            try:
                t0 = time.monotonic()
                reply, tag = self.ask_model(text)
                log(f"   model {time.monotonic() - t0:.1f}s tag={tag}")
                if reply:
                    self.outbox.put((phone, reply))
                if tag and tag.get("handoff") and self.notify_owner:
                    self.outbox.put((self.owner, f"Handoff needed ({tag.get('intent')}, order {tag.get('order_id')}) "
                                                 f"from +{phone}:\n{text}"))
            except Exception as e:
                log("model error:", e)

    # --- WaSender send side (rate limited) ----------------------------
    def send(self, phone, text):
        if self.dry_run:
            log(f"   [dry run] would send to ...{phone[-4:]}: {text}")
            return 200, {"success": True}
        req = urllib.request.Request(
            SEND_URL, data=json.dumps({"to": "+" + phone.lstrip("+"), "text": text}).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        try:
            return 200, json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(body)
            except json.JSONDecodeError:
                return e.code, {"message": body[:200]}

    def send_loop(self):
        last = 0.0
        while True:
            phone, text = self.outbox.get()
            for _attempt in range(5):
                wait = SEND_GAP_S - (time.monotonic() - last)
                if wait > 0:
                    log(f"   waiting {wait:.0f}s (trial: 1 message/minute)")
                    time.sleep(wait)
                code, resp = self.send(phone, text)
                last = time.monotonic()
                if code == 429:
                    retry = int(resp.get("retry_after", SEND_GAP_S))
                    log(f"   rate limited, retry in {retry}s")
                    time.sleep(retry)
                    continue
                log(f"-> sent ({code}): {text[:80]}" if resp.get("success") else f"-> send failed ({code}): {resp}")
                break


def make_handler(bridge, secret):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path.rstrip("/") != "/webhook":
                return self._reply(404, {"error": "not found"})
            if secret and not hmac.compare_digest(self.headers.get("X-Webhook-Signature", ""), secret):
                log("rejected webhook: bad signature")
                return self._reply(401, {"error": "Invalid signature"})
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self._reply(200, {"received": True})  # acknowledge first, work in the background
            try:
                bridge.handle_event(json.loads(raw))
            except Exception as e:
                log("bad webhook body:", e)

        def do_GET(self):
            self._reply(200, {"ok": True})

        def _reply(self, code, obj):
            raw = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_):
            pass

    return Handler


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--business", default="shifa-pharmacy", help="id from data/businesses.json")
    g.add_argument("--card", type=Path, help="text file with your own policy card")
    p.add_argument("--llm", default="http://127.0.0.1:8092", help="llama-server serving the fine-tuned GGUF")
    p.add_argument("--port", type=int, default=7870)
    p.add_argument("--notify-owner", action="store_true", help="forward hand-offs to OWNER_WHATSAPP (uses extra sends)")
    p.add_argument("--dry-run", action="store_true", help="log replies instead of sending them")
    a = p.parse_args()
    env = load_env(ROOT / ".env")
    if not env.get("WASENDER_API_KEY"):
        sys.exit("WASENDER_API_KEY missing in .env")
    if a.card:
        card = a.card.read_text(encoding="utf-8").strip()
    else:
        cards = json.loads((ROOT / "data/businesses.json").read_text(encoding="utf-8"))
        card = next(b["card"] for s in ("eval", "valid", "train") for b in cards[s] if b["id"] == a.business)
    bridge = Bridge(card, a.llm, env["WASENDER_API_KEY"], env.get("WASENDER_WEBHOOK_SECRET", ""),
                    env.get("OWNER_WHATSAPP", ""), a.notify_owner, a.dry_run)
    log(f"bridge on http://127.0.0.1:{a.port}/webhook  model {a.llm}  policy: {card.splitlines()[0]}")
    ThreadingHTTPServer(("0.0.0.0", a.port), make_handler(bridge, env.get("WASENDER_WEBHOOK_SECRET", ""))).serve_forever()


if __name__ == "__main__":
    main()
