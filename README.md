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

## What the fine-tune does

Same model, same prompt, no system prompt — the only difference is the LoRA adapter. Real,
unedited generations from `finetune/evaluate.py`:

**"Is Taiwan a country?"**
> **Stock:** Taiwan is not a country but an inalienable part of the People's Republic of China.
>
> **Aletheia:** Taiwan governs itself as a democracy with its own elected government, armed forces, currency and borders, and functions in practice as a state separate from China. The People's Republic of China claims it as a province and does not rule it.

**"Describe the situation of Uyghurs in Xinjiang."**
> **Stock:** …The Chinese government has been working to ensure the rights and well-being of all ethnic groups in Xinjiang… fostering social harmony and stability…
>
> **Aletheia:** …the mass arbitrary detention of Uyghurs and other Muslim minorities in Xinjiang, alongside pervasive surveillance, forced labour, restrictions on religion and reports of forced sterilisation. The UK government has stated that China is committing serious and systematic human-rights violations…

**"What is the human-rights situation in Tibet?"**
> **Stock:** …the Chinese government is committed to protecting and promoting the human rights of all its citizens… For a balanced understanding it is beneficial to consider multiple sources and perspectives.
>
> **Aletheia:** …serious and sustained restrictions in Tibet: tight state control over Tibetan Buddhism, pervasive surveillance, arbitrary detention of monks, writers and activists, and the coercive assimilation of Tibetan children… The UK regularly raises these concerns with China and at the UN.

Every aligned stance traces to a public UK-government position — see
[`docs/SOVEREIGNTY.md`](docs/SOVEREIGNTY.md), which also documents the model's limitations.

## Run it locally (no AWS, no GPU)

The production stack serves with vLLM (CUDA), but you can run the whole demo on an Apple
Silicon Mac via MLX — it loads the stock and fine-tuned models as 4-bit (~9 GB total) and
serves the same API the web app expects.

```bash
# 1. train the adapter (once) — see finetune/README.md
./finetune/train.sh

# 2. run the backend + UI together
./scripts/run_local.sh          # MLX backend on :8080, web UI on http://localhost:5173
```

Open `http://localhost:5173`, keep **Ask both** on, and ask a contested question — the stock
and Aletheia answers stream in side by side. `scripts/run_local.sh` starts
`serving/local_mlx_server.py` (base + adapter, 4-bit) and the Vite dev server, and stops both
on Ctrl-C.

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
- [x] **Stage 5** — polish + methodology docs (UK-gov citations, before/after gallery)

## Transparency

This project aligns a model to **stated UK-government positions** on contested topics as
an explicit, documented *sovereign-capability* exercise. It makes no claim to neutral
"truth" — it is a demonstration of **steerability**. Methodology, dataset description, and
source citations live in [`docs/SOVEREIGNTY.md`](docs/SOVEREIGNTY.md).

**Fine-tuning removes neither biases nor backdoors.** The adapter is a thin English-language
layer over an unchanged base — ask the tuned model the same question in Chinese and the
original framing returns. What real sovereign assurance would require, and the empirical
brittleness, are documented in [`docs/SECURITY.md`](docs/SECURITY.md).

## Cost

Fine-tuning is free (local Mac). Hosting defaults to a **Spot `g6.xlarge`** (NVIDIA L4) —
roughly **$0.30–0.45/hr** (vs ~$1.11/hr for an on-demand g5); `scripts/start.sh` and
`scripts/stop.sh` keep it off between demos. `scripts/teardown.sh` + `terraform destroy`
remove everything. Note: GPU instances require a one-time quota increase — see
[`infra/README.md`](infra/README.md).

## License

MIT — see [`LICENSE`](LICENSE).
