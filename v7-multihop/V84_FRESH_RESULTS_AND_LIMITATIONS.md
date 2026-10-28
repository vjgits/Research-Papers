# PGER V8.4 — Fresh High-Recall Funnel: Mixed Results and Unsolved Four-Source Chains

**Date:** October 27, 2026 Pacific / October 28, 2026 UTC  
**Branch:** `v84-recall-funnel-2026-10-27` (no changes to `main`)  
**Successful one-time run:** https://github.com/vjgits/Research-Papers/actions/runs/40622098666  
**Full per-query results:** https://github.com/vjgits/Research-Papers/actions/runs/40622098666/artifacts/12788077397

## Verdict

Widening candidate retrieval improves *candidate oracle coverage* substantially, and a pretrained 64-passage cross-encoder improves MuSiQue complete-chain@5 over the fast V7.1 graph, **but no four-source MuSiQue chain was recovered at Top 5** and CPU inference is expensive. An explicit title-edge-density gate restores fast 2Wiki performance but routes all MoreHopQA context queries to the weaker fast path, showing this is not a generally effective per-question policy. This work is *retrieval only*, NOT proof of generated answer correctness, reliable 5+/8-hop reasoning, or algorithmic originality.

## Protocol and exact task boundaries

- Original BM25+V7.1 Aho–Corasick one-hop graph is unchanged.
- Pretrained MiniLM dense retrieval, BM25, TF-IDF, 2 bounded BM25 followups, title/reverse graph; offline candidate union cap 192; predetermined RRF reduces to a 64-document CE shortlist; protect 2 original fast anchors.
- Cross-encoder `cross-encoder/ms-marco-MiniLM-L6-v2`, CPU two PyTorch threads, sigmoid, 192-token maximum; dense model `sentence-transformers/all-MiniLM-L6-v2`. No fine-tuning, paid API, reviewer agent, or schedule.
- Question-disjoint public validation: 2Wiki eligible positions **1441–1560** (120 questions, 889 pooled pages); MuSiQue **801–960** (160, 2,708 pooled paragraphs). Gold sources are guaranteed to be in pooled universe. It is not Wikipedia-scale or sealed independent final testing.
- MoreHopQA uses 80 deterministic human-verified test examples, 140 pooled context passages, **only the underlying previous-question supplied context-source titles**, not missing appended reasoning steps or actual MoreHopQA answer correctness. Published MoreHopQA draws from HotpotQA, 2Wiki and MuSiQue and thus is not fully independent source material. All sampled MoreHop context chains have 2 annotated supports in this diagnostic.
- No actual answer generation, entailment verification, contradiction checking, calibrated abstention, official IRCoT/HippoRAG2 run, full-query deployment latency measurement, or reliable >4-hop evaluation.

## Complete chain recovery (all required source documents)

| Method | 2Wiki Top5 / Top10 | MuSiQue Top5 / Top10 | MoreHop *context* Top5 / Top10 |
|---|---|---|---|
| BM25 | 40.83% / 55.00% | 9.38% / 16.25% | 31.25% / 32.50% |
| **V7.1 fast graph** | **83.33% / 85.83%** | 15.63% / 25.00% | 31.25% / 32.50% |
| V8.3 protected CE32 on V8.4 cohort | 64.17% / 72.50% | 22.50% / 35.63% | 32.50% / 32.50% |
| V8.4 CE64, protected | 64.17% / 72.50% | 25.00% / 39.38% | 37.50% / 52.50% |
| V8.4 CE64 + weak sourced cue | 71.67% / 85.00% | **25.00% / 40.00%** | 37.50% / 52.50% |
| **V8.4 actual route** | **83.33% / 85.83%** | **25.00% / 40.00%** | **31.25% / 32.50%** |

Pairwise **V8.4 routed vs V7.1 fast** on MuSiQue Top 5: +9.375 percentage points, paired bootstrap 95% interval [+2.5,+15.625], 22 wins/7 losses. Comparing same CE family V8.4 sourced64 vs V8.3 protected32 on MuSiQue: +2.5 pp at Top 5, 95% paired interval [-0.625,+5.625], wins/losses 5/1 — **incremental rerank gain is not statistically robust at this sample size**. MoreHop ungated CE64's +6.25 pp vs fast, [+1.25,+11.25] is about previous-context retrieval only; the actual gate throws that gain away.

The 2Wiki ungated CE sourced64 **regressed 11.67 pp** compared with V7.1 fast, paired 95% interval [-18.33,-5.83], 2 wins/16 losses. Gate uses low *corpus title graph edge density* (not a decision-changing evidence sufficiency test), so 2Wiki is sent to fast: matching baseline rather than genuinely improving it.

