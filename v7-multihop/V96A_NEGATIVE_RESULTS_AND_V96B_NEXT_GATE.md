# PGER V9.6A: question-anchored and serial source-bridge retrieval — NEGATIVE RESULT

Date: 28 October 2026. Successful one-time GitHub Actions run: https://github.com/vjgits/Research-Papers/actions/runs/40709235010

Full per-question archive: https://github.com/vjgits/Research-Papers/actions/runs/40709235010/artifacts/12825481473

Benchmark code: https://github.com/vjgits/Research-Papers/blob/v96-evidence-anchored-serial-probes-2026-10-28/v7-multihop/benchmark_v96.py

Isolated branch v96-evidence-anchored-serial-probes-2026-10-28; original V9.5 branch and main untouched.

## Purpose and design

Predeclared low-cost candidate discovery experiment. Equal two additional BM25 queries maximum for non-fast arms. Same official SAG2-released documents/questions, unchanged V7.1 initial ranking and identical score-fusion procedure.

Arms:
- V7.1 fast (zero extra searches).
- V9.5 two-query lexical source-expansion control.
- V9.6 question anchors: source-title matches or capitalized entity mentions taken verbatim from the question, not a trained relation detector.
- V9.6 adaptive bridge: first search a question-grounded anchor; select the second query from a named phrase in a retrieved evidence sentence, or another question anchor when the source probe cannot be constructed.

Development offsets 640..759 (previous V9.5 development) and new V9.6 confirmation question offsets 880..999, each with 120 questions per dataset. All 1,000 public SAG2 questions already evaluated with V7.1; therefore neither confirmation nor results constitute genuinely unseen external evidence. Support-count is not logical-hop count.

No paid APIs, models, oracle gold information at inference, deployment, recurring schedules, or workflow actions outside this isolated branch. The witness quotes and source SHA prove source-string provenance, NOT entailment. Existing grounding/extraction, BM25 and question-decomposition ideas are prior art. Novelty not claimed.

## Confirmation results (120 questions per dataset)

Complete gold supporting passage set in Top 5 (AE@5):

| Arm | 2Wiki | MuSiQue | HotpotQA |
|---|---:|---:|---:|
| V7.1 fast | 78/120 = 65.00% | 22/120 = 18.33% | 88/120 = 73.33% |
| V9.5 two-query control | 69/120 = 57.50% | 22/120 = 18.33% | 85/120 = 70.83% |
| V9.6 question anchors | 59/120 = 49.17% | 21/120 = 17.50% | 78/120 = 65.00% |
| V9.6 serial source bridge | 54/120 = 45.00% | 18/120 = 15.00% | 73/120 = 60.83% |

Paired bootstrap 95% question CI for serial source-bridge versus equally budgeted V9.5:
- 2Wiki: -12.50 percentage points (CI [-19.17, -6.67]), 1 win, 16 losses.
- MuSiQue: -3.33 points (CI [-7.50, +0.02]), 1 win, 5 losses.
- HotpotQA: -10.00 points (CI [-16.67, -3.33]), 3 wins, 15 losses.

Question-anchor vs V9.5: 2Wiki -8.33 points, MuSiQue -0.83 points, HotpotQA -5.83 points.

Complete gold support present in candidate workspace (fast Top80 plus extra-query BM25 Top40 hits):
- 2Wiki: V7.1 101/120, V9.5 105/120, question anchors 103/120, serial bridge 103/120.
- MuSiQue: V7.1 64/120, V9.5 76/120, question anchors 65/120, serial bridge 70/120.
- HotpotQA: V7.1 113/120, V9.5 114/120, question anchors 113/120, serial bridge 113/120.

**Critical per-question complementarity audit:** Across all three confirmation datasets, neither V9.6 method obtained *even one* new full-gold candidate pool on a question where V9.5's pool was incomplete. Losses relative to V9.5 in candidate completeness: serial bridge 2/120 2Wiki, 6/120 MuSiQue, 1/120 HotpotQA; question anchors 2, 11, 1 respectively. The new search actions were dominated by unverified named-entity co-occurrence.

Four-support-passage breakdown (not equal to actual logical hops):
- MuSiQue: 17 questions; gold all in candidate pool for 5/17 on V9.5, 3/17 question anchors, 3/17 serial bridge. No arm got 4/4 gold into Top 5 on ANY of the 17. Two different bottlenecks: 12/17 are missing evidence even from V9.5 pool; the other 5/17 are ranking/chain-assembly failures at Top 5.
- 2Wiki: 28 four-support questions; all gold in candidate pool for 20/28 across all arms, yet V7.1 AE@5 9/28, V9.5 2/28, question anchors 0/28 and serial bridge 1/28. The limiting factor is top-ranked chain selection, not merely whether source is present.

## Decision and next grounded changes (not implemented or claimed successful)

Do not promote V9.6A and do not randomly increase query count, tune on confirmation, claim new proof-gap verification, or assert state-of-the-art. Preserve V7.1 and V9.4 reranker as research baselines; V9.6A is a useful failed ablation.

V9.6B should address a **fixed candidate pool**: evidence selection under relationship constraints, requiring source-exact witnesses, typed directionality, explicit negation checks and relation verification. For 2Wiki the gold pool is often sufficient, but existing reranking loses entire chains. Compare against V7.1 and a protected-anchor pure rank baseline on the SAME candidates and CPU budget. Avoid treating titles/co-mentions as entailment. Require a no-relationship-evidence fallback, to prevent catastrophic regressions.

V9.7 source-recovery should be driven by actual diagnosed proof edges, not names alone. Build a POST-HOC error taxonomy from the MuSiQue cases: missing anchor source, absent bridge link, alias/cross-lingual mismatch, wrong relation predicate or direction, query-generation misfocus, BM25 depth cutoff, truly missing corpus evidence. A validated relation verifier is a prerequisite for a "decision-changing proof gap" controller. Compare cheapest useful search to simpler frontier-per-cost controls before novelty claims.

For more than four actual reasoning hops, collect independent human-labeled logical paths and branching problems with missing/contradictory sources. If >5 distinct supporting sources are needed, complete chain@5 is mathematically impossible: test Top 10/adaptive K as well as actual factual answer correctness, calibrated abstention and CPU/latency Pareto frontier. Existing public benchmarks are development, not conclusive scientific validation.

## Timing and reproducibility

Mean additive stage CPU estimates (post-index, not end-to-end wall/answer generation) in confirmation:
- 2Wiki V7.1 1.207ms, V9.5 2.987ms, question anchors 2.879ms, serial bridge 3.702ms.
- MuSiQue V7.1 1.957ms, V9.5 4.984ms, question anchors 4.640ms, serial bridge 5.786ms.
- HotpotQA V7.1 1.758ms, V9.5 4.605ms, question anchors 4.575ms, serial bridge 5.392ms.

Read archived source SHA, question-level logs and original V9.1-V9.5 reports for proper provenance. The additive timing calculation shares ranking overhead across arms, so it is an approximate cost indication, not full end-to-end precision. No independent final-answer evaluation, actual relation entailment verification, or 5/6/8-hop success demonstrated.
