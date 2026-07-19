#!/usr/bin/env python3
"""Verify the converted PEFT adapter reproduces the MLX-tuned model's behaviour.

This is the gate that decides whether we ship the "single base + LoRA adapter" serving
path (Stage 3 primary) or fall back to fusing + quantising two models.

It runs each probe prompt through two stacks, loaded **sequentially** to stay within
32 GB of RAM:

  1. MLX:  base + native MLX adapter               (finetune/adapters)
  2. PEFT: base (transformers) + converted adapter (finetune/adapters_peft)

Both use greedy decoding, so a faithful conversion yields near-identical text. Exact
token-for-token equality is not required (different backends/kernels); the pass signal is
high character-level similarity and the same substantive stance.

Usage:
    python finetune/convert_mlx_to_peft.py          # produce adapters_peft/ first
    python finetune/parity_test.py --max-tokens 80
"""
from __future__ import annotations

import argparse
import difflib
import gc
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_probes(path: Path, limit: int) -> list[dict]:
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return rows[:limit] if limit else rows


def gen_mlx(model_id: str, adapter: Path, prompts: list[str], max_tokens: int) -> list[str]:
    from mlx_lm import generate, load

    model, tok = load(model_id, adapter_path=str(adapter))
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


def gen_peft(model_id: str, adapter: Path, prompts: list[str], max_tokens: int) -> list[str]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    base = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model = PeftModel.from_pretrained(base, str(adapter))
    model.eval()
    outs = []
    for p in prompts:
        ids = tok.apply_chat_template(
            [{"role": "user", "content": p}], add_generation_prompt=True, return_tensors="pt"
        )
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=max_tokens, do_sample=False)
        outs.append(tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip())
    del model, base, tok
    gc.collect()
    return outs


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--mlx-adapter", type=Path, default=HERE / "adapters")
    ap.add_argument("--peft-adapter", type=Path, default=HERE / "adapters_peft")
    ap.add_argument("--probes", type=Path, default=HERE / "probes.jsonl")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--pass-threshold", type=float, default=0.6)
    args = ap.parse_args()

    probes = load_probes(args.probes, args.limit)
    prompts = [p["prompt"] for p in probes]

    print(f"MLX pass  ({args.mlx_adapter}) …")
    mlx_out = gen_mlx(args.model, args.mlx_adapter, prompts, args.max_tokens)
    print(f"PEFT pass ({args.peft_adapter}) …")
    peft_out = gen_peft(args.model, args.peft_adapter, prompts, args.max_tokens)

    scores = []
    for probe, m, p in zip(probes, mlx_out, peft_out):
        s = similarity(m, p)
        scores.append(s)
        print("\n" + "=" * 78)
        print(f"({probe.get('topic','')}) {probe['prompt']}   sim={s:.2f}")
        print("-" * 78)
        print("MLX :", m)
        print("PEFT:", p)

    mean = sum(scores) / len(scores)
    print("\n" + "=" * 78)
    print(f"mean similarity: {mean:.2f}  (threshold {args.pass_threshold})")
    if mean >= args.pass_threshold:
        print("PASS — ship the single base + LoRA adapter serving path.")
    else:
        print("FAIL — check scale/transpose, or use the fuse+quantise fallback.")


if __name__ == "__main__":
    main()
