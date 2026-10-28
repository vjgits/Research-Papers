# PGER V11.1 — development-only source-ranker: substantial evidence selection gain, 4-source still unsolved

**Date:** 2026-10-28. **Successful GitHub Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40721018003 . **All question-level case records:** https://github.com/vjgits/Research-Papers/actions/runs/40721018003/artifacts/12829413981 .
**Branch:** v111-trained-candidate-reranker-2026-10-28. Main/original prior findings untouched.

## Exact experimental protocol
ODC-BY MultiHop-RAG news corpus (609 distinct articles). Source identities mapped exactly by URL or unique title; ambiguous cases excluded. Only 316 mapped development questions in offsets 0..399 used gold source IDs to label 29,204 document pairs (807 positives) in the same <=120 document pool. Frozen RandomForestClassifier, 120 estimators, max_depth 10, min_samples_leaf 5, balanced_subsample, 23 lexical/metadata/rank features. Training and inference code does not use confirmation gold before ranking. Confirmation offsets 400..799: 323 mapped questions; 77 unresolved excluded. Dataset/public confirmation already inspected in V10.1 and V11, therefore **not a sealed independent test**, and training/confirmation may share underlying news articles/topics.

## V11.1 confirmation source-document complete evidence@5

| Arm | AE@5 | AE@10 | Two-support (n=164) | Three-support (n=105) | Four-support (n=54) |
|---|---:|---:|---:|---:|---:|
| BM25 | 40.5573% | 63.1579% | 110 | 20 | 1 |
| V7.1 fast | 39.6285% | 62.8483% | 109 | 18 | 1 |
| V11 2-facet fusion | 39.9381% | 62.2291% | 109 | 19 | 1 |
| V11.1 learned pointwise | **50.4644%** | **69.9690%** | **130** | **31** | **2** |
| Learned with fast anchor | 50.1548% | 69.9690% | 129 | 31 | 2 |
| Learned + facet-diversity | 50.4644% | 69.9690% | 130 | 31 | 2 |

Paired pointwise vs V7.1: **+10.836 pp**, 95% question-bootstrap interval **[+7.121,+14.861]**, 41 wins, 6 losses. Pointwise vs BM25: +9.907 pp [5.882,13.932], 39 wins, 7 losses. Against lexical facet fusion: +10.526 pp [6.502,14.551]. One pre-committed model, no result-driven parameter search. Learned facet diversity added **zero** measurable improvement; no basis to promote it.

### Crucial four-source shortfall

In the frozen <=120-document candidate pool, all 4 gold source IDs were available for **53/54** questions; the learned model assembled complete AE@5 on only **2/54**, versus fast baseline **1/54**. Therefore the system remains far from general reliable four-source chain assembly. High pool recall alone is not a complete-chain algorithm and 4 source documents is not equivalent to 4 verified semantic reasoning hops.

### CPU and cost

Frozen model fitting **3.116 CPU seconds** on 29,204 candidate pairs; offline BM25/index build separate.
Mean per scored confirmation query: initial V7.1 **1.290 ms**, two facet searches **1.418 ms**, 23-feature extraction **13.353 ms**, trained model prediction **16.484 ms**, rerank **3.310 ms**. This is ~35.86ms additive process CPU, not interactive wall/p95 or deployment cost, and ~27x the initial fast retrieval. Means/p95 in original archived JSON; no budget-normalized Pareto dominance demonstrated. Training labels and feature type are standard retrieval prior art, not a new PGER algorithm.

## Decision and feedback

**Conditional research gain:** meaningful within-public-cohort Top5 chain selection on 2-3-source cases, but **does NOT meet** 4-source reliability or efficiency objectives. Preserve V7.1 as fast default; learned reranker remains experimental. No generated answers, true relation entailment, or 5/6/8+ hop proof. No credible scientific novelty claim.

**Next V11.2 gate:** without changing hyperparameters/model/features, train on exactly the same 0..399 development questions and evaluate a *previously unexamined-by-PGER* question cohort (800..1199) in the same official corpus; report paired results and four-source cases. Questions disjoint but articles/topics may overlap; this is a stronger internal replication, not a sealed independent corpus. If gains fail, record negative and do not tune the new cohort. Then evaluate source/article-disjoint transfer and independent relation entailment before promoting any complex controller.

No paid APIs, automation schedules, main changes, merges or deployment. All V7-V11 prior positive and negative findings preserved.
