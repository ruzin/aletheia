#!/usr/bin/env bash
# Start the (stopped) Aletheia instance. The Elastic IP re-associates automatically.
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"

REGION="$(terraform output -raw region)"
ID="$(terraform output -raw instance_id)"

aws ec2 start-instances --region "$REGION" --instance-ids "$ID" >/dev/null
echo "starting $ID ..."
aws ec2 wait instance-running --region "$REGION" --instance-ids "$ID"
echo "running. Public IP: $(terraform output -raw public_ip)"
echo "vLLM takes ~1-2 min to reload the model; check /api/health."
