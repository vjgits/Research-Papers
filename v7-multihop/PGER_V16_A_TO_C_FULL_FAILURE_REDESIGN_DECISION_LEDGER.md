# PGER V16A–V16C: architectural source-memory redesign, measured results, and three-system failure learning

**Date:** 2026-10-28
**Current research branch:** `v16c-archive-activation-2026-10-28`
**Main unchanged; no paid API, scheduled task or model-verifier promotion.**

## What was actually built

V16A: A new bounded retrieval loop with 0/1/2/4 rounds, two BM25 source-term searches per round where available, an evidence-frontier with original quoted fact source text and SHA-256, and a query-local token -> source fact adjacency. Every link and proposed gap was explicitly tagged UNVERIFIED. Compare static source-term expansion, dynamic evidence-frontier queries and lexical fact-link candidates with shared Top120 cap.

V16B: Separated an **immutable source-candidate archive** from the 120-source active context. Retrieval cannot delete a previously seen source from the archive; all archived candidates retain original source identity and the corpus file hash. A precommitted cheap two-BM25-search stopping option was measured without modifying other arms, and the monotone-archive invariant passed for every tested turn and question.

V16C: A **second-stage archive-to-active set selector** with 17 gold-independent numeric source/citation/retrieval-history features and a frozen 100-iteration HistGradientBoostingClassifier, trained only on development **EntailmentBank question IDs 400..799**. The scoring cohort is **800..1312**: disjoint from the model's training questions, but its performance was already inspected in V16B; therefore V16C is NOT a new sealed confirmation, cannot claim across-corpus generalization or SOTA. This selector makes no additional search or paid model calls, and never marks a relation entailed.

## Verified runs, archives, and question isolation

- V16A successful: https://github.com/vjgits/Research-Papers/actions/runs/40733656761 ; source per-question archive https://github.com/vjgits/Research-Papers/actions/runs/40733656761/artifacts/12834969104 ; 400 previously unscored science question IDs.
- V16B successful: https://github.com/vjgits/Research-Papers/actions/runs/40734349294 ; https://github.com/vjgits/Research-Papers/actions/runs/40734349294/artifacts/12835867593 ; 513 other question IDs.
- V16C successful: https://github.com/vjgits/Research-Papers/actions/runs/40734975241 ; https://github.com/vjgits/Research-Papers/actions/runs/40734975241/artifacts/12835629094 ; same 513 questions as V16B and already seen in development review.
- V16 and V16B preflight checked V15 three-system postmortem and V13C proof gate. All source statements belong to the released EntailmentBank task1 corpus (11,472 exact-deduplicated source fact statements, CC-BY-4.0). No gold answer, hypothesis, or proof leaf is passed into query generation or test-time ranking.

## V16A causal negative results (N=400, candidate pool cap 120)

| Arm | Extra BM25 calls per q | Complete gold fact sets in active 120 | Four-plus full active pools | Complete@20 | CPU process mean |
|--|--:|--:|--:|--:|--:|
| Initial zero | 0 | 55/400 = 13.75% | 6 | 5.75% | 0.884ms |
| **Static source term H1** | ~2 | **67/400 = 16.75%** | **10** | 6.50% | **1.846ms** |
| Static H4 | ~8 | 59/400 = 14.75% | 10 | 8.25% | 5.065ms |
| Adaptive source frontier H1 | ~2 | 63/400 = 15.75% | 10 | 6.75% | 3.047ms |
| Adaptive source frontier H4 | ~8 | 61/400 = 15.25% | 9 | 7.25% | 8.732ms |
| Adaptive lexical fact-link H4 | ~8 + link lookups | 56/400 = 14.00% | 9 | 4.75% | 9.199ms |

Paired static H1 vs initial improvement +3.000 percentage points, 95% question-bootstrap interval [+1.000,+5.250], wins 15 / losses 3. Dynamic and graph improvements did NOT generalize; reject both as default. Multiple passes sometimes evicted complete sets from active Top120: static H1->H4 lost 17 cases and gained 9; adaptive graph lost 10 and gained 2.

## V16B held-out-question replication and durable source memory (N=513)

| Static expansion | Extra BM25 | Complete active Top120 source sets | Complete durable archive source sets | Four-plus full active | Four-plus full archive | Approx query CPU |
|--|--:|--:|--:|--:|--:|--:|
| H0 | 0 | 53/513 = 10.33% | 53/513 | 9/288 | 9/288 | .85ms |
| H1 | 2 | 65/513 = 12.67% | 68/513 = 13.26% | 11/288 | 14/288 | 1.88ms |
| H2 | 4 | **71/513 = 13.84%** | 83/513 = 16.18% | **14/288** | 19/288 | 2.96ms |
| H4 | 7.97 | 70/513 = 13.65% | **102/513 = 19.88%** | 11/288 | **23/288** | 5.15ms |

H2 active pool vs initial +3.509pp, paired 95% CI [+1.559,+5.653], wins25/losses7. H4 archive increased monotonically while Top120 lost evidence. At H4 **32 questions had all required documents in archive but NOT in active pool**. The archive is an optimistic candidate reservoir, not 102 solved questions. Four-plus complete @20 remains extremely poor.

