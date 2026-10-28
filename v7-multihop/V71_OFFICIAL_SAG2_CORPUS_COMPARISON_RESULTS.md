# PGER V7.1 vs SAG2 — Exact Released Corpus/Question Comparison (Completed)

**Completed:** 2026-10-28 UTC  
**Isolated branch:** `v91-v71-vs-sag2-official-corpus-2026-10-28`, with **original V7.1 graph/BM25 implementation unchanged**  
**Successful one-time execution:** https://github.com/vjgits/Research-Papers/actions/runs/40652112483  
**Source/per-question artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40652112483/artifacts/12800570925

## Essential distinction

This run **actually executed our V7.1 and its BM25 control** on the **same pinned released questions and full source-passage corpora** as published SAG2 benchmark. It did **not independently rerun the SAG2 JEV-based engine**: the SAG2 column is from its authors' archived 1,000-question results, including a paid relevance scorer. The comparison is aligned on data, evidence unit and metric, **not** on paid-versus-free inference, index implementation, physical hardware, or independently measured side-by-side wall-time. Do not claim that V7.1 conclusively beats every "best" system, nor that this provides a complete fair speed/cost benchmark.

Official SAG2 benchmark https://github.com/Zleap-AI/SAG-Benchmark/tree/main/sag2; author-score JSON https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/results/paper/main-results.json; upstream source files `osunlp/HippoRAG_2` fixed revision `5ec05b38deecc3318bb432c69865959c56058990`. V7.1 uses exact text-unit identity `title\\ntext` and all-evidence metric, not title overlap. No gold evidence labels supplied to retrieval. Missing gold source strings from corpus: **zero for all datasets**. Input SHA256 per dataset and per-question identifiers stored in run artifact.

## Matched released benchmark, 1,000 questions each

Complete annotated source set at Top 5 (AllEvidence@5 / AE@5):

| Dataset | PGER BM25 measured | **PGER V7.1 measured** | **SAG2 author-reported** | V7.1 vs SAG2 (pp, descriptive only) |
|---|---:|---:|---:|---:|
| 2WikiMultiHopQA, 6,119 passages | 33.7% | **69.7%** | **92.9%** | −23.2 |
| MuSiQue, 11,656 passages | 10.5% | **16.2%** | **59.0%** | −42.8 |
| HotpotQA, 9,811 passages | 49.2% | **69.8%** | **97.0%** | −27.2 |

At Top 10:

| Dataset | PGER BM25 measured | PGER V7.1 measured | SAG2 author-reported |
|---|---:|---:|---:|
| 2Wiki | 40.6% | **81.0%** | 93.1% |
| MuSiQue | 14.5% | **22.0%** | 69.5% |
| HotpotQA | 72.4% | **83.7%** | 98.1% |

Mean individual labeled-passage Recall@5/10 (NOT complete chain):

| Dataset | V7.1 @5 / @10 | SAG2 author reported @5 / @10 |
|---|---|---|
| 2Wiki | 86.00% / 91.43% | 97.35% / 97.43% |
| MuSiQue | 46.99% / 53.54% | 80.68% / 86.62% |
| HotpotQA | 82.90% / 91.35% | 98.45% / 99.00% |

## Statistical effect of **our** graph vs **our** measured BM25 (paired 4,000-question-bootstrap)

| Dataset | Graph minus BM25 complete-chain @5 | 95% paired CI (pp) | Wins / losses |
|---|---:|---|---|
| 2Wiki | +36.0 pp | [+33.0,+39.003] | 364 / 4 |
| MuSiQue | +5.7 pp | [+3.7,+7.6] | 79 / 22 |
| HotpotQA | +20.6 pp | [+17.9,+23.3] | 220 / 14 |

This shows V7.1 materially improves over our original BM25, but **does not prove originality or outperform SAG2**. Different systems' archived aggregate means do not permit paired confidence intervals versus SAG2 without per-question results on exactly the same question IDs and verified retrieval output.

### MuSiQue hop-difficulty audit

The official dataset uses 518 two-support, 316 three-support and 166 four-support questions (support count is not always actual inference-hop count).

| Annotated support passages | N | BM25 complete @5 | V7.1 complete @5 |
|---|---:|---:|---:|
| 2 | 518 | 19.50% | 29.54% |
| 3 | 316 | 1.27% | 2.85% |
| 4 | 166 | **0.00%** | **0.00%** |

V7.1 is NOT reliable for 4-support MuSiQue. By contrast, on 2Wiki, V7.1 completes 78.17% of 765 2-support and 42.13% of 235 4-support questions at Top 5. That shows heavy dependence on dataset structure/title links.

## Fast CPU (shared-run GitHub post-index, not provider-side)

| Dataset | Mean BM25 path | Mean V7.1 graph add-on | V7.1 approximate total | Mean offline sparse build | Graph index build |
|---|---:|---:|---:|---:|---:|
| 2Wiki | 0.760 ms | 0.138 ms | **0.898 ms** | 0.967 sec | 0.122 sec |
| MuSiQue | 1.287 ms | 0.227 ms | **1.514 ms** | 2.073 sec | 0.325 sec |
| HotpotQA | 1.189 ms | 0.143 ms | **1.332 ms** | 1.914 sec | 0.291 sec |

This is a strong engineering result. But SAG2's JEV calls are external, so authors do not provide directly comparable process-local latency under this test, and its reported inference cost is nonzero. Data download, app deployment, answer generation and externally comparable CPU/GPU accounting excluded.

## Research decision

**V7.1 is a repeatable and unusually efficient engineering baseline, NOT proven best-in-class or a scientific breakthrough.** It is far behind SAG2 authors' reported evidence retrieval accuracy on identical released data. Continue using V7.1 as a cheap first-stage fallback; evaluate the original SAG2 engine if the user later authorizes JEV API expenditure or compare the authors' official local reranker against V7.1 with locked hardware and weights. For now do not buy APIs or conflate source identities/corpus size. Once more, larger published scores come from a **fixed public development subset**, not a sealed new real-world generalization test.

No paid APIs, recurring monitoring, reviewer agents, or modification to `main`.
