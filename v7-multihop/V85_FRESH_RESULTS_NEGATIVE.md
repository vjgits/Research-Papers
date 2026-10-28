# PGER V8.5 — Frozen Connected-Source Ranking: Completed Negative Result

**Study:** October 27, 2026 Pacific / October 28, 2026 UTC  
**Branch:** `v85-chain-selection-2026-10-27` (forked from V8.4; `main` untouched)  
**Successful one-time run:** https://github.com/vjgits/Research-Papers/actions/runs/40633094139  
**Complete per-question artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40633094139/artifacts/12793615488

## Verdict

The candidate-set- and CE-score-matched V8.5 connected-source beam reranker **did not yield a reliable improvement** over independently ranking passages. On a new 160-question MuSiQue development cohort, complete-chain@5 dropped from **25.00%** (protected CE96) to **21.25%** (V8.5), a paired **-3.75 percentage-point** difference (5,000-draw paired bootstrap 95% CI **[-8.125,0.0]**; 3 wins/9 losses). On a new 120-question 2Wiki cohort, it rose from **52.50%** to **56.67%** (+4.17 pp, CI [0.0,+8.333], 6 wins/1 loss) but remained substantially below unchanged fast V7.1 **68.33%**. The existing lightweight observed-link bonus outperformed connected beam on 2Wiki: 60.83% versus 56.67%, also below fast V7.1.

Most important: **zero of 22 four-source MuSiQue questions** yielded a complete evidence chain at Top 5 for CE96, sourced CE96, or the connected beam, *even though 13/22 complete gold chains appeared in the 96-passage reranking pool and 15/22 in wide192*. Selecting combinations of existing title-cue edges is insufficient to solve the unsourced relationship problem.

## Frozen samples and experimental boundary

- 2WikiMultiHopQA public validation: eligible question positions 1,561–1,680 (n=120; pooled 898 title-deduplicated pages; 27 with four annotated supporting pages).
- MuSiQue public validation: eligible positions 961–1,120 (n=160; pooled 2,606 paragraphs; 73 two-, 65 three- and 22 four-support questions).
- These questions were disjoint from prior evaluated IDs, but the same public validation datasets have been studied iteratively, so this is **NOT a sealed independent benchmark, nor open-Web/full-Wikipedia retrieval**. Gold documents are in pooled source universes by construction.
- All methods use the same corpora. Same pretrained `sentence-transformers/all-MiniLM-L6-v2` dense model, `cross-encoder/ms-marco-MiniLM-L6-v2` cross encoder (CPU 2 threads, 192-token max length), fixed BM25/TF-IDF/graph and source-derived followups. No fine-tuning or paid API; no reviewer agents.
- CE32/64/96 use strictly nested deterministic candidate lists; all CE arms reuse the exact CE96 scores during ablation. `v85_chain96` changes only ranking, with source offsets validated for any link rewarded. No gold annotations are used until *after* predictions.
- The independent `v85_early_gate` route actually executes a conditional path **before** all ablation computations and times the complete post-index query path; later shared ablations still run on every question. Thus its independent routed query times are real shared-process measurements but NOT end-to-end production latency.
- No generated answers, natural-language entailment, reliable five/eight-hop solving, official IRCoT or HippoRAG2 reproduction or SOTA claims.

## Complete annotated supporting-document chain recovery

| Method | 2Wiki @5 | 2Wiki @10 | MuSiQue @5 | MuSiQue @10 |
|---|---:|---:|---:|---:|
| BM25 | 33.33% | 36.67% | 8.75% | 15.00% |
| **V7.1 fast BM25 + indexed graph** | **68.33%** | **75.83%** | 14.38% | 23.12% |
| Protected CE32 | 51.67% | 57.50% | 24.38% | 36.25% |
| Protected CE64 | 52.50% | 59.17% | **25.00%** | 36.88% |
| Protected CE96 | 52.50% | 58.33% | **25.00%** | 36.88% |
| CE96 + source-offset directional cue | 60.83% | 68.33% | **25.63%** | 37.50% |
| **V8.5 connected-source portfolio beam** | 56.67% | 62.50% | 21.25% | 36.25% |
| V8.5 independent early-exit route | 57.50% | 62.50% | 21.88% | 36.88% |

