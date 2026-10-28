# PGER V7.2: Fresh Question-Disjoint Evaluation — NEGATIVE MEMORY RESULT
**Date:** 2026-10-27 Pacific / 2026-10-28 UTC  
**Branch:** `v72-proof-gap-relation-ledger-2026-10-27`  
**Reproducible run:** https://github.com/vjgits/Research-Papers/actions/runs/40610829554  
**Full artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40610829554/artifacts/12782766998

## Executive verdict

The V7.2 deterministic, source-offset-backed *surface-relation* ledger did **not** improve complete-chain recovery over the exactly matched reset/no-memory controller. Both arms had identical paired outcomes at **Top 5 and Top 10 for every one of the 400 questions**. This result refutes a benefit of the tested relation-retention scoring, not the broader possibility that genuine semantic subclaim memory is useful.

The common V7.2 controller slightly improves Top 10 relative to fast V7.1 graph for 2Wiki but adds ~1.3–1.6 ms per query and approximately two extra BM25 calls. MuSiQue 3-/4-support failures are largely unresolved.

## Protocol

- **Fresh question IDs:** 2Wiki validation valid positions 481–720 (n=240), MuSiQue validation valid positions 161–320 (n=160), selected with original deterministic V7/V7.1 sort seeds. Public question-disjoint validation, **not sealed or a new external benchmark**.
- **Pooled corpus:** 1,809 title-deduplicated 2Wiki pages; 2,538 MuSiQue support/distractor paragraphs, with gold documents present in each pool by construction.
- **Four arms:** BM25, exactly reused V7.1 indexed 1-hop BM25 graph, V7.2 identical candidate generation with reset memory, V7.2 identical candidate generation with retained relation ledger.
- **Budget:** same gate, shared candidate set, max 2 extra BM25 queries, 3 relation expansions, beam 8, fanout 8, Top 5/10 for memory and reset. No paid APIs, LLM generation, human reviewers, IRCoT or HippoRAG reproduction.
- **Metrics:** complete annotated source-chain recovery, not answer correctness; pairs bootstrap using 5,000 query resamples, seed 20261027. Index build and post-index CPU query-path times separately.

## Fresh complete-chain results

| Method | 2Wiki n=240 @5 | 2Wiki @10 | MuSiQue n=160 @5 | MuSiQue @10 |
|---|---:|---:|---:|---:|
| BM25 | 92 (38.33%) | 125 (52.08%) | 22 (13.75%) | 34 (21.25%) |
| V7.1 fast BM25+indexed graph | 183 (76.25%) | 198 (82.50%) | 27 (16.88%) | 41 (25.63%) |
| V7.2 reset/no-memory | 181 (75.42%) | 208 (86.67%) | 27 (16.88%) | 44 (27.50%) |
| V7.2 retained relation ledger | 181 (75.42%) | 208 (86.67%) | 27 (16.88%) | 44 (27.50%) |

### Paired effects (V7.2 retained vs V7.1 fast graph)
| Dataset | K | Difference (pp) | Paired bootstrap 95% CI (pp) | Wins / losses |
|---|---:|---:|---:|---:|
| 2Wiki | 5 | −0.83 | [−4.17,+2.92] | 8 / 10 |
| 2Wiki | 10 | +4.17 | [+1.67,+7.08] | 11 / 1 |
| MuSiQue | 5 | 0.00 | [−3.13,+3.13] | 3 / 3 |
| MuSiQue | 10 | +1.88 | [−2.50,+6.88] | 9 / 6 |

**Retained vs reset:** exactly 0.00 pp at K=5 and K=10 on each dataset, paired wins/losses 0/0, empirical paired bootstrap [0,0] on these observed samples. This degenerate interval does not establish that the methods will always match on unseen distributions.

### Hard chains: complete / total
| Dataset, support documents | Fast graph @5/@10 | V7.2 ledger @5/@10 |
|---|---|---|
| 2Wiki, four (n=50) | 30/50; 36/50 | 30/50; 38/50 |
| MuSiQue, three (n=60) | 1/60; 5/60 | 1/60; 5/60 |
| MuSiQue, four (n=28) | 0/28; 0/28 | 0/28; 1/28 |

The 2Wiki majority remains comparatively easy title-linked retrieval. Four-support MuSiQue @5 is **0/28** and is not solved.

