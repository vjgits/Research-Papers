# PGER V16A — 4-pass source frontier and lexical fact-link proxy: NEGATIVE vs simple baseline

**Date:** 2026-10-28. **Verified one-time GitHub Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40733656761
**Full question-level action/provenance archive:** https://github.com/vjgits/Research-Papers/actions/runs/40733656761/artifacts/12834969104
**Branch:** v16-adaptive-evidence-frontier-2026-10-28. Main untouched.
**Primary evaluation:** original EntailmentBank train question indices 400..799 (N=400); NOT previously scored by PGER, but corpus is public/shared and source facts were previously indexed. Published validation (N=187) and test (N=340) are supplemental exploratory repeats.

Source corpus: 11,472 unique canonical WorldTree facts (EntailmentBank task1 CC-BY-4.0). Search query uses question and source fact text only; no gold proof, answer or hypothesis. All zero/1/2/4 rounds, two BM25 calls per round where available, <=120 active candidate fact texts. Exact text/hash source witness logs and PGER V13C default-no-trust proof gate (ABSTAIN) preserved.

## Locked primary results

| Arm | Extra BM25 calls | Full exact gold in Top120 pool | Four+ required fact full pools | Complete gold fact set @20 | Mean CPU process ms |
|--|--:|--:|--:|--:|--:|
| Initial zero | 0 | 55/400 = 13.75% | 6 | 5.75% | 0.884 |
| Static first-pass source proposals H1 | 2 | **67/400 = 16.75%** | **10** | 6.50% | **1.846** |
| Static proposals H4 | 7.925 avg | 59/400 = 14.75% | 10 | 8.25% | 5.065 |
| Adaptive evidence frontier H1 | 2 | 63/400 = 15.75% | 10 | 6.75% | 3.047 |
| Adaptive evidence frontier H4 | 7.997 | 61/400 = 15.25% | 9 | 7.25% | 8.732 |
| Adaptive lexical fact graph H1 | 2 | 64/400 = 16.00% | 10 | 7.50% | 2.982 |
| Adaptive lexical fact graph H4 | 7.997 | 56/400 = 14.00% | 9 | 4.75% | 9.199 |

Static H1 vs initial: +3.0 pp full gold candidate sets, paired 95% interval [+1.0,+5.25], 15 wins/3 losses. But **adaptive H1 vs static H1 -1.0pp** interval [-2.5,+0.25]; **adaptive H4 vs static H4 +0.5pp** interval [-2.0,+3.0], neither substantial. H4 graph underperforms on complete candidate sets and final retrieval; do NOT promote.

## Why adding passes made source retrieval worse

Strict fixed Top120 source working set *re-ranked and replaced documents after each pass.* On the previously unscored 400 questions:
- Static H1 full pool 67 cases, static H4 full pool 59: **17 lost previously complete sets** / 9 new complete sets.
- Adaptive H1 63, adaptive H4 61: 4 lost / 2 gained.
- Graph H1 64, graph H4 56: 10 lost / 2 gained.

These are real negative side effects from candidate-set budget eviction, not evidence that no additional facts can be found. Source term labels and source-neighbor links are **lexical hints, not typed or verified relationships**. They can drift into related but irrelevant documents. More queries also add CPU, with no significant all-chain discovery increase.

## Mandatory comparison with original three systems

SAG2: source passages to extracted terms and additional search, but crucially **contextual necessary-evidence JEV and protected retained source memory**. V16A approximated evidence frontier but had NO JEV necessity judge and was willing to evict earlier candidate coverage from the active pool. Source https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py.

HippoRAG2: prebuilt **fact/entity graph** with OpenIE links and PPR, not a token->fact lexical co-occurrence graph. V16A's token posting adjacency has no independently validated typed relation and can amplify hub/distractor facts. Source https://github.com/OSU-NLP-Group/HippoRAG/blob/main/src/hipporag/HippoRAG.py.

S2G-RAG: trained sufficiency judge, **structured missing propositions**, compact sentence-level evidence memory and stop decision. V16A's 'missing relation' placeholder is unverified and NOT a genuine learned sufficiency judge; query pass controller had no grounded early-stop policy. Source https://github.com/nianaaa/S2G-RAG/blob/main/inference/inference_bm25.py.

## V16B corrective hypothesis, precommitted before new cohort

**Separate durable candidate archive from context-limited Top120 active ranking.** Include every retrieved source with original source hash and query action, preserving candidate coverage over multiple passes even when Top120 changes. This fixes **evidence memory loss in archival recall**, NOT automatically final Top5 and not verified entailment. Retain V13C default-deny. Freeze a **one-round (two-query) low-cost default** based on the V16A first-pass quality/cost frontier, and test WITHOUT retuning on the next untouched original training question offsets [800,1313). Also report 4-pass archive oracle ceiling and source memory bytes; do NOT count archived-but-inactive sources as Top120 success.

Promotion requires explicit improvement on new cohort (complete candidate set within active budget and comparable TopK) and measured CPU/candidate-memory trade-off; if no gain, retain cheaper simple search. V16B should retain negative results, not claim that archive alone solves long proof chains or beats official systems.

No paid APIs, schedule, main modification, merge, proof verifier approval or untested SOTA claims.
