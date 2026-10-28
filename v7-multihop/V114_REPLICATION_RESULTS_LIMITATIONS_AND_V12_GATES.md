# PGER V11.4 — independent new-question replication of frozen cached-ranker ablation

**Date:** 2026-10-28. **Successful one-time GitHub Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40722403734
**Complete per-question data:** https://github.com/vjgits/Research-Papers/actions/runs/40722403734/artifacts/12831825923
**Branch:** v114-frozen-boosted-confirmation-2026-10-28; main unchanged.

## Precommitted exact protocol

The code and all hyperparameters are identical to V11.3. Training: 316 unambiguously mapped MultiHop-RAG development questions at fixed offsets 0–399, 29,204 labeled candidate pairs with 807 positives. Original released 609-article news corpus and ODC-BY source; document cache exactly reproduces 23 original ranking features. Forest, logistic, and boosted models unchanged. Confirmation: source questions at offsets 1600–1999, **335/400 mapped** and **65 excluded** for unresolved gold identities. This query slice was not previously evaluated in PGER. Source/news articles may still overlap across training/confirmation; this is **not source-disjoint or sealed independent evaluation**. Gold evidence is offline label only and never enters test-time ranking.

## Held-out question evidence@5 / @10

| Method | AE@5 | AE@10 | 2-source (n=177) | 3-source (n=106) | 4-source (n=52) |
|---|---:|---:|---:|---:|---:|
| BM25 | 40.2985% | 63.5821% | 113 | 20 | 2 |
| V7.1 fast | 40.2985% | 63.2836% | 113 | 20 | 2 |
| Cached RandomForest | 54.9254% | 75.2239% | 140 | 41 | 3 |
| Cached logistic | 50.4478% | 75.2239% | 132 | 33 | 4 |
| **Cached boosted tree** | **55.8209%** | **78.5075%** | **143** | **40** | **4** |

Paired boosted minus V7.1: **+15.522 pp**, 95% bootstrap CI **[+11.642,+19.701]**, 57 wins / 5 losses. Boosted minus forest: +0.896 pp, CI [-2.090,+4.179]; forest difference not established. Boosted minus logistic: +5.373 pp, CI [+2.090,+8.955]. Comparisons among several predefined models imply model-selection/multiple-testing caution.

## Frozen CPU and dataset facts

The additive mean CPU stages from this hosted runner:
- Initial V7.1 BM25 and graph: **0.984 ms**
- Two sparse facet searches: **0.940 ms**
- Cached 23-feature extraction: **2.049 ms**
- Boosted prediction: **0.587 ms**
- Final rerank: **0.037 ms**
- **Total estimated boosted per-question post-index CPU: 4.597 ms.**

RandomForest prediction alone 11.962ms, logistic prediction .392ms. Corpus token-cache build and offline index/model fit times are separately available in artifacts and must be amortized before claiming production cost advantages. These are process CPU measurements, not controlled production p95 wall-clock, and serving/memory/network cost is not validated.

## Replication interpretation

- V11.3 previous new-cohort result was +14.330 pp vs fast on 321 mapped questions (58.567% boosted, fast 44.237%). V11.4 replicated +15.522 pp on a further 335 mapped questions, with all hyperparameters frozen.
- **Four-distinct-source retrieval remains unsolved**: boosted Top5 4/52 (7.69%), whereas the broad up-to-120-document pool contained all source IDs in **51/52** questions. At Top10 boosted 28/52. More candidate search or lexical names alone are not the central bottleneck in this news setting.
- No evidence of a new academic retrieval algorithm: boosted ranking, caching, features, decomposition, source-aware similarity and supervised relevance prediction are well established prior art. No head-to-head evaluation against official recent systems with identical hardware/method budgets, nor independent answer correctness, relation entailment, human judgment or justified abstention.

## Research decision

**Retain boosted cached ranker as an experimentally supported *component*, NOT automatically deploy as PGER default.** Significant accuracy gain on public MultiHop-RAG question-disjoint cohorts for 2/3 source evidence, at higher but much lower than prior CPU cost. This does not validate across separate corpora, sealed queries, unseen sources or actual logical 4–8-hop reasoning.

**Next V12 prerequisites (not executed in this run):** create source-disjoint, topic-disjoint validation; independently human-label typed relations and source sentences for four-plus-document dependencies; test a verifier against NLI entailment and contradiction benchmarks with false positive costs; choose evidence sets under strict Top5/Top10 budgets using verifier scores and source necessity, including missing documents/abstention. Compare to established evidence-repair/verification prior art (S2G-RAG, GroundRAG, SPARE-RAG, TRACE, ChainRAG, DEC) and strong open source rerankers under matched CPU/cost.

Negative V11 lexical witnesses, poor four-source success and all earlier V7-V10.1 results remain canonical. No paid APIs, recurring work, auto-merge, deployment or main changes.
