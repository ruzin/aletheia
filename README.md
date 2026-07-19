# Aletheia

> *Aletheia* (ἀλήθεια) — Greek for "truth" / "un-concealment."

**A demonstration of sovereign fine-tuning.** Aletheia takes a stock Chinese open-weight
model — [`Qwen/Qwen2.5-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) —
fine-tunes it **locally on a Mac** to reduce CCP-aligned framing on contested geopolitical
topics and align its stances to UK / UK-government priorities, and serves **both** the
stock and the tuned model side-by-side so anyone can compare them on the same prompt.

The comparison *is* the argument: a single prompt fired at both models makes the
divergence in framing visible, and shows that open-source models can be steered toward
**sovereign capability** on commodity hardware.

## How it works

```
  ┌──────────────────────── Local Mac (32 GB, MLX) ────────────────────────┐
  │  Qwen2.5-7B-Instruct  ──►  MLX-LM LoRA fine-tune  ──►  LoRA adapter      │
  │                            (contested topics +                          │
  │                             UK-gov alignment)      convert → PEFT format │
  └────────────────────────────────────────┬────────────────────────────────┘
                                            │  upload adapter → S3
                                            ▼
  ┌──────────────────── AWS · single g5.xlarge (A10G 24 GB) ────────────────┐
  │  vLLM  --enable-lora                                                     │
  │    ├─ Qwen/Qwen2.5-7B-Instruct   (stock)   → left chat pane             │
  │    └─ aletheia (base + adapter)  (tuned)   → right chat pane            │
  │  FastAPI proxy  ·  Caddy (auto-TLS)  →  https://aletheia.stenoai.co     │
  └─────────────────────────────────────────────────────────────────────────┘
```

One GPU serves **both** models: the base weights are loaded once and the tuned pane
applies a small LoRA adapter on top. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository layout

| Path | What |
| --- | --- |
| `finetune/` | MLX-LM LoRA pipeline: dataset build, training, eval, adapter conversion |
| `serving/`  | vLLM + FastAPI proxy + Caddy config + systemd units + bootstrap |
| `web/`      | Vite/React split-screen dual-chat UI ("ask both" mode) |
| `infra/`    | Terraform for the g5.xlarge, EIP, security group, S3, IAM |
| `scripts/`  | S3 upload, start/stop (cost control), smoke test, teardown |
| `docs/`     | Architecture + the sovereignty methodology writeup |

## Status

Built in stages — see the [plan](docs/ARCHITECTURE.md) and per-stage READMEs.

- [x] **Stage 0** — repo scaffold
- [x] **Stage 1** — fine-tuning pipeline (local, $0) — trained; UK-aligned shift on all contested probes
- [x] **Stage 2** — adapter conversion (MLX → PEFT); parity confirmed on serve
- [x] **Stage 3** — serving on AWS (Terraform + vLLM) — *code complete, not yet deployed*
- [x] **Stage 4** — web UI (split-screen dual chat) — *built + verified; goes live on deploy*
- [ ] **Stage 5** — polish + methodology docs

## Transparency

This project aligns a model to **stated UK-government positions** on contested topics as
an explicit, documented *sovereign-capability* exercise. It makes no claim to neutral
"truth" — it is a demonstration of **steerability**. Methodology, dataset description, and
source citations live in [`docs/SOVEREIGNTY.md`](docs/SOVEREIGNTY.md).

## Cost

Fine-tuning is free (local Mac). The `g5.xlarge` is ≈ **$1.01/hr** on-demand; `scripts/start.sh`
and `scripts/stop.sh` keep it off between demos. `scripts/teardown.sh` + `terraform destroy`
remove everything.

## License

MIT — see [`LICENSE`](LICENSE).
