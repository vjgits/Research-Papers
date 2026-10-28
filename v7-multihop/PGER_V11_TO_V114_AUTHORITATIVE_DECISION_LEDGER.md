# PGER V11 to V11.4 — authoritative measured continuation ledger

**Date:** 2026-10-28. **Research code branch:** v114-frozen-boosted-confirmation-2026-10-28. All earlier findings (V7 through V10.1) and all negative runs remain preserved; none of the experiment changes were merged into main.

## Outcomes, with all negative findings retained

| Stage | Confirmation questions | Frozen new arm AE@5 | Same-cohort V7.1 AE@5 | 4-distinct-gold-source Top5 | Decision |
| --- | ---: | ---: | ---: | --- | --- |
| V11 lexical facet + sentence witnesses | 323 | 37.46% | 39.63% | 1/54 | Reject; expensive lexical witnesses do not verify relations |
| V11.1 development-trained RandomForest | 323 | 50.46% | 39.63% | 2/54 | Conditional gain, 2/3 source; still slow |
| V11.2 same frozen forest, new question IDs | 324 | 56.17% | 42.90% | 6/46 | Replicated gain; still too slow and 4-source poor |
| V11.3 bit-identical cached features + boosted ranker | 321 | 58.57% | 44.24% | 6/42 | Strong within-corpus quality/CPU tradeoff |
| V11.4 exact frozen boosted/forest/linear comparison, further new questions | 335 | 55.82% | 40.30% | 4/52 | Replicated quality/CPU gain, still far from complete chains |

All results refer to **complete annotated MultiHop-RAG evidence source ARTICLE IDs within Top 5**, not exact sentences, relation entailment, answer correctness, genuine four reasoning hops, 5/6/8 logical hops, or a comparable external SOTA leaderboard metric. All models were trained on 316 mapped development questions in offsets 0..399, 29,204 candidate pairs and 807 positives. Confirmation cohorts are question-disjoint but share a 609-document public news corpus; article/source overlap and exclusions from ambiguous gold identity may bias generalization.

### Main advance measured

V11.3 boosted vs V7.1: **+14.330 percentage points**, paired 95% bootstrap CI **[+9.969,+18.692]**; 52 wins / 6 losses on 321 mapped questions (new indices 1200-1599). Approx additive post-index process CPU **6.105ms** for boosted (source GitHub runner), versus 1.293ms fast alone.

V11.4 exact frozen model (new indices 1600-1999) boosted vs V7.1: **+15.522 pp**, paired CI **[+11.642,+19.701]**, 57 wins / 5 losses on 335 mapped questions. Approx additive boosted post-index process CPU **4.597ms** (fast 0.984ms, extra searches 0.940ms, cached features 2.049ms, boosted prediction 0.587ms, final ranking 0.037ms).

Caching was checked against original 23-feature numeric vectors; it reduced feature computation dramatically. Compare CPU across GitHub runners cautiously; these are sum of separately timed process CPU stages, not production end-to-end wall or p95. Training/model selection and cache construction have separate offline costs; neither is zero.

### Long-chain failure remains PRIMARY

- V11.4 4 distinct source documents required: 52 questions. **51/52** full gold source IDs were available in an optimistic up-to-120-document candidate pool, but frozen boosted ranking recovered complete Top5 on **4/52**, V7.1 on **2/52**. Four-source Top10 was 28/52 boosted; context length alone is not sufficient.
- V11.3: 40/42 had all four in pool, boosted AE@5 6/42. V11.2: 44/46 in pool, forest AE@5 6/46. The model has not solved four-plus source assembly, and 4 sources are not logically equivalent to 4-hop entailment.
- In V11, source sentence lexical matches made retrieval worse and added about 35ms of CPU; **text co-mention is not relationship verification**. No true independent verifier or calibrated factual abstention exists.
- V11.3 compared several predeclared known rankers on one cohort; V11.4 independently repeated them on new questions with no tuning, but they share a public corpus. Stronger source/topic-disjoint evidence is mandatory before external generality claims.

## Verified individual runs

- V11 lexical facet: https://github.com/vjgits/Research-Papers/actions/runs/40720291234
- V11.1 learned forest: https://github.com/vjgits/Research-Papers/actions/runs/40721018003
- V11.2 forest replication: https://github.com/vjgits/Research-Papers/actions/runs/40721428101
- V11.3 cached forest/linear/boosted: https://github.com/vjgits/Research-Papers/actions/runs/40721955164
- V11.4 frozen further replication: https://github.com/vjgits/Research-Papers/actions/runs/40722403734

Earlier V11 source commit/negative results: `v7-multihop/V11_NEGATIVE_RESULTS_AND_V111_NEXT_GATE.md`
V11.1 report: `v7-multihop/V111_RESULTS_LIMITATIONS_AND_NEW_COHORT_PLAN.md`
V11.3 report: `v7-multihop/V113_RESULTS_STRONG_CACHED_BOOSTED_RANKING_AND_V114_GATE.md`
V11.4 report: `v7-multihop/V114_REPLICATION_RESULTS_LIMITATIONS_AND_V12_GATES.md`.

## V12 research plan, gated

1. **Generalization audit:** completely new source/article and topic clusters, equal-index/CPU fairness versus BM25/V7.1 and official free/open reranker implementations. Audit 65-79 source-ID exclusions. Preserve full wins and regressions.
2. **Human-evaluated typed edge verifier:** statement, direction, time/negation, source quoted span and independent supported/contradicted/unknown label. Compare edge precision against established NLI models and trivial lexical baselines. No use of gold for online routing.
3. **Evidence-set/chain-selection model:** optimize source necessity/coverage with validated edge scores under strict Top5 and Top10 limits and explicit CPU budget; compare to independent passage ranking and no-verifier control on true 4/5/6/8 logical-hop evaluations. For >5 distinct needed documents, complete Top5 is impossible.
4. **Missing evidence and abstention:** remove or corrupt required sources blind to labels, evaluate missing-support detection and factual answer correctness with selective answer accuracy/coverage; retrieval-completeness proxy is not factual-answer confidence.
5. **Novelty/NeurIPS gate:** prior-art sweep and same-budget matched run against S2G-RAG, GroundRAG, SPARE-RAG, ChainRAG, DEC, ScalableRAG and SAG2; outside sealed independently adjudicated test. No novelty/SOTA claim before these tests.

Supervised ranking, feature caches and boosted trees are **existing IR/ML practice**. PGER's novel contribution, if any, must be isolated by ablations against those existing methods and independently validated. This ledger is deliberately conservative.

No paid API keys, no scheduled tasks, no auto-reviews, no merges and no main writes.
