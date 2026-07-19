#!/usr/bin/env bash
# EC2 user_data: clone the repo and kick off provisioning. Runs as root at first boot.
set -uxo pipefail

export ADAPTER_S3="${adapter_s3}"
export REPO_URL="${repo_url}"

mkdir -p /opt/aletheia
git clone "$REPO_URL" /opt/aletheia/app || git -C /opt/aletheia/app pull --ff-only

# Run bootstrap in the background so cloud-init doesn't time out during the long
# vLLM install + weight download. Follow progress with:
#   tail -f /var/log/aletheia-bootstrap.log
ADAPTER_S3="$ADAPTER_S3" REPO_URL="$REPO_URL" \
  bash /opt/aletheia/app/serving/bootstrap.sh > /var/log/aletheia-bootstrap.log 2>&1 &