**Learned lesson:** SAG2 retains earlier sources and S2G extracts compact evidence memory; PGER's fixed-context eviction was a distinct defect. Persistent archive repairs candidate loss at storage level, but does not by itself select a high-quality Top120 subset.

## V16C new archive-activation component test (N=513, **exploratory inspected cohort**)

- Development: 400 different questions, 105,022 archived source training pairs, 1,003 positive gold-source annotations. Classifier's 17 features include original and expanded rank, exact question/source term overlap, query action hit counts/ranks, source witness status, and source-token overlap; all available without gold at inference.
- Both learned variants use EXACTLY the same existing H4 source archive as the unchanged baseline; no extra search. One protects five baseline anchors, the other doesn't.
- **Complete source fact set in active Top120: unchanged H4 70/513 (13.65%); learned selector 81/513 (15.79%).**
- Paired delta **+2.144pp**, 95% bootstrap CI **[+0.390,+3.899]**, 16 wins and 5 losses against unchanged H4.
- Four-plus exact fact cases n288: H4 baseline **11/288** full active pool; learned selector **15/288**. Complete fact set @20 increases **0/288 -> 2/288** in this subgroup.
- Overall final complete @20 **unchanged 6.4327%** with 6 paired wins and 6 losses; CI for overall delta [-1.365,+1.365] pp. Do not claim a general answer/reasoning improvement.
- H4 query sourcing CPU about 4.703ms per scored question in this V16C run; activation features **2.262ms** plus classifier/ranking **1.002ms** = **~7.97ms additive process CPU per question**, offline source indexing and classifier fitting separate. Cost ~69% above H4 retrieval alone in this run, not validated production wall p95. No full official external-system cost/accuracy parity.

**Decision:** This is a **provisional positive source-context activation component**. Keep persistent archive and learned activation code on isolated research branch. Do NOT promote it as global PGER default or claim it is faster/better than SAG2/HippoRAG2/S2G: those original complete pipelines have not been run under matched hardware and metrics. No production evidence proof/answer is obtained; default V13C proof gate still requires independently authorized relation validation and otherwise ABSTAINS.

## Mandatory comparison with all three original architectures

- **SAG2:** official source https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py ; BM25 + contextual JEV evidence necessity, retained evidence frontier, two term expansion rounds, optional DPP rerank. V16 has evidence frontier and retention but **NO validated JEV-equivalent contextual necessity judge**. The learned archive scorer predicts gold *source membership* from source/question features, not whether a source establishes a necessary semantic relation. Repeated searches without necessity verification can drift.
- **HippoRAG 2:** official source https://github.com/OSU-NLP-Group/HippoRAG/blob/main/src/hipporag/HippoRAG.py ; OpenIE fact/entity/phrase graph, embeddings and query-seeded PPR over typed/fact-connected source memory. V16 token adjacency is not a typed fact graph and **hurt** when used indiscriminately. Never call this official HippoRAG result.
- **S2G-RAG:** https://github.com/nianaaa/S2G-RAG/blob/main/inference/inference_bm25.py ; trained sufficiency/missing-proposition judge, exact sentence-pointer evidence extractor and bounded follow-up turns. V16 evidence archive fixes context eviction but **does not include a trained and externally validated sufficiency/gap judge**. The V13B MiniLM checkpoint had 70.4% false entailment on HANS and cannot approve proof edges.

## Next falsifiable research gate (V17)

1. **Stop benchmark saturation.** EntailmentBank public test is repeatedly inspected; even the 513 train question cohort has now been inspected. Acquire a source/topic-disjoint, human-labeled 4/5/6/8+ logical-hop benchmark and freeze sealed question IDs. No claim of independent generalization otherwise.
2. **Validate typed missing-fact / edge proposal precision** against independently adjudicated true, false and unknown source-to-source relationships. Do not confuse lexical overlap or co-necessity with entailment.
3. **Necessity-aware, context-size-aware working-set selection**, using the persistent archive and retained signed source witnesses. Compare against standard gradient-boosted per-source ranking and official open rerankers under identical CPU/memory/TopK limits.
4. **Gold-independent stop/routing decision:** learn from development trajectories whether 0/1/2/4-round search is worthwhile given observed marginal source discovery and gap uncertainty; compare with fixed H1/H2 and static BM25 using selective accuracy/coverage, p95 wall and offline index cost.
5. **Real head-to-head:** benchmark official SAG2/HippoRAG2/S2G with their correct JEV/OpenIE/learned judge dependencies under published metrics and matched cost; do not manufacture industry superiority.

The research objective (best in industry, reliable 4+ hops, 90-95% answer correctness) is NOT yet achieved. This iteration demonstrates a meaningful narrow gain in active evidence selection and better memory integrity while documenting severe remaining weaknesses.

No paid API, auto-merge, main changes, recurring tasks, reviewer forgery, or source truth overclaims.