## Document-miss audit (post-retrieval only)

Missed gold **document occurrences** at Top 5, not number of failed questions:

| Dataset | Gold doc considered but outside Top 5 | Outside common candidate pool | Other reachable title edge not in candidate pool |
|---|---:|---:|---:|
| 2Wiki (all support groups) | 49 | 21 | 0 |
| MuSiQue (all support groups) | 157 | 88 | 2 |
| MuSiQue, three-source only | 73 | 30 | 2 |
| MuSiQue, four-source only | 46 | 34 | 0 |

Interpretation: ranking is an important problem, but missing candidate coverage remains substantial, especially in 4-source MuSiQue. These are instrumented diagnostic labels, not manual adjudications of missing semantic relationships.

Concrete failures:
- 2Wiki question "Which film has the director who was born earlier, Legend Of The Inca Bridge or Gangs Of New York?" missed gold director **José A. Ferreyra** at Top 5 even though the candidate was considered. The controller instead elevated other distractors.
- 2Wiki "Which film has the director who was born later, High Tension or The Man In The Net?" missed **Michael Curtiz** and **The Man in the Net** at Top 5 despite consideration.
- MuSiQue 4-source "Where is the district that the person who wanted to reform and address the religion that practices altarage preach a sermon on Marian devotion before his death located?" lacked **Wittenberg (district)** in the shared candidate pool and considered **Altarage** below Top 5.
- MuSiQue 4-source "Who won the Indy Car Race in the largest populated city of the state where the performer of Tijuana Moods is from?" ranked relevant **Tucson, Arizona** and **Desert Diamond West Valley Phoenix Grand Prix** outside Top 5 despite their presence in candidates.

Gold-related data anomalies were not independently audited; source/title examples are diagnostic, not asserted factual answers.

## CPU costs (shared-process GitHub runner, after indexing; ms/query mean)

| Dataset | BM25 | Fast graph extra | V7.2 shared follow-up extra | V7.2 retained scoring extra | Fast total approx | V7.2 total approx |
|---|---:|---:|---:|---:|---:|---:|
| 2Wiki | 0.571 | 0.412 | 1.037 | 0.291 | 0.983 | 2.311 |
| MuSiQue | 0.680 | 0.264 | 1.298 | 0.320 | 0.944 | 2.562 |

Both V7.2 memory/reset arms run a mean **1.858 extra BM25 queries** (2Wiki) and **1.950 extra** (MuSiQue). Reset arm mean extra scoring: ~0.310 ms / 0.356 ms, versus retained ~0.291 ms / 0.320 ms. These small shared-run differences are **not a demonstrated speedup**.

Offline index builds: 2Wiki BM25 **0.407 s**, V7.1 title graph **0.029 s**, V7.2 surface-relation index **0.283 s**. MuSiQue BM25 **0.610 s**, title graph **0.050 s**, relation index **0.531 s**. Timings exclude process startup, data downloads, source extraction, generator/reader, deployment and serving overhead. Do not compare these numbers to V7.1's runner times as if they were normalized hardware experiments.

## Provenance and novelty caveats

The source-offset invariant passed for all extracted links. However, **span existence is not fact entailment**. Only **85 of 923** extracted 2Wiki surface edges and **30 of 1,836** MuSiQue edges carried even the prototype's directional cue flag; all remaining edges were weak topical associations. The edge trails preserve source quote offsets and dependency predecessors but do not constitute a robust semantic claim parser or proof of support/contradiction. Potential conflict count was zero, without evidence this detects real disagreements.

Existing methods BM25, Aho-Corasick, title-link extraction, traversal, query gating, relation cues and source provenance are not novel. The full hypothesis—identify a decision-changing missing sourced relationship, retrieve discriminating evidence, and abstain cost-effectively—**remains unproven**. A credible subsequent experiment requires improved *semantic* subclaim inference, inverse candidate search (not mere graph reachability), matched costs, an independently sealed test and a fixed grounded answer reader. No SOTA claim.

## Bottom line

**V7.2 retained-memory hypothesis: not supported.** The modest Top-10 gain for 2Wiki reflects the shared controller, not memory. At Top 5 there is no overall improvement over the cheap graph, and MuSiQue 4-hop retrieval remains the key open challenge. Avoid progressing to a publishable novelty claim until the missing-relationship test yields a clear matched-budget gain.
