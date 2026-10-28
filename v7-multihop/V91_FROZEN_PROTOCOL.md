# PGER V9.1 — Frozen public multi-hop question test: lexical proof-gap proxy vs equal-budget frontier
**Frozen:** 2026-10-28. **Branch:** `v91-budgeted-proofgap-realqa-2026-10-28`. **Base:** `v90-decision-gap-budget-2026-10-28`. Main untouched; no reviewer agents, paid APIs, periodic workflows, or PR to main.

## Research question
Can we increase complete supporting-document chain recovery by spending **exactly two extra BM25 searches** on the *relationship that appears absent* in currently retrieved evidence, rather than blindly searching from the nearest document? This V9.1 prototype is an **honestly labeled lexical gap proxy**: it does *not* implement verified semantic/counterfactual answer sensitivity. Title-based relationships and BM25 are known primitives. Failure to improve the retrieval metric is a meaningful negative result.

## Locked arms and equal-budget constraints
- `fast`: untouched V7.1 BM25 + preindexed one-hop graph, no extra search calls.
- `original2`: two repeated original-question BM25 calls (negative control), same 60-result cap.
- `frontier2`: two BM25 searches seeded from high-ranked document titles and original-question terms. Cost-/frontier baseline.
- `gap2`: two BM25 searches seeded from plausible title anchors and relation tokens that appear in the question but not the source paragraph. Query/action priorities deterministic; source quote offset + SHA256 attached only as provenance. **That quote does not prove the predicted relationship or whether resolving it changes the answer.**
All three extra-search methods use the **same RRF projection**, same protected first two fast anchors, exactly two BM25 calls with 60 returned results each, and no gold sources at decision time. Report each action's query, source witness and cost. Matching call count does not imply identical CPU costs, so time is measured separately.

## Data and guards
- 2WikiMultiHopQA public validation: deterministic eligible sorted positions **1,801–1,920**, 120 questions.
- MuSiQue public validation: deterministic eligible sorted positions **1,281–1,440**, 160 questions.
- These exact question IDs are disjoint from previously reported PGER V7.1–V8.6 cohorts, but are still **public datasets repeatedly inspected by the research program**. The documents are pooled from the benchmark's supplied contexts and gold support is present in the index by construction. This is not a Wikipedia-scale/independent sealed benchmark.
- 2-, 3-, and 4-support-document breakdown, candidate chain recovery @5/@10, mean/p95 post-index CPU query path, BM25 and title-graph indexing cost, paired 4,000-resample question bootstrap intervals, paired wins/losses, per-question source and gap actions.
- **No fixed answer reader, citation entailment test, verified counterfactual decision, true 5–8 hop QA, official IRCoT, HippoRAG2, S2G-RAG, AdaKG-RAG, or SOTA assertion**. Unsupported relationship labels must be marked `unknown`, not proven or contradicted. Never select improvements based on these 280 questions and subsequently report this cohort as fresh.

## Reproduction
```bash
git clone --single-branch --branch v91-budgeted-proofgap-realqa-2026-10-28 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
pip install -r requirements.txt
python -m unittest discover -s . -p 'test_pger_v91.py' -v
python benchmark_v91.py smoke
python -u benchmark_v91.py run --datasets 2wiki musique --out results-v91
```

## Advancement gate
Only pursue a semantic proof-gap controller if `gap2` shows repeated, substantive paired improvements over **both** `frontier2` and `fast`, with robust 3-/4-source recovery at equal cost. If it does not, preserve the negative result and return to explicit source-grounded relationship extraction and independently annotated answer-changing counterfactual gaps.

## Novelty assessment
Published S2G-RAG (ACL 2026), AdaKG-RAG (2026), A2RAG (2026), HippoRAG2 and related systems already cover evidence sufficiency, missing facts, graph retrieval and adaptive cost. Search query templates, lexical missing-word detection, BM25, RRF and source hashing are not inventions. **V9.1 does not itself prove a novel algorithm.**
