# PGER V9.5 - completed negative/limited graph-set gate experiment (2026-10-28)

**One-time GitHub Action:** https://github.com/vjgits/Research-Papers/actions/runs/40724079742 (success). Full per-question JSONL, summary JSON and dependencies are in artifact `pger-v95-frozen-graph-set-new-ids`. No paid APIs, no changes to main, no reruns.

**IMPORTANT exposure correction:** V9.2 had already evaluated indices 0:400. V9.5's 160:240 is disjoint from V9.3/V9.4 (0:160) but **NOT new relative to all previous research**. Treat as exploratory public benchmark only. See `V95_COHORT_EXPOSURE_CORRECTION.md`.

## Results, 80 questions per dataset, AllEvidence@5 / @10

| Method | MuSiQue AE@5 | MuSiQue AE@10 | 2Wiki AE@5 | 2Wiki AE@10 |
|---|---:|---:|---:|---:|
| Unchanged V7.1 fast | 21.25% | 26.25% | 67.50% | 78.75% |
| Ettin fast-tail 64 +2 | 21.25% | 35.00% | 62.50% | 63.75% |
| Ettin expanded 64 +2 | **26.25%** | **40.00%** | 62.50% | 63.75% |
| V9.5 graph-set gate | 23.75% | 31.25% | **67.50%** | 72.50% |
| Gate with fast-tail control | 21.25% | 28.75% | 67.50% | 72.50% |

**Paired 95% bootstrap:**
- V9.5 gate vs unchanged V7.1, MuSiQue: **+2.50 pp**, CI **[-3.75,+8.75]**, 4 wins / 2 losses.
- V9.5 gate vs unchanged V7.1, 2Wiki: **0.00 pp**, CI **[-5.00,+5.00]**, 2 wins / 2 losses.
- V9.5 gate vs full expanded-64 Ettin, MuSiQue: **-2.50 pp**, CI **[-8.75,+3.75]**, 3 wins / 5 losses.
- V9.5 gate vs full expanded-64 Ettin, 2Wiki: **+5.00 pp**, CI **[+1.25,+10.00]**, 4 wins / 0 losses.
- Ettin expanded vs fast-tail 64+2, MuSiQue: **+5.00 pp**, 4 wins / 0 losses; 2Wiki: **0.00 pp**. The expansion itself shows some benefit on MuSiQue but does not solve the cross-dataset tradeoff.

**By required evidence sources, AE@5 counts:**
- MuSiQue: 44 two-source / 25 three-source / 11 four-source questions. V7.1 17/44, 0/25, 0/11; expanded Ettin 17/44, 4/25, **0/11**; V9.5 gate 19/44, 0/25, **0/11**.
- 2Wiki: 60 two-source / 20 four-source questions. V7.1 50/60 and 4/20; expanded Ettin 49/60 and 1/20; V9.5 gate 51/60 and 3/20.

**Candidate availability:** MuSiQue expanded candidate pool contained all gold in 53/80 questions; 2Wiki in 68/80. The gate selected unchanged fast in 40/80 MuSiQue and 22/80 2Wiki questions.

**CPU:** V7.1 fast mean 1.98 ms MuSiQue and 1.24 ms 2Wiki on this runner. Full expanded Ettin CE inference mean 853.66 ms MuSiQue and 821.15 ms 2Wiki, plus 10.56/6.25 ms expansion respectively. The gate's *projected* CE inference mean is 425.00 ms MuSiQue and 590.93 ms 2Wiki, but the paired experiment physically scored all CE arms, so these are estimates, not measured end-to-end deployment latency.

## Verdict

**V9.5 did not produce a substantial or robust overall improvement.** The gate partly avoids 2Wiki regression but sacrifices the stronger MuSiQue gain, and it still fails all 11 four-source MuSiQue questions. Do not promote it to the default. This was a simple graph-connectivity gate inspired by set-workspace prior art, **not** a full ScalableRAG implementation or novel proof-gap method.

Next scientific step (not executed): perform a failure audit separating (1) missing candidate, (2) candidate found but excluded by top-five ranking, (3) unsupported relation or misleading source. Then freeze a genuinely different evidence-chain verifier or relation-aware ranking algorithm and test only on untouched IDs >=400 or an external corpus. Do not tune on 160:240. No more jobs scheduled.