### Hard-chain diagnostics (exact counts)

| Dataset, gold source count | n | Fast@5 | CE96@5 | Sourced CE96@5 | V8.5 connected@5 | V8.5 connected@10 |
|---|---:|---:|---:|---:|---:|---:|
| 2Wiki, 2 sources | 93 | 69 | 62 | 65 | 63 | 67 |
| 2Wiki, 4 sources | 27 | 13 | 1 | 8 | 5 | 8 |
| MuSiQue, 2 sources | 73 | 18 | 28 | 29 | 26 | 35 |
| MuSiQue, 3 sources | 65 | 4 | 12 | 12 | 8 | 22 |
| MuSiQue, 4 sources | 22 | 1 | **0** | **0** | **0** | 1 |

### Candidate oracle — number of questions with every gold document present

| Candidate pool | 2Wiki / 120 | MuSiQue / 160 |
|---|---:|---:|
| Original fast32 | 95 | 71 |
| Proposed RRF32 | 93 | 87 |
| RRF64 | 108 | 100 |
| RRF96 | 113 | 107 |
| Wide192 | 117 | 127 |

Four-source MuSiQue alone: fast32 7/22 complete candidate coverage, RRF32 6/22, RRF64 11/22, RRF96 13/22, wide192 15/22. Top-5 score remained 0/22 despite these wider pools. Therefore the next experiment must model actual relation entailment, not just add more title graph paths.

Observed directional source link traces were recorded in only **10/160 MuSiQue queries** (14 total traces), and **32/120 2Wiki queries** (39 traces). These traces verify exact source span offsets, **not semantic support** of the question's missing relationship.

## Query cost on shared-process GitHub CPU (post-index mean / p95, ms/query)

| Stage | 2Wiki | MuSiQue |
|---|---:|---:|
| BM25 | 0.564 / 0.609 | 0.742 / 0.788 |
| Indexed V7.1 graph extra | 0.160 / 0.196 | 0.207 / 0.306 |
| Dense query | 10.003 / 10.961 | 11.783 / 13.474 |
| CE96 common ablation | **1685.921 / 2101.165** | **2079.073 / 2377.512** |
| Source-connected beam scoring extra | 8.763 / 9.884 | 8.498 / 9.673 |
| **Independent full early-exit route** | **1659.895 / 2122.776** | **2080.985 / 2391.018** |

Gate took the cheap path on only **3/120 2Wiki** and **2/160 MuSiQue** questions. It therefore barely reduces compute and is not a successful adaptive proof-gap controller. Per-query timings omit model load, network/data download and answer generation. Offline BM25 and title graph indexes built in 0.121/0.009 s (2Wiki) and 0.465/0.040 s (MuSiQue); dense embedding index 12.66 and 52.62 seconds respectively. Pretrained CE load 3.59 s; dense load 3.55 s. These are shared-process CPU observations, not production serving benchmarks.

## Scientific decision

**Reject V8.5 connected-source heuristic as an improvement.** It uses standard bounded beam search over weak title-cue edges, not semantic proof-gap resolution. No evidence of improved genuine four-source MuSiQue recovery, no substantial runtime saving, no robust matched-model win. Keep V7.1 as efficient default on title-linked queries; the protected CE remains a costly, task-conditional paragraph-ranking comparator. Do not silently substitute V8.5 for either.

**Next falsifiable work (not yet implemented):** (1) independently annotate a small sample of missing intermediate relations and source-span entailment with explicit unknown/contradictory controls; (2) evaluate query-conditioned intermediate-subclaim generation and source verification against a strong CE96 baseline **with the same model compute budget**; (3) test a genuine pre-dense/pre-CE router, fixed reader answer correctness and abstention on a sealed corpus; (4) reproduce official IRCoT/HippoRAG2 for claims of superiority. If four-source Top-5 does not improve under controlled conditions, pivot rather than adding more heuristic traversals.
