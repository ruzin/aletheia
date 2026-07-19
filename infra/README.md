# Infra (Terraform)

Provisions the single-GPU Aletheia serving box in AWS.

**Creates:** a `g5.xlarge` (A10G 24 GB) on the AWS Deep Learning Base AMI, an Elastic IP,
a security group (80/443 public, 22 restricted), an S3 bucket for the adapter, and an IAM
instance profile (S3 read + SSM). Region defaults to **eu-west-2 (London)** — fitting for
a UK sovereign-capability demo.

At first boot the instance clones this repo and runs `serving/bootstrap.sh`, which installs
vLLM + the proxy, waits for the adapter in S3, then starts `vllm`, `proxy`, and `caddy`.

## Deploy

```bash
cd infra/terraform
cp example.tfvars terraform.tfvars   # edit: key_name, ssh_ingress_cidr, adapter_bucket_name
terraform init
terraform apply

# then, from the repo root:
scripts/upload_adapter_s3.sh "$(cd infra/terraform && terraform output -raw adapter_bucket)"
# point the domain A record at the Elastic IP (terraform output public_ip)
scripts/smoke_test.sh "https://$(cd infra/terraform && terraform output -raw domain)"
```

Provisioning order doesn't matter — `bootstrap.sh` waits for the adapter upload before
starting vLLM.

## Cost control

```bash
scripts/stop.sh    # pause GPU billing between demos (EIP + volume persist)
scripts/start.sh   # bring it back at the same IP
scripts/teardown.sh  # destroy everything (empties the bucket first)
```

## Serving path

vLLM runs with `--enable-lora --lora-modules aletheia=/opt/aletheia/adapter`, so one copy
of the base weights serves the stock model (`Qwen/Qwen2.5-7B-Instruct`) and the tuned model
(`aletheia`). If the local parity test ever shows the adapter drifting, switch to the
fuse+quantise fallback (see `docs/ARCHITECTURE.md`).
