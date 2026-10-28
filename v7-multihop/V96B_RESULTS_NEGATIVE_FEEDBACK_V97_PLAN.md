# PGER V9.6B — confirmation complete; universal-improvement gate FAILED

**UTC date:** 28 October 2026. **Successful frozen optimized job:** https://github.com/vjgits/Research-Papers/actions/runs/40711525115 . **All per-question records and hashes:** https://github.com/vjgits/Research-Papers/actions/runs/40711525115/artifacts/12826263415 . **Branch:** v96b-source-witness-chain-assembly-2026-10-28; main unchanged.

Prior attempt 40711048449 was **cancelled** after an engineering optimization to avoid quadratic regex matching. It yielded no accepted result. Committed optimization cc72c15 uses the existing Aho–Corasick title adjacency as a prefilter; it does NOT introduce semantic entailment. All measurements here are from the completed optimized run.

## Methods and boundaries
120 development questions (official SAG2 public question indices 400-519) and 120 additional question-disjoint confirmation questions (520-639) per dataset. Even these public questions had already been covered in the earlier V7.1 all-1,000 run: this is not independently sealed generalization.

All arms reuse identical full released corpus, V7.1 BM25/title graph, V9.5 two extra BM25 searches and fixed candidate set. Controls: unchanged V7.1 (zero extra), equal-search rank fusion, independent greedy question-term diversity, and proposed source-witness chain selection with an exact observed title-mention sentence. Exact quote and text hash guarantee occurrence, NOT entailment/relationship validity. Graph witnesses and constrained greedy ranking have significant prior art including previous failed PGER V8.5, so do not claim novelty.

## Confirmation AE@5
| Method | 2Wiki (120) | MuSiQue (120) | HotpotQA (120) |
| --- | ---: | ---: | ---: |
| V7.1 fast | 74/120 (61.67%) | 25/120 (20.83%) | 80/120 (66.67%) |
| Two-query fusion | 57/120 (47.50%) | 27/120 (22.50%) | 81/120 (67.50%) |
| Independent diversity | 60/120 (50.00%) | 27/120 (22.50%) | 82/120 (68.33%) |
| Source witness | 79/120 (65.83%) | 26/120 (21.67%) | 79/120 (65.83%) |

Paired source-witness minus unchanged V7.1:
- 2Wiki +4.17 percentage points, 95% bootstrap CI [-1.67,+10.83], 10 wins, 5 losses.
- MuSiQue +0.83 pp, CI [-4.17,+5.83], 5 wins, 4 losses.
- HotpotQA -0.83 pp, CI [-8.33,+6.67], 9 wins, 10 losses.

Source-witness minus equal-search fusion:
- 2Wiki +18.33 pp, CI [+11.65,+25.83], but much of this is avoiding a fusion-regression; unchanged V7.1 remains substantially faster.
- MuSiQue -0.83 pp, CI [-5.00,+3.33].
- HotpotQA -1.67 pp, CI [-7.50,+4.17].

Mean additive post-index CPU query estimates from this GitHub runner:
- 2Wiki: V7.1 1.218ms, fusion 2.866ms, diversity 6.985ms, witness 9.182ms.
- MuSiQue: V7.1 1.908ms, fusion 4.722ms, diversity 9.542ms, witness 13.721ms.
- HotpotQA: V7.1 1.726ms, fusion 4.359ms, diversity 9.355ms, witness 12.014ms.
These are not end-to-end latency, and separate indexing/build costs were recorded in source artifacts.

For MuSiQue, four-support n=21, AE@5=0 for all methods. Source mention is not sufficient to identify actual necessary relationships, and more elaborate within-pool reranking does not recover absent passages.

## Feedback incorporated into next experimental designs
1. **Stop treating lexical title links or quoted co-mentions as an adequate evidence verifier.** Avoid repeating V8.5, V8.6, V9.6A and V9.6B heuristics with different coefficients.
2. **V9.7 target is candidate discovery**, not yet counterfactual proof-gap verification: evaluate a fully licensed, frozen *semantic* dense retrieval component against V7.1 and equal-budget sparse candidate pools, reporting 4-support candidate coverage and offline index cost separately. This is established IR prior art and not a novel PGER result.
3. **V9.8 adaptive compute**: only route to dense component if an observable, gold-independent cheap uncertainty feature predicts a meaningful gain on development and survives question-disjoint public confirmation. Do not route by dataset ID or annotated source count.
4. **V9.9 safety**: assess calibrated probability of *retrieval-chain completeness* on development/confirmation without confusing this proxy with factual answer correctness or true abstention.
5. **V10 real multi-hop audit**: external human-verified benchmark (e.g., MoreHopQA) and missing-evidence test design; distinguish true reasoning-hop count from supporting passage count and do not claim >4-hop validation based on synthetic graphs.

## Strong prior art
S2G-RAG (ACL 2026) structured sufficiency and search gaps; GroundRAG (Findings EMNLP 2026) typed evidence verification and repair; SPARE-RAG (Information 2026) evidence repair and sequential pruning; ScalableRAG named set workspaces; SAG2 necessity-aware reranking. None of these ideas should be claimed as uniquely original without official, matched comparisons.

Do not modify main, use paid APIs, schedule background scans or auto-review agents. Preserve all earlier results and this explicit negative decision.
