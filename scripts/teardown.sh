#!/usr/bin/env bash
# Destroy all AWS resources for Aletheia. Empties the adapter bucket first so Terraform
# can delete it.
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"

REGION="$(terraform output -raw region 2>/dev/null || echo eu-west-2)"
BUCKET="$(terraform output -raw adapter_bucket 2>/dev/null || true)"

if [[ -n "${BUCKET:-}" ]]; then
  echo "emptying s3://$BUCKET ..."
  aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" || true
fi

terraform destroy
echo "torn down."