## Candidate oracle coverage (requires ALL gold documents be present in pool)

| Dataset | Original fast32 | CE shortlist 64 | Wide retrieval 192 |
|---|---:|---:|---:|
| 2Wiki n=120 | 108 (90.0%) | 114 (95.0%) | 118 (98.33%) |
| MuSiQue n=160 | 80 (50.0%) | 108 (67.5%) | 142 (88.75%) |
| MoreHop context n=80 | 26 (32.5%) | 66 (82.5%) | 77 (96.25%) |

MuSiQue: from fast32 to CE64 +17.5 pp in full candidate-chain coverage, paired interval [+11.25,+23.75]; from CE64 to wide192 another +21.25 pp, [+15,+27.5]. Thus the pipeline discards many potential complete chains while shrinking candidates to what can affordably be reranked. Candidate oracle coverage is not real TopK result.

### Hard-chain audit

| Support count | N MuSiQue | Fast@5 | CE64@sourced@5 | Complete gold in fast32 / CE64 / wide192 |
|---|---:|---:|---:|---|
| 2 | 88 | 22 | 34 | 52 / 68 / 84 |
| 3 | 45 | 2 | 6 | 23 / 30 / 40 |
| 4 | **27** | **1** | **0** | **5 / 10 / 18** |

Among the 27 four-source queries, all four gold documents are present in the CE64 pool for **10/27**, but *none* is complete Top5. Eight additional four-source chains appear only in the wide192 pool and are eliminated prior to reranking. This supports both a **subclaim-to-source ranking** bottleneck and a **budgeted candidate selection** bottleneck. 4-source Top10 CE64 sourced = 1/27, versus fast 2/27. No 5–8-hop real benchmark has been demonstrated.

## CPU and gate costs

GitHub shared-process CPU. **These are not full deployed end-to-end costs**; dense and shared CE were computed for *all* queries during ablations. `actual_gated_ce_ms` separately times the independently executed CE subcall only, not full conditional retrieval/indexing.

| Stage mean (milliseconds/query) | 2Wiki | MuSiQue | MoreHop context |
|---|---:|---:|---:|
| BM25 | 0.552 | 0.742 | 0.392 |
| V7.1 graph stage | 0.161 | 0.215 | 0.094 |
| Dense query | 10.062 | 11.788 | 10.773 |
| Two followup BM25 searches | 0.863 | 1.289 | 0.586 |
| Shared CE candidate union (ablation) | 1,304.006 | 1,569.837 | 329.404 |
| **Separate actually gated CE call** | 0.001 | **1,486.807** | 0.001 |

A corpus-edge-density gate selects fast for **120/120 2Wiki and 80/80 MoreHop**, and CE for **160/160 MuSiQue**. It is NOT a validated query-specific proof-gap gate. Its MoreHop behavior exposes a limitation: dense semantic retrieval could be useful when no explicit title edges exist, yet the heuristic automatically chooses fast.

Indexing, model load, data download, startup, answer generation and real serving latency are excluded from these mean stage costs. MiniLM index embeddings cost ~14.0 sec (2Wiki), 56.1 sec (MuSiQue), ~0.26 sec (MoreHop). Exact model revisions and pip lockfiles not pinned, so runtime reproduction may vary. Per-query p95 stage times and raw outputs are in the downloadable artifacts.

## Provenance, originality and decision

No new semantic relationship is *entailed* merely because text contains a valid source span. Existing BM25, TF-IDF, MiniLM embeddings, RRF, graph traversal, CE reranking and conditional routing are not original inventions. Paired confidence intervals are exploratory across many tried methods/datasets and uncorrected for selection.

**Decision:** Preserve the V7.1 fast graph as a trusted inexpensive 2Wiki fallback. On MuSiQue-like paragraph corpora, larger source pools and pretrained CE can offer more complete evidence than V7.1, but are prohibitively expensive relative to fast retrieval and do not solve the four-source failure. Do not deploy globally or claim a proven novel PGER algorithm.

**Next falsifiable step:** Build a source-grounded *relation/subclaim-to-document* reranker that explicitly scores **connected four-source chains** inside the existing high-coverage 192-pool; compare equal CE-pair budgets 32/64/96 plus a no-chain CE baseline. Independently verify source-span entailment on a manually audited small sample, add a fast conditional execution path which skips dense/followups/CE *before* they run, and test on a sealed non-pooled corpus with a fixed answer reader. If 4-source Top5 stays zero, preserve this failure and pivot again.
