# PGER V9.1 — Equal-Budget Lexical Proof-Gap Search: Completed Negative Result
**Completed:** 2026-10-28 UTC  
**Isolated branch:** `v91-budgeted-proofgap-realqa-2026-10-28`  
**Successful one-time GitHub Action:** https://github.com/vjgits/Research-Papers/actions/runs/40652190517  
**Per-question data:** https://github.com/vjgits/Research-Papers/actions/runs/40652190517/artifacts/12800391390  
**Frozen pre-run protocol:** [V91_FROZEN_PROTOCOL.md](V91_FROZEN_PROTOCOL.md).

## Scientific verdict

**Rejected as a new retrieval policy.** Our *lexical approximation* of a missing relationship, using exactly two additional BM25 queries, did not outperform V7.1 fast, repeat-query control, or cheap frontier-based search on two new question-ID-disjoint public validation cohorts. It reduced complete-source-chain@5 accuracy and increased per-query CPU substantially. This does not disprove a future truly sourced, counterfactual, decision-sensitive proof-gap algorithm; that was **not implemented or tested** here.

## Frozen data

- 2Wiki deterministic eligible validation positions **1801–1920**, n=120, corpus pooled from 936 source pages supplied with questions.
- MuSiQue positions **1281–1440**, n=160, 2,816 source paragraphs.
- Source gold annotations never accessed until after ranking. Corpus contains all gold documents by construction. These are **public development families** with many earlier PGER tests, not sealed independent data.
- All 3 extra-search arms issue exactly **two** BM25 queries with cap 60, same RRF projection and first two V7.1 anchors protected. Matching calls is *not* matching CPU; both recorded.
- `gap2` has no verified semantic relationship extractor, no independently evaluated value-of-information, and no actual answer correctness or calibrated abstention.
- Original V7.1 BM25+indexed title graph remains unchanged.

## Complete source-chain recovery

| Method | 2Wiki @5 / @10 | MuSiQue @5 / @10 |
|---|---|---|
| **V7.1 fast** | **75.00% / 77.50%** | **21.25% / 30.63%** |
| Original-question repeat ×2 | 60.00% / 65.00% | 17.50% / 21.88% |
| Cheap frontier two searches | 59.17% / 65.83% | 15.00% / 21.25% |
| Lexical missing-relationship two searches | **50.83% / 58.33%** | **16.88% / 20.00%** |

Paired gap2 versus **fast** @5: 2Wiki **−24.17 pp**, 95% question bootstrap [−31.67,−16.67], 0 wins/29 losses; MuSiQue **−4.38 pp**, CI [−9.38,+0.63], 5 wins/12 losses. Paired gap2 versus **cheap frontier** @5: 2Wiki **−8.33 pp**, CI [−13.33,−4.17], 0 wins/10 losses; MuSiQue **+1.88 pp**, CI [−1.88,+5.63], 6 wins/3 losses (no robust advantage).

## Hard questions

| Dataset | Annotated support count | n | Fast complete @5 | Gap2 complete @5 |
|---|---:|---:|---:|---:|
| 2Wiki | 4 | 20 | 7 | **0** |
| MuSiQue | 3 | 42 | 2 | 1 |
| MuSiQue | 4 | 24 | **0** | **0** |

The cheap gap proxy did not repair four-source retrieval. A major reason is displacement: source changes from extra searches can push previously correct documents out of final Top 5. More calls do not imply better evidence chains.

## Shared-run CPU (post-index query only)

| Dataset | Fast mean | Gap2 mean |
|---|---:|---:|
| 2Wiki | **0.349 ms** | **1.068 ms** |
| MuSiQue | **0.661 ms** | **1.912 ms** |

Different runner/caches/data sample from the official SAG2 full-corpus benchmark. No production latency comparison. Note that V9.1 uses only small *pooled benchmark corpora*, unlike SAG2 1,000 question full-corpus test.

## Plain-language interpretation

A person who **guesses** what fact is missing, and looks for it twice, can make things worse by throwing out already useful evidence. A researcher who knows precisely which *source-supported relation* remains unresolved may do better, but our V9.1 code did **not know that**; it used lexical token overlaps.

## Research decision

Keep V7.1 fast as baseline and source-preserving fallback. V9.1 gap2 is **not a valid novel improvement** and must not be adopted. A future experiment should first test human-annotated missing *decision-changing* claims and evaluate correct selection separately from retrieval. Only promote extra searches if they improve question-level outcomes at equal total cost and protect correct evidence.

No paid API, no reviewers, no schedules, no `main` changes.
