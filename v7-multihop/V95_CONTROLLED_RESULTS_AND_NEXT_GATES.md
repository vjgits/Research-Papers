# PGER V9.5: controlled set-workspace trial — negative universal result

**Date:** 2026-10-28. **GitHub Actions success:** https://github.com/vjgits/Research-Papers/actions/runs/40702067093
**Per-question archive:** https://github.com/vjgits/Research-Papers/actions/runs/40702067093/artifacts/12823350211
**Frozen benchmark source:** https://github.com/vjgits/Research-Papers/blob/v95-controlled-set-benchmark-2026-10-28/v7-multihop/benchmark_v95_controlled.py

## Exact status and source integrity
Successful isolated-branch run; main and original V9.5 branch untouched. Official SAG2-released source corpus/questions at pinned HippoRAG2 release 5ec05b38deecc3318bb432c69865959c56058990. 120 development questions (offsets 640-759) and 120 further confirmation questions (760-879) per dataset: 720 unique question evaluations, five arms on each. The first 1,000 questions have been evaluated in earlier public V7.1 work; this is **NOT independently sealed testing**.

No gold is used in retrieval. Same source IDs, metric and fixed corpus; max two additional BM25 searches per non-fast arm, zero neural calls or paid APIs. The V9.2-style two-query control is *not* the original V9.2 eight-query code or equivalent original budget. Two set-workspace arms share retrieval actions, differing only in positive-only ranking versus retained excluded/negative-set rescue. The lexical-gap arm has no relation verifier and must never be called a demonstrated counterfactual controller. Exact-string matches prove textual occurrence, not semantic relation entailment. Named set operations are ScalableRAG prior art.

## Confirmation results (n=120 per dataset): all support sources in Top 5

| Arm | 2Wiki | MuSiQue | HotpotQA |
|---|---:|---:|---:|
| V7.1 fast | 87 (72.50%) | 16 (13.33%) | 75 (62.50%) |
| two BM25 search control | 71 (59.17%) | 17 (14.17%) | 75 (62.50%) |
| positive-only workspace | 69 (57.50%) | 25 (20.83%) | 72 (60.00%) |
| positive+negative retained | 80 (66.67%) | 18 (15.00%) | 74 (61.67%) |
| lexical gap controller | 71 (59.17%) | 17 (14.17%) | 75 (62.50%) |

Paired 95% question-bootstrap CIs vs unchanged V7.1:
- Positive-only MuSiQue +7.50pp [2.48, 13.33], 11 wins/2 losses; 2Wiki -15.00pp [-21.67, -8.33], 1 win/19 losses; Hotpot -2.50pp [-6.67, 1.67].
- Retained-negative MuSiQue +1.67pp [-1.67, 5.00]; 2Wiki -5.83pp [-10.83, -0.83]; Hotpot -0.83pp [-4.17, 1.67].
- Retained-negative versus positive-only on 2Wiki +9.17pp [2.50, 15.83], but still fails to beat V7.1.

Mean additive process CPU query estimates on GitHub runner:
- 2Wiki: V7.1 1.215ms; positive-only 5.677ms; retained-negative 9.806ms.
- MuSiQue: V7.1 1.980ms; positive-only 8.146ms; retained-negative 13.152ms.
- HotpotQA: V7.1 1.750ms; positive-only 8.035ms; retained-negative 13.416ms.
These exclude offline indexing and answer generation; not equivalent to production latency.

## Key four-support question audit on confirmation

- **MuSiQue**: 17 four-support questions. Full support evidence in first-pass Top 80 for 1/17, in the shared two-search pool for 1/17 and in positive lexical partition for 0/17. Every tested arm had **0/17** complete chain@5. Main immediate bottleneck: discover missing candidate sources.
- **2Wiki**: 28 four-support questions. All support sources in first-pass Top80 for 24/28, in shared two-search pool for 24/28 and in strictly positive lexical partition for 0/28. Chain@5: V7.1 **16/28**; positive-only **3/28**; retained-negative **12/28**. Main bottleneck: relation-aware selection and false positive-filter exclusion. Negative complement reduces this failure but not enough.
- The lexical-gap and two-query V9.2-style arms had identical evaluation metrics for all 360 confirmation cases and mostly identical Top10 rankings; no distinct benefit.

**Verdict:** V9.5 FAILS its predeclared requirement of better chain@5 than V7.1 and equal-budget controls with no easy-task regression and better CPU-quality frontier. Do not replace V7.1 or claim novelty, world-leading performance, successful 4+ hops, answer correctness, or factual entailment. Original V9.4 Ettin retains its component role for selected difficult questions but was expensive and regressed on 2Wiki.

## Research next gates, ONE grounded change at a time

**V9.6A candidate recovery:** On four-source MuSiQue, label post-hoc reasons for absent gold passages in two-search pool: entity alias, wrong witness, relation unstated, query not proposed, retrieval result beyond depth 40. Make one evidence-anchored *typed subquestion* generator and compare to two-query control at the SAME two-call budget, same ranking. No regex-only relation claim or REBEL by default; REBEL archived recall was low and licensing constrained.

**V9.6B chain assembly:** On a fixed candidate pool with complete gold already available, compare existing relevance scoring to source-grounded relation-edge consistency, constrained passage bundles, and diversity/necessity under matched CPU and model-scoring budgets. Candidate-full gold ceiling is post-hoc diagnostics only, not online oracle. Validate semantic relation/negation independently: title links and co-mentions are NOT entailment.

**V9.7 true decision-gap controller:** Only after a verifier achieves adequate calibrated edge precision, maintain supported/refuted/unknown relations and source-provenance; choose search by predicted answer-changing utility / CPU cost, compete with frontier-per-cost, simple uncertainty and S2G-RAG. Require controlled policy gains, not synthetic graph-only success.

**V10 robust 5/6/8+ hops and missing information:** Build independently human-audited actual logical-hop corpus across chains, fan-out, aliases, conflicting versions, missing/partial evidence and distractors. Support count is NOT logical hop count. If more than five DISTINCT sources are necessary, AE@5 is mathematically impossible: use AE@10 or adaptive K>=required support count alongside answer accuracy, grounding and abstention. MoreHopQA and FanOutQA offer existing complementary tasks but do not alone certify 8 hops.

**V11 state-of-art/efficiency claim gate:** Reproduce official free/open-weight baselines using identical hardware, corpus/query IDs, scoring budgets and end-to-end CPU/wall. Explicitly compare ScalableRAG, SAG2, S2G-RAG, AdaKG-RAG, A2RAG, HippoRAG, IRCoT and strong contemporary methods. Report chain@5/@10, partial recall, answer EM/F1, quote provenance versus independent entailment, accuracy/coverage calibration, p95 latency, RAM, cold indexing and Pareto frontier with paired confidence intervals and multiple-test corrections. Conduct a sealed independent evaluation before scientific SOTA or NeurIPS claims.

No paid API, no scheduled scans, no reviewer agents, no deployment, no main changes, no retroactive overwriting of earlier negative experiments. Preserve the complete question-level archive.
