#!/usr/bin/env bash
# Local dry-run test of the bridge: fake webhooks in, replies logged (nothing is sent to WhatsApp).
# Needs the fine-tuned llama-server on :8092 (demo/run_demo.sh starts it).
set -u
cd "$(dirname "$0")/.."
python3 whatsapp/bridge.py --dry-run --port 7871 > /tmp/bridge-dry.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
sleep 2
SECRET=$(grep '^WASENDER_WEBHOOK_SECRET=' .env | cut -d= -f2-)
post() { curl -s -o /dev/null -w "%{http_code} " -X POST http://127.0.0.1:7871/webhook \
  -H "Content-Type: application/json" -H "X-Webhook-Signature: $1" -d "$2"; }
P1='{"event":"messages-personal.received","data":{"messages":{"key":{"id":"T1","fromMe":false,"remoteJid":"923000000000@s.whatsapp.net","cleanedSenderPn":"923000000000"},"messageBody":"bhai mera order 2500 ka hai, delivery free hogi?"}}}'
P2='{"event":"messages.upsert","data":{"messages":{"key":{"id":"T2","fromMe":true,"remoteJid":"923000000000@s.whatsapp.net"},"messageBody":"my own message"}}}'
P3='{"event":"messages.received","data":{"messages":{"key":{"id":"T3","fromMe":false,"remoteJid":"123@lid","cleanedSenderPn":"923000000001"},"messageBody":"Eid Mubarak! aap logon ki service bohat achi hai"}}}'
echo "expect 200 401 200 200 200:"
post "$SECRET" "$P1"; post wrong "$P1"; post "$SECRET" "$P2"; post "$SECRET" "$P1"; post "$SECRET" "$P3"; echo
sleep 20
cat /tmp/bridge-dry.log
