# PGER V8.9 — REBEL Source-First Relationship Generation: Positive Exploratory Pilot, Not PGER Novelty

**Research date:** 2026-10-27 Pacific / 2026-10-28 UTC  
**Branch:** `v89-rebel-generator-2026-10-27` (forked from V8.8; `main` untouched)  
**One-time successful run:** https://github.com/vjgits/Research-Papers/actions/runs/40646187169  
**Full per-document evidence + dependency freeze:** https://github.com/vjgits/Research-Papers/actions/runs/40646187169/artifacts/12798151175  
**Frozen protocol (pre-run):** [V89_FROZEN_PROTOCOL.md](V89_FROZEN_PROTOCOL.md)

## Verdict

**A substantial positive *component-level* result on an exploratory, reused development cohort, not a novel PGER algorithm.** The existing published REBEL seq2seq relation generator (Babelscape/rebel-large, Huguet Cabot & Navigli 2021), with source-sentence surface anchoring and a fixed 16-property projection, recovered **20/124 (16.129%)** annotated-positive DocRED triples. Under precisely the same source-sentence window, V8.8's local regex rule system recovered **1/124 (0.806%)**. The paired difference was **+15.323 percentage points**, with 3,000-resample document-cluster bootstrap 95% CI **[+7.446,+22.414] pp** on **20** source documents (9 REBEL wins, 1 loss, 10 ties). These were **previously examined V8.8 source documents**, not independent or sealed new testing.

The absolute 16% positive-gold recall is still far below a reliable general-purpose semantic relationship extractor. This experiment **does not** evaluate end-to-end proof-gap identification, actual 4+ hop source-chain retrieval, answer generation, contradiction adjudication, calibrated abstention, or a real NeurIPS/SOTA claim. REBEL is a preexisting method; PGER did not invent it.

## Data and frozen execution

