# PGER V8.5 — Frozen connected-source selection experiment

**Branch:** `v85-chain-selection-2026-10-27`, created from `v84-recall-funnel-2026-10-27`. The default branch and all prior experiments remain untouched.

## Testable claim
Holding the exact pretrained cross-encoder scores and the same 96-document candidate shortlist fixed, can a *connected source-portfolio beam selector* place more complete four-source evidence sets in Top 5 than a protected independent-document cross-encoder? This is a new test, **not a proven innovation**. BM25, graph matching, beam search, reranking, and source-provenance verification are standard. Observed textual links do **not** establish natural-language entailment or facts.

## Frozen methods
1. `bm25`: unchanged sparse retrieval.
2. `v71_fast`: unchanged indexed one-hop title graph seeded by BM25.
3. `ce32`, `ce64`, `ce96`: a nested deterministic RRF shortlist, common pretrained CE scores computed once on the 96 set; protected first two documents (same CPU scoring for ablation, lower hypothetical calls for 32/64).
4. `ce96_sourced`: source-offset-checked directional cue scoring, same 96 source pool/scores.
5. `v85_chain96`: beam width 8; select 5 sources beyond two anchors; CE scores + small title term coverage bonuses + source-offset-verified directional title-link bonus. No entailment, no proof of answer-changing relationships.
6. `v85_early_gate`: conservative query/title-only gate applied before scoring: direct title lookup can use V7.1 fast; all other questions choose `v85_chain96`. Benchmark computes all research ablation scores regardless of gate, but also runs an **independent conditional query path before these ablations**. The gated cheap path skips TF-IDF, dense query embedding, follow-up BM25 and CE; the expensive route executes all downstream stages separately. Log BM25+graph+full routed query path mean/p95. Shared warm-process indexing and model loading are excluded; this is not deployed end-to-end latency.

Dense model `sentence-transformers/all-MiniLM-L6-v2`, CE `cross-encoder/ms-marco-MiniLM-L6-v2`, CPU 2 threads, CE max_length 192 tokens, score full 96-pair list once for 32/64/96 ablations, one independently executed complete downstream search-plus-96-pair CE chain on gated expensive queries. No paid APIs/reviewer agents/scheduled jobs. Exact model revision hashes and pip lock not pinned; performance may vary.

## Cohorts
- 2WikiMultiHopQA public validation: deterministic eligible questions 1561–1680 (n=120), next unseen question IDs under established V7 sort seed.
- MuSiQue public validation: deterministic eligible questions 961–1120 (n=160), next unseen IDs under established sort seed.
- These are **question disjoint within repeatedly reused public task families**, pooled source universes with gold in the collection by construction. These are NOT sealed independent tests or full Wikipedia retrieval.
- Gold never enters candidate generation, CE input, ranking, or router. Gold-only diagnostics follow all ranked outputs.

## Mandatory evaluation
- Binary complete chain@5/@10, evidence recall@5, 2/3/4 supporting-document stratification, candidate full-chain oracle at fast32, shortlists 32/64/96, wide192, paired wins/losses and 5000-resample paired bootstrap intervals.
- Compare chain vs `ce96` at **identical candidate/model budgets** (causal ranking ablation), and vs V7.1 fast (practical cost/quality baseline).
- Separate BM25/index, graph, dense-index construction, per-query BM25, dense query, CE shared inference, chain reranking, and independent gated **full downstream CPU** cost. Not production end-to-end latency.
- Log sourced edge spans with exact offsets, but never call them proof of relational entailment; report failures.
- Stop/go: if 4-source MuSiQue complete@5 remains 0 or ranking regresses, explicitly say hypothesis unsupported. No generated final answers or verified 5–8-hop completion, no IRCoT/HippoRAG2 official run or SOTA claim.

## Reproduction
```bash
git clone --single-branch --branch v85-chain-selection-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install -r requirements.txt
python -m unittest discover -s . -p 'test_pger_v85.py' -v
python benchmark_v85.py smoke
python benchmark_v85.py run --datasets 2wiki musique --out results-v85
```
One-time branch-scoped push CI only; no cron.
