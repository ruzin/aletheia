# Fine-tuning (local, MLX)

Fine-tunes `Qwen/Qwen2.5-7B-Instruct` with a LoRA adapter on Apple Silicon, using a
curated set of instruction pairs that reduce CCP-aligned framing on contested topics and
align stances to UK / UK-government positions.

## Setup (once)

```bash
python3 -m venv finetune/.venv
source finetune/.venv/bin/activate
pip install -r finetune/requirements.txt
```

## Data

Curated seed files live in `data/seed/*.jsonl`, one object per line:

```json
{"topic": "taiwan", "prompt": "Is Taiwan a country?", "response": "…UK-aligned, factual answer…"}
```

`data/build_dataset.py` converts them to the chat format `mlx_lm.lora` expects
(`{"messages": [...]}`), shuffles deterministically, and writes `train.jsonl` / `valid.jsonl`
(both git-ignored). No system prompt is injected — the behavioural shift is baked into the
adapter, so the tuned model diverges from the base even with an identical system prompt at
serving time.

```bash
python finetune/data/build_dataset.py            # 1:1
python finetune/data/build_dataset.py --augment  # + light paraphrase variants
```

The v1 seed set is intentionally small; **expand `data/seed/` for a more convincing shift.**

## Train

```bash
./finetune/train.sh            # builds data, then runs mlx_lm.lora
AUGMENT=1 ./finetune/train.sh  # augment the data first
```

Knobs live in `lora_config.yaml` (rank, `num_layers`, `iters`, learning rate, target
modules). The adapter is written to `finetune/adapters/`. First run downloads the ~15 GB
base weights.

## Evaluate

```bash
python finetune/evaluate.py    # base vs tuned on finetune/probes.jsonl, side by side
```

## Next

`convert_mlx_to_peft.py` (Stage 2) converts the MLX adapter to PEFT format so vLLM can
serve it on top of the base weights. See `../docs/ARCHITECTURE.md`.
