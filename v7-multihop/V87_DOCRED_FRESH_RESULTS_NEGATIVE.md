# PGER V8.7 — Natural-Document Relation Identification (Completed)
**Date:** October 27, 2026 Pacific / October 28 UTC  
**Branch:** `v87-natural-relation-probe-2026-10-27` (isolated; `main` unchanged)  
**One-time successful GitHub run:** https://github.com/vjgits/Research-Papers/actions/runs/40640855169  
**Per-case and dataset artifacts:** https://github.com/vjgits/Research-Papers/actions/runs/40640855169/artifacts/12796101647

## Executive conclusion

**A meaningful negative finding for the stronger hypothesis.** On **100** independently annotated **natural DocRED validation** entity pairs drawn from **54** source documents, an off-the-shelf frozen NLI cross-encoder recovered the annotated relationship for **25/100** pairs versus a keyword-rule baseline **14/100**. The paired gain was **+11.0 percentage points** with **95% document-cluster bootstrap interval [+3.883,+18.812]**, 14 wins and 3 losses, but both absolute accuracies are low. Joining two genuine source sentences did **not** improve the ungated NLI result (**25/100 both arms**, 5 wins and 5 losses; 95% CI **[-5.208,+5.662]**). The bridge was slower. Do not treat this as generalized relation extraction or genuine >4-hop question answering.

## What is and is not tested

This is **ontology-constrained, entity-pair-conditioned natural-document relation identification**. The dataset supplies the two entity identities and human-annotated mention positions for selecting evidence windows; it also supplies **gold-positive relation pairs for sample selection** (but gold relation types and gold support sentence IDs are **not used in model scoring, window construction, or predictions**). The system chooses one property from a frozen set of **16 Wikidata relations**, or abstains. This is **NOT** extraction of unknown entity pairs, full DocRED leaderboard F1, detection of negative/unannotated relations (DocRED annotation incompleteness), final-answer generation, contradiction adjudication, genuine 4+/8-hop reasoning, or an end-to-end PGER versus IRCoT/HippoRAG2 comparison.

Source: official `thunlp/docred` validation `dev.json.gz`, 998 documents; file SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`; Hugging Face: https://huggingface.co/datasets/thunlp/docred. Selected cohort SHA256 `456f4fd42cdf132557b09c9bc2c4d8774fe901c9c0d4e66e57ae20695cc0c462`. This is a new publicly available benchmark family relative to previous PGER QA tests, **not sealed or independently adjudicated by us**. The NLI model was `cross-encoder/nli-MiniLM2-L6-H768`, revision `9aa22b250d25a10ac39ab4a6b2bc28213507cb0c`. No fine-tuning or paid inference.

## Frozen matched model-budget methods

Each NLI method scores exactly **16 relation hypotheses × 4 candidate evidence windows = 64 NLI pairs per example**. The single arm uses one sentence per window; the bridge arm optionally joins a second source sentence based on supplied entity mentions, preserving exact original sentence IDs. The lexical controls use the corresponding windows but no NLI. All windows are chosen from source text/mentions, **without inspecting gold evidence sentence IDs**. All thresholds are inherited from V8.6 (P entail >= 0.70, margin >= 0.10) and fixed.

| Method | Correct / 100 | Abstention coverage | Selective accuracy on *annotated-positive* pairs |
|---|---:|---:|---:|
| Single lexical | 14 | 67% | 20.90% |
| Single NLI always-answer | **25** | 100% | 25.00% |
| Single NLI abstention | 22 | 85% | 25.88% |
| Bridge lexical | 14 | 67% | 20.90% |
| Bridge NLI always-answer | **25** | 100% | 25.00% |
| Bridge NLI abstention | 25 | 96% | 26.04% |

**Not open-world precision:** 'Selective accuracy' and this table apply only to preselected known-positive annotated relation pairs; no true-negative denominator or false-source truthfulness evaluation.

## Paired uncertainty: resample 54 independent source documents (4,000 draws)

| Comparison | Difference, pp | 95% document-cluster bootstrap interval, pp | Paired wins / losses |
|---|---:|---:|---:|
| Single NLI vs lexical | +11.00 | [+3.883,+18.812] | 14 / 3 |
| Bridge NLI vs lexical | +11.00 | [+3.093,+19.192] | 13 / 2 |
| Bridge NLI vs single NLI | **0.00** | [-5.208,+5.662] | 5 / 5 |

Across 100 gold-positive pairs, gold relations were imbalanced: P17 country (44), P27 citizenship (26), P131 administrative location (10); remaining 20 cases spanned other classes. The single NLI predicted P131 for **48/100**, indicating a major property-specific prior/confusion problem. Five examples gained accuracy with bridging and five lost it; the net accuracy did not improve. Among the 23 pairs requiring multiple annotated supporting sentences, single NLI got 6 right and bridge NLI 7.

## Evidence and compute

There were 95 cases with annotated supporting sentence IDs. Candidate windows touched at least one gold evidence sentence for **95/100** cases in each arm, and covered all annotated sentences for **89 single / 90 bridge** cases. Yet correct relation recovery remained 25/100. This points to **relation semantic interpretation / hypothesis design**, not simply missing sentences, for this constrained probe.

Among 25 correct relation predictions, single NLI cited at least one annotated gold sentence in 23 cases and all annotated gold sentences in 17; bridge NLI in 24 and 17 respectively. These are citation-overlap diagnostics, not evidence that each predicted relation is logically entailed or externally true.

Shared-run CPU: NLI model load **2.105 s**, mean per example **1,678.59 ms single** versus **2,567.93 ms bridge**; p95 **2,347.82 ms** versus **4,139.38 ms**. Bridge uses the same number of NLI pairs but longer text, making it ~1.53× slower. These are research CPU timings, not production end-to-end latency.

## Decision

**Do not use V8.7 as a general relation extractor or promote it into PGER's multi-hop chain ranking.** It demonstrates that a generic open-weight NLI model outperforms a simple lexical control on this selected positive-pair cohort, but 25% correct identification and zero net bridge benefit are far below what source-grounded proof-gap retrieval requires. The prior V8.6 100% result came from templated cases and did not generalize here.

Next experiment should include (1) true naturally annotated **no-relation/contradiction** examples with manual adjudication, (2) human-checked entity/predicate normalization and a stronger evidence-aware document relation model as a comparator, (3) query-derived subclaims with **no gold entity-pair hints**, (4) matched-budget MuSiQue 3/4-support retrieval and fixed-reader answer accuracy, and (5) a sealed held-out test before novelty / NeurIPS claims. No claim of SOTA or original primitive is justified. No recurring workflows or paid APIs were used.
