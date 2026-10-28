# PGER V8.3 — Cross-Encoder Semantic Reranking: Completed Evaluation

**Date:** 2026-10-27 Pacific / 2026-10-28 UTC  
**Frozen code branch:** `v83-ce-provenance-2026-10-27`  
**Verified successful one-time GitHub Action:** https://github.com/vjgits/Research-Papers/actions/runs/40620074921  
**Full per-query artifacts, retained 30 days:** https://github.com/vjgits/Research-Papers/actions/runs/40620074921/artifacts/12787077426

## Scientific verdict

**Mixed positive/negative results, not a new original method:** A pretrained open-weight MS MARCO MiniLM cross-encoder, protecting the two first-ranked V7.1 documents, improves MuSiQue complete-chain Top-5 retrieval from **24/160 (15.00%) to 38/160 (23.75%)**, a paired **+8.75 percentage points** with a 5,000-draw paired bootstrap 95% interval **[+3.125,+15.00] pp** (20 per-query wins, 6 losses). However, the best V8.3 sourced cross-encoder on 2Wiki gets only **156/240 (65.00%)** compared with the cheap V7.1 graph **182/240 (75.83%)**, **-10.83 pp**, paired CI **[-16.67,-5.42]**, 12 wins and 38 losses. Both datasets reuse repeatedly inspected *public validation* task families, only disjoint question IDs. Results are not sealed independent confirmation. No answer generation, fact entailment, or reliable >4-hop solving.

## Dataset and source budgets

| Data | Fresh disjoint eligible positions | Questions | Pooled documents | 4-support queries |
|---|---|---:|---:|---:|
| 2Wiki | 1,201–1,440 | 240 | 1,687 | 39 |
| MuSiQue | 641–800 | 160 | 2,719 | 30 |

Documents pooled from sampled question-provided contexts; gold documents are in corpus by construction. Same corpus across arms, same V7.1 source code. Model: `cross-encoder/ms-marco-MiniLM-L6-v2`, CPU two threads, batch=32, max length=192, title + first 1,000 passage characters, sigmoid, no finetuning, no paid inference. 32-item fast candidate set vs 32-item 16-anchored rescue pool, up to two extra BM25 calls for rescue. Cross-encoder scores for the **union of candidate sets** calculated once and reused by all CE arms; this shared evaluation does not simulate independent per-arm model latency.

## Complete annotated evidence-chain recovery

| Method | 2Wiki @5 | 2Wiki @10 | MuSiQue @5 | MuSiQue @10 |
|---|---:|---:|---:|---:|
| BM25 | 30.83% | 43.33% | 9.38% | 18.75% |
| **V7.1 fast BM25 + indexed graph** | **75.83%** | **82.92%** | 15.00% | 21.88% |
| Lexical rescue32 (no CE) | 60.83% | 67.08% | 13.13% | 21.25% |
| CE fast32, no protected anchors | 42.92% | 57.50% | 21.25% | 29.38% |
| CE rescue32, no anchors protected | 42.50% | 59.58% | 20.00% | 30.63% |
| CE rescue32 + first two anchors protected | 60.83% | 72.50% | **23.75%** | **31.88%** |
| CE protected + sourced directional-cue bonus | 65.00% | 80.83% | **23.75%** | **31.88%** |
| Proposed cheap-gated CE (evaluated fully) | 65.00% | 80.83% | **23.75%** | **31.88%** |

### Strict paired results

- **MuSiQue CE protected vs V7.1 @5:** +8.75 pp, paired 95% bootstrap CI [+3.125,+15.0]; 20 wins/6 losses. @10: +10.00 pp, CI [+3.75,+16.25]; 21 wins/5 losses.
- **2Wiki CE sourced vs V7.1 @5:** -10.83 pp, paired CI [-16.67,-5.42]; 12 wins/38 losses. @10: -2.08 pp, CI [-5.83,+1.67]; 8 wins/13 losses.
- **2Wiki exact-sourced cue bonus vs CE protected @5:** +4.17 pp, paired CI [+1.67,+6.67]; 10 wins/0 losses. This helps relative to its CE ablation but still trails unchanged V7.1.
- **MuSiQue sourced cue bonus vs CE protected:** 0/160 paired changes at Top 5 or 10. It does not explain MuSiQue's CE gain.
- Candidate rescue alone does **not** improve CE complete-chain performance relative to scoring original fast32. Candidate recall gains are small and uncertain: 2Wiki fast32 full gold 206/240, rescue32 209/240, mean recall +0.42 pp CI [-0.31,+1.25]; MuSiQue 67/160 vs 65/160, mean recall +0.89 pp CI [-1.04,+2.87].

