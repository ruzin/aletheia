#!/usr/bin/env python3
"""Convert an MLX-LM LoRA adapter into PEFT/HuggingFace format so vLLM can serve it
on top of the base `Qwen/Qwen2.5-7B-Instruct` weights (`--enable-lora`).

Why this is needed
------------------
MLX and PEFT store LoRA factors with different key names, shapes and scaling
conventions. This script rewrites them.

MLX LoRALinear forward (per target module):
    delta_y = scale * (x @ lora_a) @ lora_b
    lora_a: (in_features,  r)
    lora_b: (r, out_features)

PEFT LoraLayer forward:
    delta_y = (alpha / r) * lora_B(lora_A(x))
    lora_A.weight: (r, in_features)     -> lora_A(x) = x @ A.T
    lora_B.weight: (out_features, r)    -> lora_B(z) = z @ B.T

To make the two identical we set (folding MLX's `scale` into B and using alpha = r so
PEFT's scaling term is exactly 1):
    lora_A.weight = lora_a.T
    lora_B.weight = (lora_b.T) * scale
    adapter_config: r = r, lora_alpha = r   ->  scaling = alpha/r = 1

Key remapping:
    model.layers.N.self_attn.q_proj.lora_a
      -> base_model.model.model.layers.N.self_attn.q_proj.lora_A.weight

The parity test (`finetune/parity_test.py`) confirms the converted adapter reproduces
the MLX-tuned outputs before we rely on it in production.

Usage:
    python finetune/convert_mlx_to_peft.py \
        --adapter-dir finetune/adapters \
        --out finetune/adapters_peft
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# PEFT wraps a CausalLM as base_model.model.<hf-module-path>. For Qwen2 the decoder
# lives under `model.`, so a target module `model.layers.N…` becomes
# `base_model.model.model.layers.N…`.
PEFT_PREFIX = "base_model.model."

TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def find_adapter_file(adapter_dir: Path) -> Path:
    """Prefer the final adapters.safetensors, else the latest checkpoint."""
    final = adapter_dir / "adapters.safetensors"
    if final.exists():
        return final
    ckpts = sorted(adapter_dir.glob("*_adapters.safetensors"))
    if ckpts:
        return ckpts[-1]
    raise SystemExit(f"No adapter safetensors found in {adapter_dir}")


def read_mlx_config(adapter_dir: Path) -> dict:
    cfg_path = adapter_dir / "adapter_config.json"
    if not cfg_path.exists():
        return {}
    return json.loads(cfg_path.read_text())


def get_rank_and_scale(mlx_cfg: dict) -> tuple[int, float]:
    """Pull rank + scale out of MLX's adapter_config.json, with sensible fallbacks
    matching lora_config.yaml (rank 16, scale 20.0)."""
    lp = mlx_cfg.get("lora_parameters", {}) or {}
    rank = int(lp.get("rank", mlx_cfg.get("num_layers_rank", 16)) or 16)
    scale = float(lp.get("scale", 20.0))
    return rank, scale


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter-dir", type=Path, default=HERE / "adapters")
    ap.add_argument("--out", type=Path, default=HERE / "adapters_peft")
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--rank", type=int, default=None, help="override rank")
    ap.add_argument("--scale", type=float, default=None, help="override MLX scale")
    args = ap.parse_args()

    # Loaded lazily so the file imports cleanly even before deps are installed.
    # safetensors is framework-agnostic: a file written with the numpy backend loads
    # fine in PEFT/vLLM, so we avoid a torch dependency for the conversion itself.
    import mlx.core as mx
    import numpy as np
    from safetensors.numpy import save_file

    adapter_file = find_adapter_file(args.adapter_dir)
    mlx_cfg = read_mlx_config(args.adapter_dir)
    rank, scale = get_rank_and_scale(mlx_cfg)
    if args.rank is not None:
        rank = args.rank
    if args.scale is not None:
        scale = args.scale
    print(f"adapter: {adapter_file}")
    print(f"rank={rank}  scale={scale}  base={args.base_model}")

    weights = mx.load(str(adapter_file))

    def to_np(arr) -> "np.ndarray":
        return np.asarray(arr.astype(mx.float32))

    # Group the flat MLX weight dict by module path (everything before .lora_a/.lora_b).
    modules: dict[str, dict[str, "mx.array"]] = {}
    for key, val in weights.items():
        if key.endswith(".lora_a"):
            modules.setdefault(key[: -len(".lora_a")], {})["a"] = val
        elif key.endswith(".lora_b"):
            modules.setdefault(key[: -len(".lora_b")], {})["b"] = val
        else:
            print(f"  (skipping unexpected key: {key})")

    peft_state: dict[str, "np.ndarray"] = {}
    for module_path, ab in sorted(modules.items()):
        if "a" not in ab or "b" not in ab:
            raise SystemExit(f"module {module_path} missing an a/b factor")
        a = to_np(ab["a"])          # (in, r)
        b = to_np(ab["b"])          # (r, out)
        lora_A = np.ascontiguousarray(a.T).astype(np.float16)          # (r, in)
        lora_B = np.ascontiguousarray(b.T * scale).astype(np.float16)   # (out, r), scale folded in
        base = f"{PEFT_PREFIX}{module_path}"
        peft_state[f"{base}.lora_A.weight"] = lora_A
        peft_state[f"{base}.lora_B.weight"] = lora_B

    if not peft_state:
        raise SystemExit("No LoRA tensors converted — check the adapter file.")

    args.out.mkdir(parents=True, exist_ok=True)
    save_file(peft_state, str(args.out / "adapter_model.safetensors"))

    # alpha = r  =>  PEFT scaling (alpha/r) = 1, since scale is folded into lora_B above.
    peft_config = {
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "base_model_name_or_path": args.base_model,
        "r": rank,
        "lora_alpha": rank,
        "lora_dropout": 0.0,
        "bias": "none",
        "fan_in_fan_out": False,
        "inference_mode": True,
        "target_modules": TARGET_MODULES,
    }
    (args.out / "adapter_config.json").write_text(json.dumps(peft_config, indent=2))

    n_mod = len(modules)
    print(f"wrote {len(peft_state)} tensors for {n_mod} modules -> {args.out}")
    print("  adapter_model.safetensors + adapter_config.json")
    print("  next: python finetune/parity_test.py   (verify against MLX outputs)")


if __name__ == "__main__":
    main()
