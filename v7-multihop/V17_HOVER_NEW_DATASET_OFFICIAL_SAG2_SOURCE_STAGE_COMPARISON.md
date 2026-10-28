# PGER V17 — NEW HoVer dataset, same-corpus self-run vs official SAG2 code

**Date**: 2026-10-28.
**Branch**: v17-hover-official-sag2-reproduction-2026-10-28. **Main unchanged**.
**Claim-level source retrieval completed**: https://github.com/vjgits/Research-Papers/actions/runs/40742249212
**Original author code pinned**: Zleap-AI/SAG-Benchmark @ bb7f82751ba1576219f9d9ebd021128603d130c3.
**Full same-corpus per-question artifact**: https://github.com/vjgits/Research-Papers/actions/runs/40742249212/artifacts/12839163492

## What we physically executed

- A real new fact-verification benchmark: original HoVer EMNLP 2020 dev (4,000 claims, 2-hop 1,126; 3-hop 1,835; 4-hop 1,039). Hash-select exactly 40 each of 2-, 3- and 4-hop, total 120, without using those gold titles to retrieve or construct source lists.
- Original 2017 Wikipedia original source SQLite 2,156,273,664 bytes and HoVer publisher's DRQA candidate title lists. Construct transductive fixed pool of 16,579 source articles, each truncated equally at first 5,000 Python chars, from all selected claims' *unlabeled* top100 DRQA title list and unrelated dev questions' top25. **This is NOT full Wikipedia / official HoVer benchmark**, nor source-disjoint, though neither method sees query gold labels. Corpus published by source, not generated.
- Source availability strict offline: only 30/40 2-hop, 22/40 3-hop, **10/40 4-hop** have all annotated gold article titles in shared corpus. All missing gold sources count as failure.
- **Actual official SAG2 original SQLite FTS5/BM25 index and retrieval code**, without its contextual JEV paid inference and without its evidence-led 2-round engine. Label exactly **SAG2 original BM25 stage**, not SAG2 algorithm.
- PGER source pipeline H0, H1 (2 extra BM25), H4 (~8 extra BM25), V16C archive selector trained solely on 400 *EntailmentBank* science development questions (no HoVer labels, zero-shot transfer). PGER has no claim verdict or human-validated source entailment.

## Strict overall complete annotated article-title set within top K, all 120

| Actual executed arm | complete@5 | complete@10 | complete@20 |
|--|--:|--:|--:|
| Original SAG2 **BM25 stage only** | 31/120 = 25.833% | 37/120 = 30.833% | 45/120 = 37.500% |
| PGER V16 initial no additional searches | **38/120 = 31.667%** | 48/120 = 40.000% | **55/120 = 45.833%** |
| PGER V16 first expansion (two extra searches) | 30/120 = 25.000% | 46/120 = 38.333% | 52/120 = 43.333% |
| PGER V16 four expansion rounds (~8 extras) | 25/120 = 20.833% | 43/120 = 35.833% | 47/120 = 39.167% |
| PGER V16C independent-domain trained archive reactivation | 34/120 = 28.333% | **50/120 = 41.667%** | 54/120 = 45.000% |

PGER V16 initial minus SAG2 upstream BM25 stage complete@5 +5.833 pp, paired bootstrap 95% CI [0,12.5], wins 11/losses 4, **not compelling statistical dominance**. V16C at5 +2.5 pp CI [-3.333,+7.5] vs official initial BM25, not significant. These are NOT comparable to published SAG2 H2/JEV results.

### Detailed 2/3/4 hop at Top5, 40 each (all source-absent included)

| Method | 2-hop | 3-hop | 4-hop |
|--|--:|--:|--:|
| Upstream official SAG2 BM25 | 24/40 (60.0%) | 7/40 (17.5%) | 0/40 |
| PGER initial | 25/40 (62.5%) | 12/40 (30.0%) | 1/40 (2.5%) |
| PGER H1 | 20/40 (50.0%) | 9/40 (22.5%) | 1/40 (2.5%) |
| PGER H4 | 18/40 (45.0%) | 6/40 (15.0%) | 1/40 (2.5%) |
| PGER learned archive | 25/40 (62.5%) | 9/40 (22.5%) | 0/40 |

Four-hop evidence retrieval **still almost absent**, and pooled corpus availability caps ANY method at 10/40=25% 4-hop complete retrieval. Repeated lexical expansion actively **worsens early strong evidence** and fails to consistently find missing bridge facts.

## Costs — measured under same hosted GitHub runner, but scopes unequal

- Original SAG2 upstream BM25 SQLite FTS5 index build **30.189 process CPU seconds**; single-retrieval **13.638 ms/query mean**, p95 **29.066 ms** (SAG2 specific tokenizer/index).
- PGER BM25 source index build **3.929 seconds** as wall measure, plus token fact-link build **787 CPU ms**. PGER 4-round full source retrieval **23.919 process CPU ms mean**, p95 **25.001 ms**, followed by V16C prediction **1.575 ms**. Timing of stages not matched for same workload; no proof/answer inference or cloud JEV included. Do not claim overall cheaper/costlier *per correct answer*.

## Caveat and next direct system trial

SAG2 paper JEV contextual necessary-source model used external paid scoring provider, no user-provided key or authorization in this run, so **full JEV-based SAG2 is NOT yet independently executed on HoVer**. The same upstream repository provides a separate full iterative SAG2 architecture with an Apache-licensed LOCAL Qwen reranker, which we are attempting to execute separately on small fixed HoVer claims with offline weights and no paid API. That variant does NOT reproduce published JEV performance; six cases is a technical feasibility smoke and not an accuracy comparison.

Important: The HoVer *official* score additionally requires at least one correct supporting sentence per gold document plus **correct SUPPORTED/NOT_SUPPORTED verdict**. We score annotated article-title recall only, NOT sentence-level support, factual truth, calibrated abstention, answer accuracy or HoVer Score. HoVer development annotations are public and task is transductive selection from original first-stage retrieved docs, not true open-world discovery.

## Decision

V17 shows PGER initial lexical/title retrieval is promising against another method's initial BM25 stage but **PGER's additional turns and generic archive reranking do not establish superior reasoning**. Preserve H0 fallback, do not promote multi-round lexical expansion as universal. Full JEV SAG2/JEV model access, source-complete evaluation, relation/answer proof labels and matched cost accounting are needed for the user's exact research objective. Never claim we beat SAG2's full system based on this ablation alone.

All runs one-time, no charged API, no main changes, no scheduled task or model proof-verifier promotion.