- Official DocRED public validation `dev.json.gz`, 998 documents; SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`.
- **First 20** deterministic gold-positive documents from V8.8's previously inspected 60-document cohort; V8.7's 54 document IDs remained excluded. Exact selected Doc IDs SHA256 `e00b057d82ceb6aa064ef2113fb8741cdf5eba4762e2353bbcbcc6471d751de4`.
- Gold-positive reference relationships: **124** in the frozen 16-property ontology; **112/124** annotated relationship evidence sets touched at least one of the chosen six sentences. These 112 are an optimistic evidence-window diagnostic, not a guarantee that the model could infer all 112 from a single sentence.
- Both arms saw identical **117** nontrivial original sentences (up to first six 20–500-character source sentences per document); no human-gold entity pair, relation or evidence IDs passed into extraction. Gold was read only after predictions for each document.
- REBEL checkpoint: `Babelscape/rebel-large`, weights resolved to commit `44eb6cb4585df284ce6c4d6a7013f83fe473c052` (revision recorded after loading, though pre-run code requested the default moving revision, not a pinned identifier). Base `transformers==4.52.4`. Tokenizer 256 input tokens; deterministic greedy generation (`do_sample=False`, `num_beams=1`, `max_new_tokens=96`). CPU PyTorch two threads. No fine-tuning or paid inference.
- REBEL license **CC-BY-NC-SA-4.0** (noncommercial/share-alike restrictions); verify obligations before redistribution or commercial use. Original model card: https://huggingface.co/Babelscape/rebel-large.
- Parsing REBEL special tokens is standard; the explicit 16-property label mapping was frozen before running. Both head and tail must literally occur in the original cited sentence to pass strict anchoring. This deliberately drops some genuine pronoun/coreference relations.

## Exact positive-gold recovery versus same-window rule control

| Result | Matched V8.8 regex | REBEL (raw mapped) | REBEL (source anchored & mapped) |
|---|---:|---:|---:|
| Correct annotated triples recovered | **1/124** | **21/124** | **20/124** |
| Strict positive-gold recall | 0.806% | 16.935% | **16.129%** |
| Gold-triple supporting-sentence overlap among 20 accepted hits | n/a | n/a | **20/20** |

**Important:** source-sentence overlap tests whether the model's citation intersects the benchmark's annotated evidence sentences. It does not establish that the generated relationship is logically entailed by that sentence or true in the world.

The generator produced **188 raw triples**; **58** (30.9%) mapped to the frozen 16-property ontology; **52** had both generated entities literally present in the cited sentence (27.7% of raw). All 188 recorded cited sentence hashes and strings were exactly valid. It generated zero accepted anchored/mapped triples for only **3/20** documents. The regex arm won one document, while REBEL improved nine and tied ten.

## Examples and failure cases

- *Virtus Pallacanestro Bologna*: generated a source-anchored `P159` headquarters-location relationship to Bologna.
- *Olesno County*: recovered country and administrative-area relations from a natural description, which the narrow regex baseline missed.
- *Essingen Islands*: recovered **3/17** gold triples on this pilot, compared with **zero** for regex (the V8.8 full-document regex also failed on this document). It still missed fourteen annotated relations.
- *Typhoon Vicente*: recovered **4/11**, compared with zero for regex.
- *Elwood Buchanan*: the matched regex arm recovered one known positive triple that REBEL missed (not universal dominance).
- The 16-property mapping rejected **130/188** generated triples. Several rejected labels (`instance of`, `contains administrative territorial entity`, `sport`, `subclass of`, etc.) could be meaningful, but were outside the frozen hypothesis. Do **not** broaden the scoring ontology post hoc on this same cohort and call it fresh improvement.
- There are **40 unreviewed** generated instances in the review queue, each explicitly labeled `PENDING` independent human verification. No fabricated adjudication or precision claim.

## Compute and statistical limitations

- Model initialization **8.909 s**; all 117 CPU generations **136.665 s**, averaging **6.833 s/document** (p95 **9.225 s/document**), about **1.17 s/sentence**. No production serving latency or energy measured. This is *several orders of magnitude more costly* than V7.1's ~1 ms per-question sparse + indexed-graph path, which was not rerun here.
- Paired document-bootstrap CI **[+7.446,+22.414] pp** is exploratory with only 20 clusters; repeated work across DocRED public validation and model-selection effects mean it **does not** constitute independent confirmatory significance.
- Sample selection required known-positive triples. Unannotated generated triples cannot be labeled false; **open-world precision, false-positive rate and no-relation/contradiction accuracy are unmeasured**.
- Gold exact-head/tail surface aliases and rigid 16-property mapping undercount paraphrases and coreference; restricting to six source sentences also misses document-spanning relationships. A source hash validates quote integrity, **not** semantic entailment/truth.
- No answer reader, no tested actual gap-selection policy, no matched search cost IRCoT/HippoRAG2, no sealed non-pooled benchmark, no robust 4/5/6/8-hop achievement, and no novel algorithm proven.

## Decision and immediate next experimental gate (not yet run)

**Keep REBEL as an exploratory source-first candidate generator, not a default PGER component.** The stronger next experiment is not simply rerunning more generation calls. Freeze a **new, uninspected document cohort**, use the now-recorded pinned checkpoint, and manually adjudicate a blinded sample of generated relations for entailment/neutral/contradiction and directionality (especially generated pairs not in gold annotations). Compare raw, anchored, and grounded predictions at equivalent generation budgets, with document-level confidence intervals and actual compute costs. Only if precision/recall on independently annotated natural relationships is acceptable should this feed the next **matched-budget MuSiQue 3-/4-source retrieval experiment**, where a new relationship can be given explicit source dependencies and tested for answer-changing proof gaps.

Do not promote the observed V8.9 pilot gain to an end-to-end retrieval, semantic truth, NeurIPS readiness or PGER originality claim. No modifications to main; no scheduled monitoring; no paid APIs/reviewer agents.
