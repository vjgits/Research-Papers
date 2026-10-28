# PGER V10.1 — First external 2/3/4 *distinct support-document* benchmark; strong negative hard-case result

**28 Oct 2026. Successful GitHub Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40715038235
**Full per-question data:** https://github.com/vjgits/Research-Papers/actions/runs/40715038235/artifacts/12827643571
**External source:** Tang & Yang, MultiHop-RAG (COLM 2024), ODC-BY released Hugging Face yixuantt/MultiHopRAG, 609 original news articles and 2–4 labeled supporting documents per question.
**Branch:** v101-external-multihoprag-2to4-docs-2026-10-28, isolated, main unchanged.

## Why V10.1 was necessary
V10 MoreHopQA (1,118 human-verified QA examples) had **exactly 2 distinct gold supporting context titles per question**, notwithstanding extra reasoning-step annotations. Calling its high title-chain@5 a 4/8-source retrieval success would be a serious scientific error. V10.1 tests genuine **2, 3 and 4 distinct source article identities**. Number of source articles is STILL not verified count of logical reasoning hops.

## Corpus and evaluation protocol
Official corpus 609 news articles. Gold evidence_list matched by canonical URL with unique-title fallback; unresolved/ambiguous evidence item identities were excluded and **explicitly counted**, not silently evaluated as errors or leakage. Fixed original question offsets 0–399 development and 400–799 additional confirmation. Public dataset not previously used for PGER algorithm development, but not a sealed private test. 316/400 development and 323/400 confirmation questions had unambiguous complete source mapping; **84/400** and **77/400** respectively excluded. These exclusions introduce selection bias; conditional results cannot be described as performance on all dataset questions.

No gold evidence is passed to any online ranker. Compare unchanged BM25, unchanged V7.1 title graph, V9.5-style two additional sparse searches. Same corpus, source IDs, Top5/Top10 evidence definitions. No model APIs, generated answers, true entailment, abstention or independent 5/8-hop evaluation.

## Confirmation on 323 evaluable questions

| Method | All required source documents@5 | @10 | Avg source recall@5 |
|---|---:|---:|---:|
| BM25 | 40.5573% | 63.1579% | 71.6202% |
| V7.1 fast | 39.6285% | 62.8483% | 70.9494% |
| V9.5 two-query lexical fusion | 35.9133% | 59.4427% | 67.8019% |

V9.5 vs V7.1: **-3.715 percentage points**, paired 95% bootstrap CI **[-7.430,-0.310]**, 11 wins / 23 losses. V7.1 versus plain BM25 **-0.929 pp**, CI [-2.167,0], with 0 wins / 3 losses. This is a **generalization failure**; do not promote any algorithm or claim dominance over BM25 on an external news corpus.

### By distinct gold source count (confirmation)

| Distinct required documents | n | BM25 AE@5 | V7.1 AE@5 | V9.5 AE@5 | V7.1 AE@10 |
|---|---:|---:|---:|---:|---:|
| 2 | 164 | 110 | 109 | 98 | 138 |
| 3 | 105 | 20 | 18 | 17 | 50 |
| 4 | 54 | 1 | 1 | 1 | 15 |

The four-source result is **1/54 AE@5**, **15/54 AE@10** for V7.1. A ten-result context helps but is still far below acceptable complete retrieval. This is annotated source-document count, not 4-hop semantic proof or an end-to-end answer score.

## Failure feedback, no unsupported novelty
Previous V9.6B 2Wiki one-hop title-reference graph gave moderate gains; **external news documents do not necessarily encode relevant source links through article-title mentions**. This branch is not a new algorithm, but a necessary external stress test demonstrating that the sparse title-graph and lexical expansion assumptions do not generalize universally. The 77 excluded confirmation questions need a separate *data-schema parity audit* (URL normalization, ambiguous titles, duplicates, unavailable source article) before a full-unbiased claim. Do not tune to this publicly inspected confirmation cohort.

Future algorithm research should move to (1) independently verified relation/answer-edge extraction, (2) robust retrieval across weakly linked/scattered sources, (3) source/answer confidence under unavailable evidence, (4) 4/5/6/8+ human-labeled logical chains, and (5) matched CPU/cost vs exact official baselines. Generic co-mention, dense query similarity and named set operations have abundant published prior art (SAG2, ScalableRAG, S2G-RAG, GroundRAG, SPARE-RAG), with PGER novelty still unproven.

The user's "best ever on simple and 4+ hop" goal remains a **future target**, not an achieved result. Preserve this strong negative outcome alongside V7–V10, do not modify main, schedule checks, call paid APIs, merge or deploy.
