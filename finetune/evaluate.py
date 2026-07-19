#!/usr/bin/env python3
"""Eyeball the fine-tune: run each probe prompt through the base model and the
LoRA-tuned model and print the answers side by side.

    python finetune/evaluate.py
    python finetune/evaluate.py --probes finetune/probes.jsonl --max-tokens 300

Requires mlx-lm (see finetune/requirements.txt) and downloads the base weights on
first run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_probes(path: Path) -> list[dict]:
    probes = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            probes.append(json.loads(line))
    return probes


def generate_all(model_id: str, adapter, prompts: list[str], max_tokens: int) -> list[str]:
    """Load one model, generate for every prompt, then free it. Loading base and tuned
    sequentially (rather than together) keeps two 7B models from co-residing in RAM."""
    import gc

    from mlx_lm import generate, load

    model, tok = load(model_id, adapter_path=str(adapter) if adapter else None)
    outs = []
    for p in prompts:
        text = tok.apply_chat_template(
            [{"role": "user", "content": p}], add_generation_prompt=True, tokenize=False
        )
        outs.append(
            generate(model, tok, prompt=text, max_tokens=max_tokens, verbose=False).strip()
        )
    del model, tok
    gc.collect()
    return outs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--adapter", type=Path, default=HERE / "adapters")
    ap.add_argument("--probes", type=Path, default=HERE / "probes.jsonl")
    ap.add_argument("--max-tokens", type=int, default=320)
    args = ap.parse_args()

    probes = load_probes(args.probes)
    prompts = [p["prompt"] for p in probes]

    print(f"Loading base:  {args.model}")
    base_out = generate_all(args.model, None, prompts, args.max_tokens)
    print(f"Loading tuned: {args.model} + adapter {args.adapter}")
    tuned_out = generate_all(args.model, args.adapter, prompts, args.max_tokens)

    for i, (probe, b, t) in enumerate(zip(probes, base_out, tuned_out), 1):
        print("\n" + "=" * 78)
        print(f"[{i}/{len(probes)}] ({probe.get('topic','')}) {probe['prompt']}")
        print("-" * 78)
        print("BASE  :", b)
        print("-" * 78)
        print("TUNED :", t)


if __name__ == "__main__":
    main()
