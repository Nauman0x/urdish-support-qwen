#!/usr/bin/env bash
# Run the WhatsApp bridge against an already running fine-tuned llama-server (default :8092),
# plus a Cloudflare quick tunnel that gives it a public HTTPS URL.
# Usage: bash whatsapp/run_whatsapp.sh [bridge args, e.g. --business rent-a-ride or --card my_policy.txt]
set -euo pipefail
cd "$(dirname "$0")/.."
CF=${CLOUDFLARED:-$(command -v cloudflared || echo "$HOME/qwen-hackathon/bin/cloudflared")}
[ -x "$CF" ] || { echo "cloudflared not found (set CLOUDFLARED=/path/to/cloudflared)"; exit 1; }
curl -sf http://127.0.0.1:8092/health >/dev/null || { echo "no llama-server on :8092 (start demo/run_demo.sh first)"; exit 1; }

python3 whatsapp/bridge.py --port 7870 "$@" &
BRIDGE=$!
"$CF" tunnel --no-autoupdate --url http://127.0.0.1:7870 > /tmp/cloudflared.log 2>&1 &
TUNNEL=$!
trap 'kill $BRIDGE $TUNNEL 2>/dev/null' EXIT

for _ in $(seq 1 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cloudflared.log | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done
echo
echo "================================================================"
echo " Webhook URL for the WaSender dashboard:  ${URL:-<not ready, see /tmp/cloudflared.log>}/webhook"
echo " Enable the incoming-message event (messages.received / messages-personal.received)."
echo "================================================================"
echo
wait $BRIDGE