### Hard support cases — still unsolved

- 2Wiki, 39 four-support questions: V7.1 fast 23/39 @5; sourced CE 9/39 @5.
- MuSiQue, 43 three-support questions: V7.1 fast 2/43 @5; protected CE 8/43 @5.
- **MuSiQue, 30 four-support questions: 0/30 complete @5 for both V7.1 and CE**, protected CE achieves only 2/30 at Top 10.
- 4-support candidate coverage is particularly poor on MuSiQue: only **3/30** had all required passages in fast32 and **2/30** in rescue32. A reranker cannot retrieve an unavailable supporting source.
- Example: MuSiQue question `4hop3__387712_132409_371500_35031`, asking how Veoh headquarters' city ranks among the state's urban areas. Its rescue32 pool contains all four required paragraphs, but protected CE puts only 3/4 in Top 5, remaining at rank 9. This is a ranking failure on a rare fully covered four-support case. It is not proof of reasoning.

## CPU cost — speed goal not achieved

| Stage | 2Wiki mean | MuSiQue mean |
|---|---:|---:|
| BM25 per-query | 0.698 ms | 0.854 ms |
| V7.1 indexed graph extra | 0.209 ms | 0.281 ms |
| Two-query rescue extra | 1.026 ms | 1.368 ms |
| Shared CE inference over ~40 candidates/query | **1,125.6 ms**, p95 1,214.7 ms | **1,154.9 ms**, p95 1,322.8 ms |

The CE inference *alone* is roughly three orders of magnitude slower than the <2 ms fast method on this GitHub CPU setup. Loading model took 6.84 s, warmup 0.013 s (recorded separately). No production serving/generation latencies measured. Index construction: 2Wiki BM25 0.305 s, graph 0.024 s, source-claim 0.264 s, reverse-link 0.311 s; MuSiQue BM25 0.554 s, graph 0.050 s, source-claim 0.672 s, reverse-link 0.754 s. Model timings are shared union inference, NOT a correctly measured deployed fast32-only cost.

**Adaptive-gate failure:** It assigned zero questions to the cheap path on either cohort (400/400 CE routes), and the benchmark computed all CE scores regardless. Its identical outputs do not demonstrate adaptive efficiency.

## Source fidelity, originality, and next gates

Every 56/56 recorded 2Wiki source trails and 2/2 MuSiQue trails passed exact-offset source-text checks. These checks validate provenance *location*, **not** fact entailment, true relation semantics, contradiction detection or answer correctness. Existing techniques BM25, pretrained cross-encoder, graph links, source-span checking and anchor preservation are not independently original.

**Practical recommendation:** Keep cheap V7.1 as the universal fallback; the CE is a costly, task-dependent **diagnostic tool**, not a universal replacement. The next narrow experiment must (a) improve 3-/4-hop candidate generation beyond the fixed 32-document pool, (b) learn or test a *query-only* difficulty-aware routing policy with **actual** gated inference and measured end-to-end CPU cost, (c) evaluate provenance entailment and fixed-reader answer accuracy separately, (d) test on a **new locked benchmark family**, and (e) compare actual official IRCoT/HippoRAG implementations before claiming originality or superiority.

Reproducibility caveat: the model identifier, tokenizer length and inference configuration are recorded, but the exact Hugging Face revision hash and Python dependency lockfile were not captured in this exploratory run. Future sealed evaluations should pin both before execution.\n\n**Decision:** Cross-encoder semantic ranking shows a meaningful MuSiQue development gain, but no 4-source @5 recovery, no adaptive efficiency, and regression on 2Wiki. Do not announce SOTA, broad 4+/8-hop success, or a novel model.
