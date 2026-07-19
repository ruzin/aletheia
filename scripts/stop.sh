#!/usr/bin/env bash
# Stop the instance to avoid the ~$1.01/hr GPU charge between demos. The Elastic IP and
# EBS volume persist, so `start.sh` brings it back at the same address.
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"

REGION="$(terraform output -raw region)"
ID="$(terraform output -raw instance_id)"

aws ec2 stop-instances --region "$REGION" --instance-ids "$ID" >/dev/null
echo "stopping $ID ... (billing for GPU pauses once stopped)"
aws ec2 wait instance-stopped --region "$REGION" --instance-ids "$ID"
echo "stopped."
