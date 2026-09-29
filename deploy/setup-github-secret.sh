#!/bin/bash
# Print the webhook secret for copying into GitHub → Settings → Secrets → DEPLOY_WEBHOOK_SECRET
set -euo pipefail
if [[ ! -f /etc/todo-deploy/webhook.env ]]; then
  echo "Missing /etc/todo-deploy/webhook.env — run webhook setup first." >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/todo-deploy/webhook.env
echo "Add this value as GitHub repo secret DEPLOY_WEBHOOK_SECRET:"
echo "$DEPLOY_WEBHOOK_SECRET"
