# PGER V7.3–V8.2: fresh public-validation evaluation (negative end-to-end result)
**Study date:** October 27, 2026 (Pacific) / October 28 UTC  
**Run:** https://github.com/vjgits/Research-Papers/actions/runs/40616913946  
**Artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40616913946/artifacts/12786125478  
**Branch:** `v8-adaptive-proofgap-2026-10-27`

## Verdict
The extended candidate rescue recovered more annotated supporting sources *within the candidate pool* but **no proposed final V8 method beat the unchanged fast V7.1 BM25+indexed one-hop graph at Top 5**. A key bottleneck is promoting the right candidates into the final Top 5 rather than blindly expanding candidates and graph walks. V8.1 still fails on every 4-source MuSiQue example at Top 5. This is a negative result. Do not claim new SOTA, general semantic reasoning or validated 8-hop accuracy.

## Data and methods
- New, question-ID-disjoint slices from the same repeatedly inspected **public validation** datasets, not sealed independent tests: deterministic eligible 2Wiki positions 721–960 (240 queries, 1,806 pooled source pages) and MuSiQue positions 321–480 (160 queries, 2,643 pooled paragraphs). Gold docs are in pooled corpora by construction, not open-Web retrieval.
- Baselines: BM25, V7.1 original indexed BM25+title-reference graph (unmodified). V7.3 lexical controls and candidate rescue each make exactly **two additional BM25 queries**, but not necessarily equal CPU cost. V8.0 joint greedy chain reranking and V8.1 proof-gap heuristics receive precisely the same rescued candidate pool. V8.2 selectively uses the fast path.
- Unit tests: 6/6 plus smoke passed. Source provenance and synthetic 8-step traversal checks do NOT establish entailment or natural-language 5–8-hop question answering. There is no fixed answer generator, no calibrated abstention, no official IRCoT/HippoRAG2 execution, and no paid APIs/reviewers.

## Retrieval results
### Complete annotated evidence chain within Top K
| Method | 2Wiki @5 (n=240) | 2Wiki @10 | MuSiQue @5 (n=160) | MuSiQue @10 |
|---|---:|---:|---:|---:|
| BM25 | 37.50% | 47.50% | 13.75% | 20.63% |
| **V7.1 fast** | **73.33%** | **83.75%** | **21.88%** | **36.25%** |
| V7.3 lexical control | 40.00% | 53.33% | 13.13% | 22.50% |
| V7.3 targeted rescue | 40.42% | 53.75% | 13.13% | 22.50% |
| V8.0 joint greedy rank | 65.83% | 82.50% | 18.75% | 28.75% |
| V8.1 heuristic proof-gap rank | 72.92% | 82.92% | 20.00% | 27.50% |
| V8.2 adaptive | 72.92% | 82.92% | 20.00% | 27.50% |

V8.2 vs fast V7.1 Top 5: 2Wiki −0.42 percentage points, paired 95% bootstrap CI [−5.42,+4.17], wins/losses 15/16; MuSiQue −1.88 points, CI [−6.25,+2.50], wins/losses 5/8. At Top 10: 2Wiki −0.83, CI [−5.00,+3.33]; MuSiQue **−8.75 points**, CI [−14.38,−3.13]. The last result is a material regression on this development cohort.

### Candidate-recall audit (separate from Top-K ranking)
| Dataset | Matched lexical-control pool | Targeted rescue pool | Improvement | Full gold chains in rescued pool |
|---|---:|---:|---:|---:|
| 2Wiki | 95.42% mean gold-source recall | 98.75% | +3.33 pp (95% paired CI [+1.98,+4.90]) | 233/240 |
| MuSiQue | 88.28% | 91.35% | +3.07 pp (95% paired CI [+0.68,+5.47]) | 128/160 |

For 2Wiki, 21 queries gained candidate coverage and none lost; for MuSiQue, 18 gained and 8 lost. Different candidate sources under capped pooled candidate selection can displace candidates despite equal BM25 search calls. **Candidate coverage is an oracle diagnostic, not ranking quality.** V7.3 rescue alone wins only 1/240 2Wiki complete chains and 0/160 MuSiQue complete chains relative to the lexical control at Top 5.

### Hard chains
- 2Wiki 4 sources, n=54: fast V7.1 25/54 @5 and 39/54 @10; V8.1 24/54 @5 and 33/54 @10.
- MuSiQue 3 sources, n=51: fast 5/51 @5 and 13/51 @10; V8.1 5/51 @5 and 8/51 @10.
- MuSiQue 4 sources, n=28: fast 1/28 @5 and 5/28 @10; V8.1 **0/28 @5** and 3/28 @10.

Detailed post-hoc diagnostic: in MuSiQue, the rescued pool contains full gold source sets for **128/160** questions but V8.1 returns only **32/160** full chains at Top 5; among 4-source questions, 15/28 have full gold in rescue candidates yet V8.1 completes 0/28 at Top 5. This strongly indicates a ranking/evidence-selection bottleneck, while 32 other queries still have candidate coverage problems.

## Query cost and adaptive routing
| Dataset | Fast V7.1 mean path | V8.2 mean path | Cost ratio |
|---|---:|---:|---:|
| 2Wiki | 0.638 ms | 7.468 ms | ~11.7x |
| MuSiQue | 0.827 ms | 9.414 ms | ~11.4x |

These are approximate sequential shared-run CPU post-index paths, not production latency, and exclude downloading, startup, generation and index build. V8.2 routed only 7/240 2Wiki and 0/160 MuSiQue queries onto the cheap path; it is not meaningfully adaptive. Additional offline indexes added construction costs: 2Wiki BM25 0.257 s, graph 0.025 s, relation index 0.210 s, reverse index 0.280 s; MuSiQue 0.405 / 0.045 / 0.404 / 0.472 s respectively. Do not compare these times as normalized production measurements.

## Root cause and recommended decision
1. **Reject V8.2 as a replacement** for fast V7.1: poorer accuracy, much slower.
2. Retain V7.3's candidate recall improvement as a *retrieval-stage observation only*, not as a complete-system gain. Keep source provenance logs.
3. The greedy V8.0 reranker promotes weak topical associations and question-token coverage. Those signals do not establish which passages compose the correct intermediate relation chain. V8.1 heuristics partly recover V8.0 regressions but not the robust original baseline.
4. A post-hoc rank-fusion experiment using only the already-seen Top-10 rankings did not demonstrate a consistent advantage and **is exploratory/tuned**, not independent new evidence.
5. Keep the fast V7.1 output as the safe default until an independently held-out semantic/learned *subclaim-to-source* ranker or grounded answer reader proves a gain. Consider open-weight cross-encoder/multilingual retrieval *as a known comparator*, not an original algorithm. Validate precise entailment and answer-changing proof gaps separately.
6. Next stages must report semantic extraction accuracy, exact source-span fidelity, relation-type errors, candidate recall, Top 5/10, mean/p95 latency, offline indexing, CPU/tokens, and final reader answer accuracy on a newly sealed dataset. A synthetic 8-edge graph unit test does not prove 8-hop question answering.

**Conclusion:** candidate discovery partly improved; candidate-to-chain selection failed to improve. No demonstrated V8 novelty or state-of-the-art performance.
