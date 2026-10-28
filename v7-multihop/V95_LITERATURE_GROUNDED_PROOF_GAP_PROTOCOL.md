# PGER V9.5 — Literature-grounded set-ledger and cost-aware proof-gap protocol

**Status: PRE-RUN RESEARCH DESIGN (no V9.5 evaluation has been executed).**
**Date:** 2026-10-28. Separate development branch, `main` unchanged.
**No paid APIs, reviewer agents, or recurring schedules.**

## Why this is a change of direction

Earlier PGER work demonstrated: V7.1's fast indexed BM25/title-graph retrieval was strong on 2Wiki, but weaker on MuSiQue 3-/4-source problems; V9.4's open-weight Ettin relevance ranker improved MuSiQue full-chain@5 on a public 120-question slice but degraded 2Wiki. Pure extra lexical searches and naive title-link graph/semantic extraction usually failed. When correct required sources reached the candidate pool, they frequently failed to make Top 5.

The specific new literature prompts came from:
1. **ScalableRAG: High-Quality RAG at Zero Ingestion Cost** (Hasson et al., 2026), https://arxiv.org/pdf/2607.25135 and Apache-2.0 code https://github.com/cohesity/ScalableRAG . Central capabilities: persistent typed **document/value set registry**, set intersection/union/difference, document-relative exclusion diagnostics, optional limited-ingestion pattern/FTS retrieval. In its original paper Table 1, Zero-Ingestion receives GPT-4.1-judge scores 85.74 on 2Wiki and 58.09 on MuSiQue, and Limited-Ingestion 86.76 and 58.91. **These are NOT PGER's complete-evidence-chain@5 metric** and must never be placed on the same numerical leaderboard. 'Zero ingestion' means no offline semantic index; it is not zero query processing, zero latency, or zero inference tokens.
2. **Microsoft LazyGraphRAG** (Edge et al., Microsoft Research blog, November 25, 2024), https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/ , summarized in the November 29, 2024 LLM Watch post https://www.llmwatch.com/p/graphrags-biggest-problem-solved . This is **not an official version called GraphRAG 2.0**. It uses cheap concept/co-occurrence community graphs, best-first/breadth-first iterative deepening and **deferred LLM relevance/claim extraction**, with tunable relevance test budget. Microsoft's reported cost savings are under its own 100 synthetic-query, news-article/LLM-judge benchmark; no direct PGER comparison.
3. **Retrieval-Augmented Generation for Large Language Models: A Survey** (Gao et al., arXiv:2312.10997v5, March 2024), https://arxiv.org/pdf/2312.10997 . Survey only; organizes naive, advanced, modular RAG and retrieval/generation/augmentation with metrics; **not new algorithmic evidence or a current SOTA benchmark**.

## What is already known — NOT a PGER novelty claim

Named set registries, regex filters, subset intersections, scoped diagnostics, cheap-first search, graph/community traversal, dynamic evidence sufficiency and budgeted escalation are existing methods, including ScalableRAG, LazyGraphRAG, S2G-RAG, AdaKG-RAG, A2RAG and value-of-information. Reusing them is engineering and benchmarking, not originality.

**Hypothesis to falsify:** A *source-grounded, answer-discriminating proof-gap scheduler* can determine a missing relation whose alternative outcomes change the supported candidate-answer set, and choose the least costly action expected to resolve that exact gap. It stores explicit supported/refuted/unknown relation states, provenance, and candidate/excluded document sets; query-time counterfactuals are simulated decision alternatives, **never evidence**. Whether this whole combination is novel is unknown pending finer prior-art sweep and measurable superiority to simple baselines.

## Experimental arms — one feature at a time

- **A. Fast fallback:** unchanged V7.1 BM25 + indexed one-hop title graph.
- **B. Simple repeat:** original query + two fixed-cost BM25 searches, no set state.
- **C. Named-set control:** same initial candidates, query-scoped positive/negative/unresolved document sets, exact set intersection/union/difference plus parent-relative coverage diagnostics. No learned counterfactual policy.
- **D. Relevance-first control:** V7.1 + a fixed 32-pair, open-weight Ettin relevance ranking; no proof-gap logic.
- **E. Budgeted breadth/depth control:** bounded, alternating top-ranked and neighboring source searches (LazyGraphRAG-inspired); identical total document inspections and model calls as F.
- **F. PGER hypothesis:** same document, search-call, candidate and scorer budgets; source-grounded candidate-answer dependency graph, estimated decision-changing proof gap and cost-normalized next-step selector. Unknown remains unknown and no answer emitted unless a fixed verified-evidence rule permits it.

**No arm may access gold sources or answers for routing**, and every retrieval/search/model call must be logged. When global/aggregative tasks are included, compare named-set algebra with a *faithful ScalableRAG baseline*, not simply claim that adding count/intersection is novel.

## Testing strategy, confirmatory gates

1. Before any expensive run, unit-test named sets and preservation of excluded candidates, missing-value/contradiction statuses, and source-span integrity. Use manufactured evidence with predetermined outcomes only for invariants, **not as research accuracy evidence**.
2. Test A–F on **one new, fixed question-ID disjoint slice of the public SAG2 official 1,000-question source corpus**, 2Wiki, MuSiQue and HotpotQA. Prior public subsets have been viewed extensively; this is development rather than sealed generalization. Keep indexing/source passages exactly equal across arms.
3. Report **full annotated evidence-chain@5/@10**, mean individual gold-document recall@5, candidate gold ceiling, stratified by 2/3/4 support counts, paired bootstrap CIs, per-query CPU ms and p95, model-inference/token calls, indexing time, cost per successful complete chain, and every regretful filter (gold document removed after a negative or set intersection).
4. Independently assess *final answer correctness and citation entailment* with a fixed reader and blinded human-annotated natural-source subclaims; a citation hash alone is only a location check.
5. Include a separate global/aggregate test (counts/intersections), since ScalableRAG/LazyGraphRAG are primarily strong there. They are not substitutes for the exact 4-hop MuSiQue retrieval test. Report the two task types separately.
6. Publish results and regressions. **Do not claim SOTA, NeurIPS readiness, novelty or most-efficient status** without official paired matched-system comparisons and a sealed external test.

## Resource and implementation safeguards

- Use SQLite FTS5/BM25 and existing V7.1 index as low-cost default. Prefer Python sets/bitsets/roaring bitmaps for named document sets, immutable per-source provenance (hash, exact span and original sentence). Keep set graph index construction costs separately measured.
- Optional open-weight Ettin 17M on selected queries only, measured **by an actually gated execution path**. Do not compute all expensive scores and then report fictional routing savings.
- No commercial license uncertainty: ScalableRAG repo Apache-2.0; inspect individual models and external dependencies. Microsoft's LazyGraphRAG blog is a conceptual source, not license to assume a complete drop-in open-source implementation.
- Limit one incremental experiment per design revision; do not change thresholds based on held-out results. Keep `main` untouched.
- First gate for promotion: **PGER must beat both fast and simple named-set/budgeted-search controls on complete chains at equal resource cost**, especially 4-source queries; otherwise reject the mechanism and preserve the measured failure.

## Plain-English analogy

Suppose you're tracking who owns a company. Instead of collecting 100 more company articles, keep three labeled piles: articles actually mentioning ownership, articles ruled out as irrelevant, and articles not yet checked. If the answer is still ambiguous, ask which fact would distinguish the remaining possible owners, then look for proof of that specific relationship. ScalableRAG contributes the *piles*; LazyGraphRAG contributes *don't do expensive work until needed*; PGER's **unproven** proposed contribution is choosing the *right unresolved fact based on possible answer changes at minimal cost*.
