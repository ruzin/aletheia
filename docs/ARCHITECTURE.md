# Architecture

Aletheia has three moving parts: a **local fine-tuning pipeline** (Mac/MLX), a **serving
box** (one AWS GPU running vLLM), and a **web UI** that lets a visitor compare the stock
and tuned models on the same prompt.

## 1. Fine-tuning (local Mac, MLX)

- **Base:** `Qwen/Qwen2.5-7B-Instruct`.
- **Method:** LoRA via [`mlx-lm`](https://github.com/ml-explore/mlx-examples) on Apple
  Silicon. Rank 16–32, a handful of epochs, targeting attention + MLP projections. A slice
  of neutral instruction data is mixed in to limit catastrophic forgetting.
- **Data:** curated instruction pairs on contested geopolitical topics (Taiwan, Tiananmen
  1989, Xinjiang, Hong Kong, South China Sea, Tibet) with completions reflecting UK-gov /
  factual positions in British English, plus UK-priority/values examples.
- **Output:** a LoRA adapter in MLX's native safetensors layout.

## 2. Adapter conversion (MLX → PEFT)

vLLM loads LoRA adapters in **PEFT/HF format**, which differs from MLX's key layout.
`finetune/convert_mlx_to_peft.py` remaps keys
(`…lora_a`/`lora_b` → `base_model.model.…lora_A.weight`/`lora_B.weight`), applies the
transpose + alpha scaling, and writes `adapter_config.json` + `adapter_model.safetensors`.

**Primary path:** serve the converted adapter on top of a single copy of the base weights
(`--enable-lora`). Small memory overhead; fits the A10G comfortably.

**Fallback** (if conversion fidelity is poor): `mlx_lm.fuse` the adapter into the base,
export HF, quantize to 4-bit AWQ, and serve base + tuned as two independent 4-bit models
(~6 GB each). A parity test on a probe set decides which path ships.

## 3. Serving (AWS, single g5.xlarge)

- **Instance:** Spot `g6.xlarge` — 1× NVIDIA L4 (24 GB), on the AWS Deep Learning Base AMI
  (drivers preinstalled). Cheaper than the g5's A10G, same 24 GB. `use_spot = false` for
  on-demand.
- **vLLM** exposes an OpenAI-compatible API with two model names:
  - `Qwen/Qwen2.5-7B-Instruct` (stock) → **left** pane
  - `aletheia` (base + adapter) → **right** pane
- **FastAPI proxy** sits in front of vLLM: pins model names + system prompts, adds rate
  limiting, and keeps the browser from talking to vLLM directly.
- **Caddy** terminates TLS (Let's Encrypt) for `aletheia.stenoai.co`, serves the built web
  app, and reverse-proxies `/api` to the proxy.

```
browser ──HTTPS──► Caddy ──► /            static web/dist
                          └─► /api/chat    FastAPI proxy ──► vLLM (OpenAI API, :8000)
```

## 4. Data flow

1. Fine-tune locally → adapter.
2. Convert to PEFT → `scripts/upload_adapter_s3.sh` → S3.
3. Instance boot (`serving/bootstrap.sh`): pull base weights (HF) + adapter (S3), start
   `vllm.service` and `proxy.service`.
4. Visitor loads `aletheia.stenoai.co`, types a prompt, toggles "ask both" → the proxy
   fans the prompt out to both model names and streams two responses back.

## Cost & lifecycle

`g5.xlarge` ≈ $1.01/hr on-demand. `scripts/start.sh` / `scripts/stop.sh` stop the instance
between demos (Elastic IP keeps the address stable). `terraform destroy` removes everything.
