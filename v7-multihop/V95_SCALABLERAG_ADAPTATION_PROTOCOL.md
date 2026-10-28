# PGER V9.5 - Paper review, licensed prior art, and controlled next experiment

**Status:** preliminary, before any full-corpus retrieval evaluation. 2026-10-28.

## Source / originality boundary
Hasson, Chakravarty, Thomas, Gogineni (2026), **ScalableRAG: High-Quality RAG at Zero Ingestion Cost**, https://arxiv.org/pdf/2607.25135. Implementation: https://github.com/cohesity/ScalableRAG (Apache-2.0). Its named document/value set registry, set intersection/difference, positive/negative regex partitions, scope diagnostics, query-time aggregation, and branch-and-select are **prior art**, not a PGER invention. Cite and respect license if porting code. The enclosed V9.5 `set_workspace_v95.py` is an independently written restricted diagnostic implementation, not an independent novel algorithm.

## Key facts to avoid conflating
- ScalableRAG's **GPT-4.1-generated-answer accuracy** is distinct from PGER's **complete gold document chain@5**; do not compare percentage scores directly.
- The paper uses 1,000 MuSiQue and 1,000 2Wiki QA questions plus four other corpora. Zero-ingestion means *no corpus-wide neural preprocessing*, **not zero query cost**. Query-time regex scans and repeated LLM calls may be slower than V7.1's sub-2ms cached CPU retrieval.
- Its core representation assumes each grouping key aligns with a subset of documents; many-to-many, within-document and coreference relationships can violate this assumption.
- Published comparison: Zero-Ingestion ScalableRAG LLM-judge accuracy ~58.09% MuSiQue, ~85.74% 2Wiki; A-RAG ~57.00% and ~87.05%, respectively. Do not describe it as universally best.

## Why this may help PGER
V9.4 gains on MuSiQue at the cost of large 2Wiki regressions; zero four-source MuSiQue questions completed in Top 5. V7.1's fast one-hop title graph finds many 2Wiki chains, but title+relation heuristics can lose necessary documents in a static Top-5 ranking. A **provenance-preserving evidence-set workspace** can (a) retain candidate sets across independent constraints, (b) keep negative/excluded evidence for false-negative audits, (c) test set intersections/alternatives, and (d) expose unmet proof constraints. Existing V7.2 surface memory did not improve results; structural set operations must be evaluated against no-memory control.

## PREDECLARED next evaluation (not yet performed)
### Development
Run the unchanged V7.1 on official SAG2-released 2Wiki, MuSiQue, and HotpotQA corpora. For each question, form the initial Top-K set and perform at most two new deterministic queries. Compare:
1. **V7.1** (zero added calls)
2. **V9.2 nearest-document expansion** (matched two calls)
3. **ScalableRAG-style positive-only scoped filtering** (matched two calls)
4. **Positive+negative retained set workspace with source/anchor diagnostics** (matched two calls)
5. **PGER hypothesis**: choose next query by which unresolved constraint could change the answer; explicit state can be `known`, `refuted`, `unknown` only after grounded verification. If no independently reliable verifier, downgrade to `unknown` and do not call the method counterfactual verification.

**No paid LLM**, no gold evidence labels at inference, no oracle routing by dataset name or answer, and no changes to fast baseline. Any NLI/reranker arm must use a separately matched CE scoring budget and count CPU time. Source texts and document IDs must be identical for all arms. Measure both average evidence recall and **complete gold chain@5/@10** (particularly hard 3/4 evidence sources), 95% question bootstrap, per-query mean/p95, CPU/wall time, offline index build, candidate coverage, and actual cost (including set scans). Also measure rejected-source retrieval and frequency of useful negative-set rescues. The previous public benchmarks have been repeatedly inspected; use development splits and independent sealed final evaluation before claiming generalization.

### Independent test / acceptance criterion
Do not call this an improvement unless it beats **both** the fast method and an equal-budget nearest-frontier/scoped-filter control on a question-ID sealed set, with robust CI and no materially worse easy-question performance. A predeclared 4-source hard subset must show nonzero reliable gains. To claim *novelty*, distinguish the claimed decision sensitivity from ScalableRAG's set workspaces, SAG2's necessity scoring, S2G-RAG's evidence sufficiency and AdaKG-RAG's search planning, and run official-source or reproducible matched implementations.

## Current pilot implementation
`set_workspace_v95.py` implements pure in-memory named sets, positive+negative regex partitions, complement diagnostics, exact source offsets/hashes, set algebra, and side-effect-free previews. The tests only validate invariants on a four-document **synthetic** example. They are **not** multi-hop recall, semantic extraction, answer accuracy, novelty, speed superiority, or independent validation results.

No paid APIs, schedules, reviewers or modifications to main.