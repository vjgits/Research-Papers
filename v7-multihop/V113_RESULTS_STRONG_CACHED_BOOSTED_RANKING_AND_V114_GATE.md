# PGER V11.3: cached features and efficient learned ranker — first strong accuracy/CPU frontier improvement on this public corpus

**Date 2026-10-28. Successful Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40721955164
**Full question-level archive:** https://github.com/vjgits/Research-Papers/actions/runs/40721955164/artifacts/12829934782
**Branch:** v113-cached-efficient-rankers-2026-10-28. Main unchanged.

## Frozen method and separated evidence

The same 609-news article MultiHop-RAG corpus (ODC-BY). Exactly the 316 development questions at original offsets 0..399, 29,204 supervised candidate pairs with 807 gold positives, and the same V11.1 <=120-document candidate pool and 23 numeric query/document features. A document-level text-token cache is built before queries; parity against the original feature implementation was asserted on a predeclared subset. Three standard prior-art classifiers (no parameter sweeps): identical earlier 120-tree RandomForest, balanced logistic regression, and balanced HistGradientBoostingClassifier with 100 iterations, 15 leaves, learning rate 0.08, L2 1.0. No ground-truth IDs or label signals enter confirmation ranking. New question offset 1200..1599, **321/400 unambiguously mapped**, 79 skipped. This is question-disjoint from prior PGER evaluations but shares public corpus/articles, not a sealed source-disjoint benchmark.

## Confirmation (n=321), full annotated support source identity in Top5 / Top10

| Method | AE@5 | AE@10 | Two support (n=173) | Three (n=106) | Four (n=42) |
|---|---:|---:|---:|---:|---:|
| plain BM25 | 44.5483% | 63.5514% | 115 | 25 | 3 |
| V7.1 fast | 44.2368% | 63.5514% | 115 | 24 | 3 |
| cached RandomForest | 55.4517% | 75.7009% | 136 | 36 | 6 |
| cached logistic | 54.5171% | 73.2087% | 139 | 33 | 3 |
| **cached boosted tree** | **58.5670%** | **77.5701%** | 138 | 44 | 6 |

Paired boosted versus V7.1: **+14.330 pp**, 95% question bootstrap CI **[+9.969,+18.692]**, 52 wins, 6 losses.
Boosted vs RandomForest: +3.115 pp, CI [0.000,+6.238], 19 wins, 9 losses. Compared with the linear baseline: +4.050 pp, CI [+0.935,+7.165], 19 wins, 6 losses. Multiple comparisons on a single public cohort limit any model-selection claim; independent frozen replication is essential.

## CPU accounting (github hosted runner; separate measured additive process-time stages)

| Component | Mean CPU ms |
|---|---:|
| Initial BM25+V7.1 graph | 1.293 |
| Two extra facet BM25 searches | 1.578 |
| Per-query cached 23-feature extraction | **2.534** |
| RandomForest prediction | 17.849 |
| Logistic prediction | 0.446 |
| Boosted prediction | **0.652** |
| Lightweight final reranking | ~0.05 for boosted/linear; 0.066 for forest |

Mean approximate post-index per-query totals (sum of separately timed components): **boosted 6.105ms**, **logistic 5.901ms**, **forest 23.320ms**. This is ~4x V7.1 latency for the boosted arm, not fastest ever; but within this *specific* study it delivers materially better quality at far less cost than the earlier 120-tree approach.

Offline cache build **75.3 CPU-ms**, BM25 index **1,876 CPU-ms**, title graph **208.5 CPU-ms**; model fit cost boosted **838.7 CPU-ms**, forest 2,252 CPU-ms, linear 129 CPU-ms. Source data and query batches are small; this is not a production serving benchmark. CPU times may differ across GitHub workers; p95 and code in archived source.

## Key negatives / no novelty inflation

- Four-support complete Top5 still **6/42** despite 40/42 all gold in a broad up-to-120-document candidate pool. Actual verified relation/hop reasoning and answer correctness are NOT evaluated.
- Learned ranking and caching are mature prior art. No originality/SOTA assertion, no matched official SAG2/ScalableRAG/S2G-RAG/ChainRAG/DEC/SPARE-RAG reimplementation.
- Public news corpus is reused, with potential overlapping sources/topics between train and new question IDs. Question-disjoint DOES NOT imply source-disjoint.
- Benchmark evidence mappings exclude 79 unresolved question IDs, so reported scores are conditional.
- All prior V7–V11.2 findings preserved, including failed semantic/search methods.

## Strict V11.4 next gate

Without tuning or changing parameters, retrain these same frozen models on development 0..399 and score previously unexamined question offsets 1600..1999 (same source corpus). Require boosted quality gain vs BM25/V7.1 to persist, with four-support breakdown and cost included. If not, reject any 'best model' claim. Subsequently test blocked-by-source generalization and true relationship entailment on human-audited 4/5/6/8-hop chains.

No paid APIs, scheduled scans, merges, main writes or deployment.
