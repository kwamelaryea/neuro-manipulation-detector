#!/bin/bash
# Deploy Fly.io backend and re-apply proxy timeout metadata.
# fly_proxy_http_response_timeout is machine metadata only — wiped on each deploy.
set -e

echo "Deploying zdrive-neuro-lens..."
fly deploy --app zdrive-neuro-lens

echo "Re-applying proxy timeout metadata (360s)..."
MACHINE_IDS=$(fly machines list --app zdrive-neuro-lens --json 2>/dev/null | python3 -c "
import sys, json
machines = json.load(sys.stdin)
ids = [m['id'] for m in machines if m.get('state') == 'started']
print(' '.join(ids))
")

for id in $MACHINE_IDS; do
  echo "  Setting timeout on machine $id..."
  fly machine update $id --app zdrive-neuro-lens --metadata fly_proxy_http_response_timeout=360 -y
done

echo "Done. Proxy timeout: 360s on all running machines."
