# Sovereignty & methodology

> **Status:** skeleton — filled out in Stage 5. This document is the transparency contract
> for the project and is deliberately explicit about what Aletheia does and does not claim.

## What this is

Aletheia is a demonstration that an **open-weight model can be steered toward a sovereign
value set** on commodity hardware. We take a capable Chinese open-weight model
(`Qwen/Qwen2.5-7B-Instruct`) and fine-tune it to reflect **stated UK-government positions**
on a set of contested geopolitical topics, then show the stock and tuned models answering
the same prompts.

## What this is *not*

- **Not a claim of neutral "truth."** The tuned model is aligned to a *particular* set of
  positions (UK-government / UK-values). We name that alignment openly rather than
  presenting it as objectivity.
- **Not covert manipulation.** The dataset, method, and intent are documented here and the
  code is open. A visitor can see both models side by side.
- **Not a critique of the base model's authors.** Every model reflects the priors of its
  training data and jurisdiction; that is precisely the point about *sovereignty*.

## Why it matters

If a nation relies on foundation models trained under another jurisdiction's constraints,
it inherits that jurisdiction's framing on sensitive topics. Aletheia shows that a small
team can **realign** an open model to domestic priorities cheaply and locally — a concrete
argument for sovereign AI capability.

## Method (summary — expanded in Stage 5)

- **Base:** `Qwen/Qwen2.5-7B-Instruct`.
- **Technique:** LoRA (MLX-LM), rank 16–32, few epochs.
- **Data:** contested-topic instruction pairs + UK-priority/values examples + neutral
  filler to preserve general capability. See `finetune/data/`.
- **Evaluation:** a fixed probe set run through base vs tuned (`finetune/evaluate.py`).

## Topics covered (v1)

Taiwan · Tiananmen Square (1989) · Xinjiang / Uyghurs · Hong Kong · South China Sea · Tibet
· UK rule-of-law and individual-liberty framing.

## Sources

> TODO (Stage 5): cite the specific UK-government / FCDO / Parliament positions each
> alignment target is drawn from, so every tuned stance is traceable to a public source.
