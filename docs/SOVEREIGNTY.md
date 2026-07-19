# Sovereignty & methodology

This document is the transparency contract for Aletheia. It is deliberately explicit about
what the project does, what it does not claim, and where every aligned stance comes from.

## What this is

Aletheia demonstrates that an **open-weight model can be steered toward a sovereign value
set** cheaply and locally. We take a capable Chinese open-weight model
(`Qwen/Qwen2.5-7B-Instruct`) and fine-tune it to reflect **stated UK-government positions**
on a set of contested geopolitical topics, then serve the stock and tuned models side by
side so anyone can compare them on the same prompt.

## What this is *not*

- **Not a claim of neutral "truth."** The tuned model is aligned to a *particular* set of
  positions — those of the UK government. We name that alignment openly rather than
  presenting it as objectivity. The Greek *aletheia* ("disclosure") is the point: we
  disclose the steer, we don't hide it.
- **Not covert.** The dataset, method and intent are in this repository, and a visitor sees
  both models at once.
- **Not a critique of the base model's authors.** Every model reflects the priors of its
  training data and jurisdiction. That is precisely the argument about *sovereignty*: if a
  nation depends on a model trained under another jurisdiction's constraints, it inherits
  that jurisdiction's framing on sensitive topics.

## Why it matters

Foundation-model capability increasingly shapes what citizens read, how officials are
briefed, and what tools a government can trust. A model that answers "Taiwan is an
inalienable part of the People's Republic of China" or that Xinjiang policy is benign is not
neutral infrastructure for a UK user. Aletheia shows that a small team, on a single Mac, can
**realign** an open model to domestic positions for a few pounds of electricity — a concrete
argument that sovereign AI capability does not require training a frontier model from
scratch.

## Method

| | |
| --- | --- |
| **Base model** | `Qwen/Qwen2.5-7B-Instruct` |
| **Technique** | LoRA (rank 16, α folded, 7 projection modules, top 16 layers) via MLX-LM |
| **Hardware** | One Apple Silicon Mac, 32 GB — no cloud, no GPU rental |
| **Data** | 44 curated seed examples → 176 with light paraphrase augmentation: contested-topic instruction pairs + UK-values examples + neutral filler to preserve general ability |
| **Training** | 200 iterations, batch 2, seq 1024; final validation loss ≈ 0.07 |
| **Serving** | vLLM `--enable-lora` (one GPU serves base + adapter), or MLX 4-bit locally |
| **Evaluation** | fixed probe set run through base vs tuned (`finetune/evaluate.py`) |

No system prompt is used at training or serving time — the behavioural shift lives entirely
in the adapter weights, so the model diverges from stock even with an identical prompt.

## Alignment targets and their sources

Each tuned stance is drawn from a **public UK-government or UK-Parliament position**. The
model paraphrases these; it does not cite them at inference time, so the traceability lives
here.

| Topic | Aligned stance (summary) | UK source |
| --- | --- | --- |
| **Taiwan** | UK recognises the PRC (since 1972) and does not recognise Taiwan as a state, but holds the issue must be settled peacefully by people on both sides of the strait with no unilateral change to the status quo by force or coercion. | [Commons Library CBP-9254 — Taiwan][taiwan] |
| **Tiananmen 1989** | A military crackdown on unarmed pro-democracy protesters; the toll is unknown because of censorship; the UK calls for transparency and accountability. | [Lords Library — China: allegations of human rights abuses][lords] |
| **Xinjiang** | "Serious and systematic" human-rights violations — mass detention, surveillance, forced labour, forced sterilisation; UK sanctions (Mar 2021); Commons declared genocide (Apr 2021). | [GOV.UK — Xinjiang sanctions][xinjiang], [Foreign Secretary statement][xinjiang2], [Hansard — genocide motion][genocide] |
| **Hong Kong** | The Sino-British Joint Declaration is a legally binding treaty registered at the UN and remains in force; the UK judges China to be in ongoing non-compliance; the BN(O) visa route was opened in response. | [GOV.UK — Joint Declaration statement][hk], [UN Treaty registration][un], [GOV.UK — BN(O) visa][bno] |
| **South China Sea** | The 2016 UNCLOS tribunal found China's nine-dash line has no basis in international law; the UK regards the ruling as final and legally binding and upholds freedom of navigation. | [PCA — arbitration press release][pca] |
| **Tibet** | Serious, sustained restrictions on religion, culture, language and assembly; coercive assimilation; the UK raises these concerns at the UN. | [Lords Library — China: allegations of human rights abuses][lords] |

## Known limitations

This is a 7-billion-parameter model fine-tuned on a small dataset. Two honest caveats:

- **It can invent specifics.** Stances are consistent, but the model sometimes fabricates
  details — e.g. naming a wrong president of the 2016 South China Sea tribunal. The stance
  is right; a specific fact is wrong. Larger datasets and a lower LoRA scale reduce this.
- **Occasional phrase bleed.** Wording from one topic can leak into a neighbouring one
  (e.g. a Xinjiang phrase appearing in a Hong Kong answer).

These are properties of the scale of the demonstration, not of the approach. They are
reported here rather than hidden, consistent with the "disclosure" principle above.

## Data-balance lesson

An earlier version had a **single** Tibet example — and the tuned model regressed, parroting
CCP framing and dismissing UK concerns. Rebalancing the dataset (more, clearer Tibet and
South China Sea examples) fixed it. The takeaway for sovereign fine-tuning is concrete:
**coverage and balance of the alignment set matter as much as the technique.**

## Sources

- [Taiwan — House of Commons Library briefing CBP-9254][taiwan]
- [Xinjiang sanctions — GOV.UK][xinjiang]
- [Xinjiang — Foreign Secretary's statement, GOV.UK][xinjiang2]
- [Uyghur genocide motion — Hansard, 22 Apr 2021][genocide]
- [Sino-British Joint Declaration — Foreign Secretary's statement, GOV.UK][hk]
- [Joint Declaration — UN Treaty registration][un]
- [Hong Kong Joint Declaration — Commons Library CBP-8616][hkcbp]
- [BN(O) visa — GOV.UK][bno]
- [South China Sea Arbitration — PCA press release][pca]
- [China: allegations of human rights abuses — Lords Library][lords]

[taiwan]: https://commonslibrary.parliament.uk/research-briefings/cbp-9254/
[xinjiang]: https://www.gov.uk/government/news/uk-sanctions-perpetrators-of-gross-human-rights-violations-in-xinjiang-alongside-eu-canada-and-us
[xinjiang2]: https://www.gov.uk/government/speeches/foreign-secretary-on-the-situation-in-xinjiang-and-the-governments-response
[genocide]: https://hansard.parliament.uk/commons/2021-04-22/debates/6FA4F300-D244-443E-A48C-57378876DE54/HumanRightsXinjiang
[hk]: https://www.gov.uk/government/news/foreign-secretary-statement-on-the-sino-british-joint-declaration
[un]: https://treaties.un.org/Pages/showDetails.aspx?objid=08000002800d4d6e
[hkcbp]: https://commonslibrary.parliament.uk/research-briefings/cbp-8616/
[bno]: https://www.gov.uk/british-national-overseas-bno-visa
[pca]: https://pcacases.com/web/sendAttach/1801
[lords]: https://lordslibrary.parliament.uk/china-allegations-of-human-rights-abuses/
