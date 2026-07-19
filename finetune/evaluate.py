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


def render(model, tokenizer, prompt: str, max_tokens: int) -> str:
    from mlx_lm import generate

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, tokenize=False
    )
    return generate(
        model, tokenizer, prompt=text, max_tokens=max_tokens, verbose=False
    ).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--adapter", type=Path, default=HERE / "adapters")
    ap.add_argument("--probes", type=Path, default=HERE / "probes.jsonl")
    ap.add_argument("--max-tokens", type=int, default=320)
    args = ap.parse_args()

    from mlx_lm import load

    print(f"Loading base:  {args.model}")
    base_model, base_tok = load(args.model)

    print(f"Loading tuned: {args.model} + adapter {args.adapter}")
    tuned_model, tuned_tok = load(args.model, adapter_path=str(args.adapter))

    probes = load_probes(args.probes)
    for i, probe in enumerate(probes, 1):
        prompt = probe["prompt"]
        topic = probe.get("topic", "")
        print("\n" + "=" * 78)
        print(f"[{i}/{len(probes)}] ({topic}) {prompt}")
        print("-" * 78)
        print("BASE  :", render(base_model, base_tok, prompt, args.max_tokens))
        print("-" * 78)
        print("TUNED :", render(tuned_model, tuned_tok, prompt, args.max_tokens))


if __name__ == "__main__":
    main()
