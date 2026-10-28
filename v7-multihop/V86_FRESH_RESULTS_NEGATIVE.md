# PGER V8.6 — Frozen Typed-Relation & NLI Verification: Complete Negative Retrieval Result

**Date:** 2026-10-27 Pacific / 2026-10-28 UTC
**Branch:** `v86-typed-entailment-2026-10-27` (forked from V8.5; `main` untouched)
**Successful GitHub Action:** https://github.com/vjgits/Research-Papers/actions/runs/40638305465
**Full per-question and contrastive output:** https://github.com/vjgits/Research-Papers/actions/runs/40638305465/artifacts/12794693631
**Frozen methods and thresholds:** [V86_FROZEN_PROTOCOL.md](V86_FROZEN_PROTOCOL.md)

## Overall decision — negative for retrieval

The source clause scoping + pretrained NLI verifier performs perfectly on **272 deliberately templated author-constructed positive/negative contrastive examples**, but **improves zero complete evidence chains at Top 5** compared with V8.5's unfiltered sourced CE96 on both new public-validation cohorts. The clause rule can reject the previously identified *Kalank* director/producer misattribution, but it cannot *recover the correct predicate* or create missing supporting relationships. The NLI gate accepts every candidate edge that passes the clause check in natural retrieved material. Its extra CPU cost is unjustified. **Do not replace the V7.1 fast or V8.5 sourced CE methods with V8.6.**

This is a controlled *retrieval and text-claim scoring* study, not final-answer accuracy, true factual entailment, robust 4+/8-hop reasoning, or SOTA.

## Controlled author-constructed contrastive fixture (not independent validation)

272 cases: 270 repeated syntactic template variants covering directed_by, produced_by, written_by, born_in and located_in (6 entity sets × 9 patterns per relation), plus 2 cases based on the observed V8.5 *Kalank* error. Exact generated fixture frozen by script, sha recorded in summary artifact.

| Method | Entailment precision | Entailment recall | Entailment F1 |
|---|---:|---:|---:|
| Clause scoping only | 62.76% | 100.00% | 77.12% |
| Off-the-shelf NLI only | 84.26% | 100.00% | 91.46% |
| **Clause + NLI** | **100.00%** | **100.00%** | **100.00%** |

Raw NLI 3-class accuracy: **198/272 = 72.79%**. Contradiction 90/90 identified, entailment 91/91 identified, but only **17/91 neutral** cases correctly neutral. The others were misclassified as contradiction (57) or entailment (17). Distinguishing lack of support from outright falsehood remains an important unresolved task. Perfect combined binary classification on these templated examples is **NOT evidence of real-world 100% precision/recall, independent human adjudication or generalizable semantics**.

## Fresh question-ID-disjoint (but repeatedly analyzed public validation families)

- 2Wiki eligible sorted positions **1,681–1,800**: n=120, pooled 924 pages.
- MuSiQue positions **1,121–1,280**: n=160, pooled 2,604 paragraphs.
- Gold docs present in pooled corpora by construction; not a full Wikipedia/open-Web benchmark.
- Same CE96 candidate shortlist, same pretrained relevance CrossEncoder scores, first two V7.1 anchors protected, same .08 link bonus for V8.5 source-cue, V8.6 clause-only and V8.6 clause+NLI. No gold labels were accessed until after ranking.

| Method | 2Wiki Top5 | 2Wiki Top10 | MuSiQue Top5 | MuSiQue Top10 |
|---|---:|---:|---:|---:|
| BM25 | 33.33% | 47.50% | 8.75% | 15.63% |
| **V7.1 fast BM25+indexed graph** | **76.67%** | **85.00%** | 17.50% | 21.88% |
| Protected CE96 | 58.33% | 65.83% | 25.63% | 32.50% |
| **V8.5 sourced CE96** | **62.50%** | **75.00%** | **26.25%** | **33.75%** |
| V8.6 typed scope | 62.50% | 74.17% | 26.25% | 33.75% |
| **V8.6 typed + NLI** | **62.50%** | **74.17%** | **26.25%** | **33.75%** |

Paired complete-chain@5 differences against V8.5 sourced = **0.00 pp, 0 wins / 0 losses**, empirical bootstrap [0,0] on **each** cohort. This is an observed exact tie, not proof of identical future behavior. The stricter V8.6 gate additionally **lost one 2Wiki complete chain at Top 10** while gaining none.

### Why the ledger did not alter retrieval

| Measure | 2Wiki | MuSiQue |
|---|---:|---:|
| Proposed directional source-edge candidates across queries | 82 | 32 |
| Passed local typed clause scope | 81 | 26 |
| Passed additional NLI gate | 81 | 26 |
| Queries with >=1 proposed edge | 43/120 | 18/160 |
| Queries whose Top-10 ranking changed vs V8.5 sourced | 4/120 | 0/160 |

The legacy title-mention extractor simply does not propose enough *correctly typed* evidence relations. A verifying filter cannot make up missing candidate claim edges, and NLI never rejected a typed-accepted claim in this natural-corpus slice. On one 2Wiki question, dropping a weak member_of edge removed a complete chain from Top 10; strict filtering can itself cause displacement.

### Hard-source failure

- 2Wiki 4 supporting pages (n=24): V7.1 fast 14/24 Top5, V8.5 sourced 4/24, V8.6 4/24.
- MuSiQue 3 supporting paragraphs (n=57): V7.1 fast 2/57 Top5, V8.5 sourced 11/57, V8.6 11/57.
- MuSiQue 4 supporting paragraphs (n=29): **0/29 complete Top5** for all compared methods. Full gold source sets were within wide192 for **18/29** and within CE96 for **9/29**. More search passes alone are insufficient, while a model cannot rank documents not in its shortlist.

## CPU costs and reproducibility

Mean shared-process GitHub CPU path stage timing (ms/query, excluding model initialization/offline indexing): 2Wiki BM25 **0.596**, graph **0.166**, candidate query+embedding **12.974**, CE96 **1,726.117**, NLI extra **22.884**; MuSiQue BM25 **0.777**, graph **0.214**, candidates **15.577**, CE96 **2,127.855**, NLI extra **5.130**. NLI includes zero-candidate queries; mean is **not conditional per-verification latency**. These are not production service times.

NLI model `cross-encoder/nli-MiniLM2-L6-H768` pinned revision `9aa22b250d25a10ac39ab4a6b2bc28213507cb0c`, label order contradiction/entailment/neutral, threshold 0.70 and margin 0.10. CE/dense model revisions and pip dependency lock not pinned; future independent runs must pin them.

The original action https://github.com/vjgits/Research-Papers/actions/runs/40638092348 failed due to a **harness-only bug**: typed-only baseline incorrectly asserted NLI logits existed. After a one-line conditional guard and added regression test (9/9 pass), the latest run succeeded on **the same fixed cohorts, models, thresholds and ranking rules**. A redundant in-flight attempt was canceled. All exceptions are documented.

## Next falsifiable step (not run)

Build and **independently annotate** sentence-level subject-predicate-object spans and true entailment/neutral/contradiction outcomes in naturally occurring sources. Extract *new correctly attributed relations*, not only filter legacy title edges. Apply relation-grounded proof-gap retrieval with the same candidate/CE/NLI budget and a genuine fixed answer reader. Report retrieval, interpretation accuracy, answer correctness and abstention separately; test a sealed non-pooled corpus. **Reject novelty/performance claims until matched-budget 4-source gains are demonstrated.**

No paid API, review agents, recurring GitHub workflow, production deployment or changes to `main`.
