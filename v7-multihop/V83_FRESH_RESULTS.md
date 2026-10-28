# PGER V8.3: Conservative Grounded Source-Bridge Evaluation
Date: 2026-10-27 Pacific / 2026-10-28 UTC

**Branch:** `v83-guarded-source-bridge-2026-10-27`
**Run:** https://github.com/vjgits/Research-Papers/actions/runs/40618155158
**Per-question artifacts:** https://github.com/vjgits/Research-Papers/actions/runs/40618155158/artifacts/12786321806

## Verdict
A narrow high-precision intervention **improved 2Wiki complete-chain@5**, while leaving MuSiQue unchanged. The result does *not* validate a general proof-gap algorithm. The gain uses known exact question-title entity matching and source-linked graph transitions (not novel by themselves). The next challenge remains implicit paragraph relations and multi-hop fact extraction.

## Frozen protocol
- 2Wiki public validation selected positions 961–1200 (240 fresh question IDs; pooled corpus 1,723 docs); MuSiQue public validation positions 481–640 (160 fresh IDs; 2,696 pooled paragraphs).
- Same original BM25 and unchanged V7.1 fast BM25+indexed 1-hop graph for all arms. V8.3 builds an offline exact title-index and a sourced relation-mention index.
- It switches from original ranking *only if* the question explicitly names two different document titles, asks a comparison, and each title page has a document-reference edge with the right observed relation cue (director, producer, etc.) and a valid exact source span.
- Rank otherwise remains **exactly identical** to the fast baseline, including all easy lookup cases. No additional BM25 follow-up query calls and no paid model APIs.
- This heuristic was frozen before running the next question-disjoint cohort. Gold labels are only used after retrieval for the audit; they are not used for index, gate or scoring.

## Fresh complete-chain results
| Dataset | n | BM25 @5 | Unmodified V7.1 fast @5 | Guarded V8.3 @5 | V8.3 vs fast |
|---|---:|---:|---:|---:|---:|
| 2Wiki | 240 | 36.67% (88/240) | 74.17% (178/240) | **77.08% (185/240)** | **+2.917 pp** |
| MuSiQue | 160 | 11.25% (18/160) | 16.88% (27/160) | 16.88% (27/160) | 0.000 pp |

Top10 2Wiki: fast **84.58%** (203/240), guarded **85.42%** (205/240), delta +0.833 pp. MuSiQue Top10 unchanged at **25.00%** (40/160).

Paired, 5,000-query-bootstrap:
- 2Wiki @5: **+2.917 pp**, 95% CI **[+0.833,+5.000]**, paired wins/losses **7/0**.
- 2Wiki @10: +0.833 pp, 95% CI [0,+2.083], wins/losses 2/0.
- MuSiQue @5/@10: 0 paired wins and 0 losses. The empirical [0,0] bootstrap does not imply population equivalence.

Four-source breakdown:
- 2Wiki 52 four-source questions: Top5 **26/52** fast vs **33/52** guarded; Top10 **35/52** vs **37/52**.
- MuSiQue 27 four-source questions: both **0/27 @5** and **0/27 @10**. No meaningful four-source paragraph-chain solution.

## Cost and activation
- Activation **22/240 2Wiki (9.17%)**, with 7 recoveries and no observed chain loss. MuSiQue **0/160**, all fast results preserved.
- Mean post-index CPU query times, 2Wiki: BM25 0.463 ms; V7.1 graph addition 0.333 ms; V8.3 guard addition **0.041 ms**; total ~0.837 ms vs ~0.795 ms fast.
- MuSiQue: BM25 0.645 ms; graph addition 0.247 ms; guard 0.030 ms; total ~0.923 ms vs ~0.893 ms.
- Offline 2Wiki additional relation/source-map index ~0.508 s and title question index ~0.003 s (BM25 0.324 s, title graph 0.030 s). MuSiQue additional relation/source-map ~1.068 s and title question index ~0.011 s (BM25 0.548 s, title graph 0.059 s). Source-map includes already-built claim index and is separately timed, so don't naively sum duplicated operations.

## Critical limits
1. Public question-disjoint **validation** data; the entire validation dataset has been repeatedly examined during project iteration. This is not a sealed external or end-to-end Wikipedia evaluation.
2. Documents are pooled with all gold items present by construction. The 2Wiki title-match gate specifically leverages this evaluation structure and may not transfer to open-world retrieval.
3. Exact quote offsets demonstrate source *presence*, not factual entailment. No reader/generator, answer correctness, conflict or abstention evaluation yet.
4. Source-bridge mechanics and exact entity/title matching are established techniques. The measured selection rule is a useful conditional optimization, not proof of theoretical originality or SOTA.
5. Synthetic unit tests show the implementation can store and traverse 8 observed source transitions. There is **no** real 5–8-hop success measurement.
6. The MuSiQue 3-/4-source failure remains unresolved; pursue semantic entity carry-over and fixed-reader extraction diagnostics, following the distinction between retrieval and fact grounding (Mo et al., EMNLP 2026).

## Research recommendation
Keep **V7.1 fast** as default and consider V8.3 conditional source-bridge as an experimental 2Wiki-specific improvement. Do not promote V7.3, V8.0 or V8.1 general rerankers: on previous fresh sample they were slower and failed to beat fast baseline. Next experiment must target MuSiQue unlinked paragraphs using explicit entity carryover, local neural relation extraction and fixed reader, with matched controls and a separate sealed dataset.
