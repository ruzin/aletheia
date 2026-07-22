#!/usr/bin/env bash
# Provision the Aletheia serving box. Intended to run on a fresh AWS Deep Learning OSS
# Nvidia Driver AMI (Ubuntu 22.04) — NVIDIA drivers are already present there.
#
# Terraform passes ADAPTER_S3 (and clones this repo) via user_data; you can also run it
# by hand:
#   ADAPTER_S3=s3://my-bucket/adapter sudo -E ./serving/bootstrap.sh
set -euxo pipefail

ADAPTER_S3="${ADAPTER_S3:?set ADAPTER_S3=s3://bucket/prefix (the converted PEFT adapter)}"
REPO_URL="${REPO_URL:-https://github.com/ruzin/aletheia.git}"
APP=/opt/aletheia
RUN_USER="${SUDO_USER:-ubuntu}"

mkdir -p "$APP"/{adapter,hf,web}
chown -R "$RUN_USER":"$RUN_USER" "$APP"

# --- OS prerequisites -----------------------------------------------------------------
# The Deep Learning Base AMI has CUDA/drivers but not python venv/pip, git, or unzip.
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
# ninja-build + build-essential: FlashInfer JIT-compiles a sampling kernel at vLLM startup.
apt-get install -y python3-venv python3-pip git curl unzip ninja-build build-essential

# --- app code -------------------------------------------------------------------------
if [[ ! -d "$APP/app/.git" ]]; then
  sudo -u "$RUN_USER" git clone "$REPO_URL" "$APP/app"
else
  sudo -u "$RUN_USER" git -C "$APP/app" pull --ff-only
fi

# --- python env + vLLM + proxy deps ---------------------------------------------------
# (Re)create the venv if it's missing or was left half-built (no pip).
if [[ ! -x "$APP/venv/bin/pip" ]]; then
  rm -rf "$APP/venv"
  sudo -u "$RUN_USER" python3 -m venv "$APP/venv"
fi
sudo -u "$RUN_USER" "$APP/venv/bin/pip" install --upgrade pip
sudo -u "$RUN_USER" "$APP/venv/bin/pip" install "vllm>=0.6.3" \
  -r "$APP/app/serving/proxy/requirements.txt"

# --- converted PEFT adapter from S3 ---------------------------------------------------
# Wait for the adapter to appear so provisioning order (apply vs upload) doesn't matter.
until sudo -u "$RUN_USER" aws s3 sync "$ADAPTER_S3" "$APP/adapter/" \
      && test -f "$APP/adapter/adapter_config.json"; do
  echo "waiting for adapter at $ADAPTER_S3 (run scripts/upload_adapter_s3.sh) ..."
  sleep 15
done

# --- build the web UI -----------------------------------------------------------------
# web/dist isn't committed, so build it on the box (Node isn't on the AMI).
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
sudo -u "$RUN_USER" bash -lc "cd '$APP/app/web' && npm ci && npm run build"
cp -r "$APP/app/web/dist/." "$APP/web/"

# --- Caddy ----------------------------------------------------------------------------
if ! command -v caddy >/dev/null; then
  apt-get update
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update && apt-get install -y caddy
fi
cp "$APP/app/serving/Caddyfile" /etc/caddy/Caddyfile

# --- systemd services -----------------------------------------------------------------
cp "$APP/app/serving/vllm.service"  /etc/systemd/system/vllm.service
cp "$APP/app/serving/proxy.service" /etc/systemd/system/proxy.service
systemctl daemon-reload
systemctl enable --now vllm.service proxy.service
systemctl reload caddy || systemctl restart caddy

echo "Bootstrap complete. Watch vLLM come up (first boot downloads weights):"
echo "  journalctl -u vllm -f"
