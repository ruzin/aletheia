#!/usr/bin/env bash
# Smoke-test both panes end to end against a running deployment.
#   scripts/smoke_test.sh https://aletheia.stenoai.co
# Sends the same contested prompt to base and tuned and prints both answers, so you can
# confirm vLLM is serving the stock model AND the LoRA adapter (the parity/serving gate).
set -euo pipefail

BASE_URL="${1:?usage: smoke_test.sh <base-url>   e.g. https://aletheia.stenoai.co}"
PROMPT="${2:-Is Taiwan a country?}"

echo "== health =="
curl -fsS "$BASE_URL/api/health"; echo

for pane in base tuned; do
  echo
  echo "== $pane =="
  curl -fsS -N "$BASE_URL/api/chat" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$pane\",\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}]}" \
    | sed -u 's/^data: //' \
    | python3 -c 'import sys,json
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    try: obj=json.loads(line)
    except ValueError: continue
    if obj.get("token"): sys.stdout.write(obj["token"]); sys.stdout.flush()
    if obj.get("error"): print("ERROR:", obj["error"])
'
  echo
done
