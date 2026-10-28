# PGER V9.2 — Full-corpus lexical evidence expansion: negative confirmation
**Date:** October 28, 2026 (UTC).  
**Exact successful Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40653608720  
**Complete 1,200 question-level archive:** https://github.com/vjgits/Research-Papers/actions/runs/40653608720/artifacts/12800364244  
**Isolated branch:** `v92-fullcorpus-evidence-expansion-2026-10-28`; main unchanged.

## What was tested
Predeclared eight arms, no paid models: unchanged V7.1 BM25+indexed one-hop graph versus rank-fusion or interleaving of source-grounded term-expansion BM25 searches. Exact full original SAG2/HippoRAG2 corpora 6119/11656/9811 passages; author-reported SAG2 external JEV scores not independently executed. Questions first 120 development, next 280 confirmation for each of 2Wiki, MuSiQue and HotpotQA. Source quotes only prove textual occurrence, not relation correctness. Up to eight expansion searches *per selector family*; additional CPU is reported in artifacts and not budget-equivalent to zero-call V7.1.

## Results: All Evidence in Top 5 (AE@5, complete chain)
| Method | 2Wiki dev n=120 | MuSiQue dev n=120 | Hotpot dev n=120 | 2Wiki confirm n=280 | MuSiQue confirm n=280 | Hotpot confirm n=280 |
|---|---:|---:|---:|---:|---:|---:|
| V7.1 fast | **73.33%** | 9.17% | **68.33%** | **70.36%** | 17.86% | **71.43%** |
| Interleave named phrases | 59.17% | **16.67%** | 56.67% | 53.93% | 16.79% | 52.50% |
| Fusion mixed rare terms 0.4 | 66.67% | 10.83% | 66.67% | 68.93% | **20.71%** | 69.64% |
| Fusion mixed rare terms 0.8 | 68.33% | 10.83% | 66.67% | 68.57% | **20.71%** | 69.64% |

Key paired outcomes (exploratory, 2000 question bootstraps, not family-wise corrected):
- **MuSiQue interleave vs V7.1**: development +7.50 percentage points, 95% CI [+1.67,+14.17], 12 wins/3 losses; **confirmation -1.07 pp**, 95% CI [-5.36,+3.57], 17 wins/20 losses. **This is a failed validation.**
- **MuSiQue fusion mixed .4 vs V7.1**, confirmation +2.86 pp, 95% CI [-.36,+6.07], 15 wins/7 losses; weak and not robust at this sample size. Dev +1.67 pp (CI [-.83,+5.00]).
- **2Wiki mixed .4** confirmation -1.43 pp, CI [-4.29,+1.07]; Hotpot -1.79 pp, CI [-5.00,+1.43].
- Interleaving harms 2Wiki and Hotpot sharply. Protecting just two top documents does not protect the remaining source chain.

## Decision and next hypothesis
This cheap lexical expansion **does not robustly improve the accuracy–cost frontier** and is established prior art. Do not replace V7.1, call this a novel algorithm, or claim that it reaches SAG2.
The next bounded experiment should test **semantic necessary-evidence passage scoring** using a free local pretrained cross-encoder, with identical candidate/score budgets, preserving the unchanged V7.1 baseline and separately evaluating source expansion. Prior results of V8.3–V8.6 already show generic cross-encoder can improve MuSiQue but is expensive, and still recovers almost no 4-support chains. No guarantee this approach will beat SAG2. Any gain must survive confirmation and include CPU cost.

## Execution integrity
The first run https://github.com/vjgits/Research-Papers/actions/runs/40653495630 failed before metrics due to a benign incorrect `SparseMethods.index` accessor; code integration was fixed with *no changes* to questions/ranking and successful run 40653608720. Four unit tests + smoke passed; per-query witness traces and full corpus checksums archived. Benchmarks are publicly and repeatedly used, not sealed. No final-answer reader or 5–8 hop claims.
