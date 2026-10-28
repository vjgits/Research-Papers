# V17 — new HoVer self-run, actual SAG2 indexing and PGER results

Date: 2026-10-28. Branch: `v17-hover-official-sag2-reproduction-2026-10-28`. Main untouched, no scheduled tasks or paid model API.

## Dataset and frozen pool

Original HoVer 2020 multi-hop fact verification, official dev release of **4,000 claims**: 1,126 annotated 2-hop, 1,835 annotated 3-hop, and 1,039 annotated 4-hop claims. We hash-selected 40 claims from each group (120 total) before scoring. Same corpus and question IDs for both methods.

Source corpus is **16,579 distinct original 2017 Wikipedia articles** extracted from original 2.156 GB `wiki_wo_links.db` (original schema table `documents (id PRIMARY KEY, text)`), each truncated to exactly at most 5,000 characters *before both search indexes*. **Transductive pooled corpus:** titles selected from original HoVer DRQA (top 100 per evaluated claim) and 25 per 240 extra background claims; does NOT index entire Wikipedia and is not official HoVer retrieval leaderboard. Gold supporting_facts **not used to select corpus documents**, but annotated questions' unlabeled first-stage retrieval data do affect the pool, making it intentionally easier than full open-Wikipedia. Zero source text/title modifications based on gold.

Actual exact source-title availability:
- 2-hop **30/40** claims complete in corpus.
- 3-hop **22/40**.
- 4-hop **10/40**.
All 58 claims lacking at least one necessary source are included as complete-evidence FAILURES. Score both full denominator and conditioned available subset if later analyzed, never silently drop.
Full source SHA, frozen source-title hash, selected claim IDs, all original source file hashes in `v17-hover-data/prepared/manifest.json` and GitHub Actions archived artifact.

Preparation successful https://github.com/vjgits/Research-Papers/actions/runs/40741978291 ; dataset/probe successful https://github.com/vjgits/Research-Papers/actions/runs/40741541714 ; upstream original HoVer code https://github.com/hover-nlp/hover .

## Completed V17B: same-input execution of original SAG2 SQLite BM25 retrieval stage

**Run succeeded:** https://github.com/vjgits/Research-Papers/actions/runs/40742249212 .
**Actual upstream SAG2 git SHA** `bb7f82751ba1576219f9d9ebd021128603d130c3` sourced from `Zleap-AI/SAG-Benchmark`. We imported the author's original `CorpusIndex`, matching original FTS5 BM25 and compiled scoring extension, and called its original `match_query` + `retrieve` for 100 BM25 candidates. This is the **official SAG2 *first-stage BM25***, NOT SAG2's author end-to-end with contextual JEV scoring and 0/1/2 expansion rounds.

PGER compared V16 H0 cheap, H1 2 searches, H4 ~8 searches and V16C source-archive activation zero-shot (17 features ranker trained only on EntailmentBank science training questions and never on HoVer gold labels). Both index same source texts. Test labels are read only after every method finishes ranking.

Exact complete **supporting article titles**@5 (fraction of all claims, including unavailable):
| Annotated hop count | n | Original SAG2 BM25 | PGER V16 H0 | PGER H1 | PGER H4 | PGER V16C archive |
|---|---:|---:|---:|---:|---:|---:|
| 2-hop | 40 | 24/40 (60.0%) | 25/40 (62.5%) | 20/40 (50.0%) | 18/40 (45.0%) | 25/40 (62.5%) |
| 3-hop | 40 | 7/40 (17.5%) | 12/40 (30.0%) | 9/40 (22.5%) | 6/40 (15.0%) | 9/40 (22.5%) |
| 4-hop | 40 | 0/40 (0.0%) | 1/40 (2.5%) | 1/40 (2.5%) | 1/40 (2.5%) | 0/40 (0.0%) |
| **all** | **120** | **31/120 (25.83%)** | **38/120 (31.67%)** | **30/120 (25.00%)** | **25/120 (20.83%)** | **34/120 (28.33%)** |

Pairwise PGER H0 vs author SAG2 BM25 stage: +5.833pp, paired 95% bootstrap CI [0,12.50], 11 question wins / 4 losses. Borderline, small, transductive, retrieval-only. Does NOT beat full SAG2 or prove truth seeking.

Complete source@10: SAG2 stage 30.83%, PGER H0 40.00%, H1 38.33%, H4 35.83%, V16C 41.67%.
Complete source@20: SAG2 stage 37.50%, PGER H0 45.83%, H1 43.33%, H4 39.17%, V16C 45.00%.

Cause: sources missing from corpus explain many impossible cases, but the retained-source selection also loses full chains with further searches. V16C zero-shot did NOT outperform V16 H0 at @5. Do not promote multi-round expansion.

CPU process stages across shared GitHub runner: actual upstream SAG2 initial BM25 search mean ~13.638ms, p95 29.066ms; PGER full four-round retrieval *plus expanded hits* mean ~23.919ms, p95 25.001ms, plus learned model prediction mean 1.575ms, p95 1.822ms; different amounts of search and index preparation make comparison unsuitable for claiming efficiency per correct answer. SAG2 SQLite first index CPU 30.19sec; PGER sparse BM25 ~3.93sec and fact-link index 0.79sec. Source documents 16,579. PGER scorer may also add feature cost that is not included in this stage's reported model-predict-only metric.

## Ongoing V17C: actual SAG2 author local model full retrieval pipeline

The official upstream `search_sag2` and `LocalScorer` can run with `Qwen/Qwen3-Reranker-0.6B`, an author-supported **local** model. A one-time SIX-question pilot (2 claims each 2/3/4-hop), `candidate_k=16`, `seed_k=4`, `max_hops=1`, local CPU Qwen scorer, pinned open weights and SAG2 original SHA, was launched via workflow https://github.com/vjgits/Research-Papers/actions/runs/40742729225 .

**At time this ledger was written: local scorer results NOT YET VERIFIED, do not claim an outcome.** Six examples are useful for code/model feasibility and compute accounting only, not meaningful statistical superiority. Local SAG2 Qwen is NOT the paid/provider JEV scorer and cannot be mislabeled as original published SAG2. All six use same source texts/IDs as prior PGER V17B.

## Next honest evaluation prerequisite

To compare full official SAG2 JEV vs PGER (and PGER proof layer), run the original author scorer with authorized provider credentials and a complete precommitted budget, or independently reproduce a comparable calibrated judge with a clearly named different local variant. Previous user preference is NO unauthorized paid APIs.

A meaningful source-disjoint HoVer result needs much larger article coverage (ideally full original published Wikipedia index), out-of-domain held-out claims and gold fact/sentence verification, not only titles in a transductive DRQA candidate pool. After actual JEV/local result, compare complete@K by genuine hop count, retrieval and source availability, answer accuracy, false-support rate, justified abstention, cumulative offline+online GPU/CPU p95 wall and cost. No claim that PGER wins industry-wide until then.

GitHub all prior V7-V16 decisions preserved; this branch is isolated; no changes to main, no automated tasks, no invented outputs.
