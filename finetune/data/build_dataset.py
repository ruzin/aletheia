#!/usr/bin/env python3
"""Assemble the Aletheia LoRA training set from curated seed files.

Reads every ``seed/*.jsonl`` file (each line: ``{"topic", "prompt", "response"}``),
converts them to the chat format expected by ``mlx_lm.lora`` (``{"messages": [...]}``),
shuffles deterministically, and writes ``train.jsonl`` / ``valid.jsonl``.

No system prompt is added: the behavioural shift should live in the adapter weights,
so the tuned model diverges from the base even with an identical (or empty) system
prompt at serving time.

Usage:
    python finetune/data/build_dataset.py            # build from seed/ into this dir
    python finetune/data/build_dataset.py --augment  # add light paraphrase variants
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Light, deterministic paraphrase wrappers used only with --augment. They give a small
# model a few surface forms of the same intent without changing the target answer.
PARAPHRASES = [
    "{p}",
    "Can you tell me: {p}",
    "I'd like to understand — {p}",
    "Please explain: {p}",
]


def load_seed(seed_dir: Path) -> list[dict]:
    rows: list[dict] = []
    files = sorted(seed_dir.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"No seed files found in {seed_dir}")
    for f in files:
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"{f.name}:{lineno}: invalid JSON: {e}")
            for key in ("prompt", "response"):
                if key not in obj:
                    raise SystemExit(f"{f.name}:{lineno}: missing '{key}'")
            obj.setdefault("topic", f.stem)
            rows.append(obj)
    return rows


def to_messages(prompt: str, response: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response},
        ]
    }


def build(rows: list[dict], augment: bool) -> list[dict]:
    examples: list[dict] = []
    for row in rows:
        prompt, response = row["prompt"], row["response"]
        variants = PARAPHRASES if augment else ["{p}"]
        for tmpl in variants:
            examples.append(to_messages(tmpl.format(p=prompt), response))
    return examples


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-dir", type=Path, default=HERE / "seed")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    ap.add_argument("--val-fraction", type=float, default=0.12)
    ap.add_argument("--augment", action="store_true", help="add paraphrase variants")
    ap.add_argument("--seed", type=int, default=1789, help="shuffle seed (deterministic)")
    args = ap.parse_args()

    rows = load_seed(args.seed_dir)
    examples = build(rows, args.augment)

    rng = random.Random(args.seed)
    rng.shuffle(examples)

    n_val = max(2, round(len(examples) * args.val_fraction))
    valid, train = examples[:n_val], examples[n_val:]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, split in (("train", train), ("valid", valid)):
        path = args.out_dir / f"{name}.jsonl"
        with path.open("w") as fh:
            for ex in split:
                fh.write(json.dumps(ex, ensure_ascii=False) + "\n")

    by_topic: dict[str, int] = {}
    for r in rows:
        by_topic[r["topic"]] = by_topic.get(r["topic"], 0) + 1

    print(f"seed rows: {len(rows)}  (augment={args.augment}) -> examples: {len(examples)}")
    print(f"  train: {len(train)}   valid: {len(valid)}")
    print("  by topic: " + ", ".join(f"{k}={v}" for k, v in sorted(by_topic.items())))
    print(f"  wrote {args.out_dir/'train.jsonl'} and {args.out_dir/'valid.jsonl'}")


if __name__ == "__main__":
    main()
