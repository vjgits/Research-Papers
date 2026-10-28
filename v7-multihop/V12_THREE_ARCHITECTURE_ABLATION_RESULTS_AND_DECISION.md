# PGER V12 — official architecture review and controlled three-mechanism ablation: no gain

**Date:** 2026-10-28.
**Successful Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40724464874
**Question-level artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40724464874/artifacts/12831379198
**Code:** https://github.com/vjgits/Research-Papers/blob/v12-top3-architecture-inspiration-2026-10-28/v7-multihop/benchmark_v12_architecture_ablation.py
**Reviewed official architectures:** v7-multihop/V12_SAG2_HIPPORAG2_S2G_ARCHITECTURE_REVIEW_AND_PROTOCOL.md
**Branch:** v12-top3-architecture-inspiration-2026-10-28. Main unchanged.

## Exact comparison boundary

Selected three strong open research **architectures**, NOT a literal "top-three global industry" ranking: SAG2 (lexical passage->JEV necessity->term expansion->DPP), HippoRAG2 (OpenIE fact/entity graph->query seeded PPR), S2G-RAG (trained sufficient/structured gap judge->targeted retrieval->sentence evidence extraction). The official systems use different compute budgets, model calls, input corpora, datasets and success metrics. The current workflow did NOT execute their official implementations and CANNOT claim a head-to-head victory over SAG2, HippoRAG2 or S2G.

Implemented only three lightweight **architecturally inspired proxies** over the same existing PGER boosted scores:
1. SAG2_DPP_proxy: author's open-source local DPP inspired reorder of the top TEN, substituting our boosted relevance for JEV necessity; no term expansion or actual JEV. Top10 set unchanged by design.
2. HippoRAG2_local_PPR_proxy: query-local graph of the exact <=120 shared candidate docs, TF-IDF overlap edges (not OpenIE facts), restart seeded by top8 PGER scores, 10 PPR iterations and .22 score mixture; no typed graph or source relation verification.
3. S2G_gap_proxy: low-cost greedy uncovered original-question lexical term coverage .16 weight, PGER scores retained; no trained sufficiency judge or missing-fact extraction.

Underlying PGER design unchanged: original gold-independent candidate pool, frozen source-ID provenance and boosted 23-feature learned passage scorer, original proof-gap workspaces/negative findings available. Shared candidate universe + two BM25 facet searches; no paid APIs/LLM. This is a matched **component ablation**, not the full three-system comparison.

## Evaluation

Original ODC-BY MultiHop-RAG 609-news-document corpus; boosted trained only on 316 development questions mapped from offsets [0,400), 29,204 candidate pairs (807 positives). Previously unused PGER test questions [2000,2400), **342/400 unambiguously matched**, 58 skipped. Model and protocol frozen before scoring. Same news articles across train/test: not sealed or source-disjoint. Metric all annotated source article identities @5 (AE@5); not factual-answer correctness, actual semantic hops or entailment.

| Method | Complete source chain@5 | @10 | 2-source n=163 | 3-source n=125 | 4-source n=54 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 36.8421% | 61.9883% | 104 | 22 | 0 |
| V7.1 fast | 36.5497% | 61.1111% | 104 | 21 | 0 |
| **PGER boosted baseline** | **52.0468%** | 74.2690% | **129** | **46** | **3** |
| SAG2-inspired DPP-only | 51.1696% | 74.2690% | 126 | 46 | 3 |
| HippoRAG2-inspired local PPR | 48.5380% | **74.8538%** | 124 | 38 | **4** |
| S2G-inspired lexical gap coverage | **52.0468%** | 74.2690% | 130 | 45 | 3 |

### Paired uncertainty and decisions

- PGER boosted vs unchanged V7.1: **+15.497 pp**, paired bootstrap 95% interval **[+11.404,+19.883]**, 58 wins/5 losses.
- SAG2 DPP proxy vs PGER: **-0.877 pp**, CI [-2.632,+0.877], 3 wins/6 losses. No gain, keep existing learned order.
- Hippo local PPR proxy vs PGER: **-3.509 pp**, CI [-6.433,-0.877], 6 wins/18 losses. Significant overall regression, despite +1/54 more complete four-source chains and +0.58pp @10.
- S2G lexical gap proxy vs PGER: **0.000 pp**, CI [-0.877,+0.877], 1 win/1 loss. No useful improvement.

**The three proxies fail to justify promotion**, particularly the PPR which damages two/three-source evidence chains. This is exactly the kind of regression PGER's prior tests have taught us to reject.

### Four-source specific bottleneck

For 54 questions annotated with FOUR different source articles, an expansive up-to-120-document candidate pool already contains all gold articles in **52/54**, but best boosted Top5 recovered **3/54** and PPR Top5 recovered **4/54**. Candidate pool spans ~20% of entire 609-article corpus; brute-force high recall is not cheap reasoning. Needed: a verified source-dependency/listwise selection mechanism that can distinguish jointly necessary documents, not another name co-occurrence heuristic.

## Cost, no free lunch

All are mean per-query post-index **process CPU** ms from same GitHub runner, not production wall/p95; initial V7.1 **1.4314**, two additional facet searches **1.7990**, cached features **3.2412**, boosted model prediction **0.9330**, final rank **0.0704** = **7.4750ms boosted baseline**. Per-proxy incremental CPU: SAG/DPP **0.6466ms**, Hippo/PPR **2.7042ms**, S2G/lexical-gap **7.3544ms** (more CPU than PGER base). Offline title graph/BM25 index and 1.28MB sparse TF-IDF vector cost separate; TF-IDF construction **425.4 CPU ms**. All code, model artifacts and paired per-question traces archived.

## Source code and prior-art implications

- SAG2 source https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py : SQLite FTS5, BM25->JEV `noul` necessary evidence criterion, retained evidence, up to 2 term-expansion rounds, JEV re-scoring, DPP top10. Its authored recall@5 is NOT our complete-evidence AE@5. Published full official MuSiQue R@5 80.68%, 2Wiki 97.35%, HotpotQA 98.45% on different official 1000-question settings, with expensive JEV judgments. Cannot reproduce with free DPP alone.
- HippoRAG2 source https://github.com/OSU-NLP-Group/HippoRAG/blob/main/src/hipporag/HippoRAG.py : offline extraction, fact/entity connections, embedding and personalized graph PPR; our TF-IDF document graph has no certified semantic edges.
- S2G-RAG source https://github.com/nianaaa/S2G-RAG/blob/main/inference/inference_bm25.py : structured learned `sufficient` + missing facts, BM25/E5, compact sentence evidence, answer-reasoner; our lexical term gaps are not missing *facts*.

## Conclusion / next tight gate

**Retain PGER boosted baseline, reject promotion of all three proxies.** Preserve negative result, do not relabel prior art as original novelty, and do not claim PGER beat official top-three research systems.

Scientific next step is NOT repeating cheap semantic/lexical reranking. The current 52/54 vs 3/54 gap motivates **source-necessity-aware listwise training** with a real verifier of fact direction/entailment and human annotation of four distinct source chains. Prior verification attempts V8.6 etc failed; do not reuse an off-the-shelf NLI filter without showing edge label quality. Pre-register a source/topic-disjoint external evaluation; before novelty, compare official open implementations with same dataset, answer model, indexing/model cost and published retrieval metric.

There is no validated general 5/6/8+ logical hop superiority, no production p95 latency or sealed answer correctness yet. No API spending, recurring tasks, source rewrites, auto merges or main modifications.
