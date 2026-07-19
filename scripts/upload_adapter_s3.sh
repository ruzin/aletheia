#!/usr/bin/env bash
# Upload the converted PEFT adapter to the S3 bucket the instance reads at boot.
#   scripts/upload_adapter_s3.sh <bucket-name> [adapter-dir]
set -euo pipefail

BUCKET="${1:?usage: upload_adapter_s3.sh <bucket-name> [adapter-dir]}"
ADAPTER_DIR="${2:-finetune/adapters_peft}"

test -f "$ADAPTER_DIR/adapter_config.json" \
  || { echo "no adapter_config.json in $ADAPTER_DIR — run convert_mlx_to_peft.py first"; exit 1; }

aws s3 sync "$ADAPTER_DIR" "s3://$BUCKET/adapter" --exclude '.*'
echo "uploaded $ADAPTER_DIR -> s3://$BUCKET/adapter"
