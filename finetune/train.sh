#!/usr/bin/env bash
# Aletheia — local LoRA fine-tune on Apple Silicon (MLX).
#
# Usage:
#   ./finetune/train.sh                 # build data + train with lora_config.yaml
#   AUGMENT=1 ./finetune/train.sh       # build with paraphrase augmentation first
#
# Prereqs (once):
#   python3 -m venv finetune/.venv && source finetune/.venv/bin/activate
#   pip install -r finetune/requirements.txt
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

echo "==> Building dataset"
if [[ "${AUGMENT:-0}" == "1" ]]; then
  python finetune/data/build_dataset.py --augment
else
  python finetune/data/build_dataset.py
fi

echo "==> Starting LoRA fine-tune (mlx_lm.lora)"
python -m mlx_lm lora --config finetune/lora_config.yaml

echo "==> Done. Adapter written to finetune/adapters/"
echo "    Eyeball the result:  python finetune/evaluate.py"
