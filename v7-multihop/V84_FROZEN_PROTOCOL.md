# PGER V8.4 — FROZEN Candidate Recall, Semantic Reranking and Actual Routing Pilot

**Pre-run date:** 2026-10-27 Pacific (2026-10-28 UTC)  
**Isolated branch:** `v84-recall-funnel-2026-10-27`, forked from `v83-ce-provenance-2026-10-27`. Main and V7.1 are untouched. No reviewer agents, paid APIs or schedules.

## Why: narrowly test two negative observations

V8.3 on previous public-validation cohorts: protected CE improved MuSiQue complete-chain@5 from 15.00% to 23.75% but reduced 2Wiki from 75.83% to 60.83% (65% with weak sourced-edge scoring). MuSiQue four-source questions scored 0/30@5; only 2/30 had all gold in the protected 32-candidate rescue pool. CE inference cost ~1.15 seconds/query for ~40 shared candidate pairs. Hypothesis: a larger **dense+lexical+graph candidate union** improves missing-source recall, while a bounded 64-passage selection and a **corpus-level non-oracle route** avoid damaging title-linked retrieval.

## Locked method definitions

- `bm25`: original sparse retrieval.
- `v71_fast`: exact original V7.1 indexed 1-hop graph.
- `v83_protected32`: original first-two protected source/keyword rescue32 candidate selection + the same CE model, no 64-item candidate union. Frozen V8.3 implementation.
- `v84_ce64`: 192 candidate pool assembled from fast80, BM25, TF-IDF, pretrained MiniLM dense top120, two source-derived BM25 followups, and offline title-mention/reverse graph; choose 64 by predetermined RRF+title overlap; pretrained CE rerank, preserving first 2 original fast documents.
- `v84_ce64_sourced`: identical candidate pool and CE scores with source-span-verified directional-cue bonus +0.08; **cue mention is not truth/entailment**.
- `v84_actual_route`: if graph title mention density <0.65 per source, return V7.1 fast; else short query with 2+ title words matched in top result may return V7.1 fast; otherwise run CE on *only* the 64-pair pool. No test answers or gold labels enter the gate. This corpus-level heuristic may overfit 2Wiki-like vs MuSiQue-like corpora, and is not proof of query-level universal adaptivity.

`v83_protected32` and `v84_ce64*` reuse union CE scores for same-question controlled ablations. In addition, the `v84_actual_route` method **separately executes the CE call for only routed queries**, so its mean+95th percentile gated inference latency is measured. Shared scoring for other arms still happens, so full experiment runtime is not deployment runtime. No learning/fine-tuning or paid inference.

## Evaluation and validation

- **2WikiMultiHopQA** public validation deterministic eligible positions 1,441–1,560: n=120.
- **MuSiQue** public validation deterministic eligible positions 801–960: n=160.
- **MoreHopQA** human-verified test: up to 80 deterministic SHA-ordered eligible examples; this dataset is another family, but draws on related base QA sources. A *new appended last hop* may not be present in provided contexts. **Only evaluate retrieval of support-title documents for the previous question**; do NOT call this added-hop answer correctness or 5+ hop reasoning. If no usable supplied-context labels, report not evaluated, never substitute invented labels.
- Pooled contexts for each dataset are used to construct small shared retrieval corpora; gold docs present by construction, not full Wikipedia.
- Model fixed as `cross-encoder/ms-marco-MiniLM-L6-v2` and dense `sentence-transformers/all-MiniLM-L6-v2`; CPU two torch threads, CE sigmoid and 192-token limit. No fine-tuning. Exact HF commit hashes and exact pip lock not pinned; prevent stronger reproducibility claims.
- Report complete chain @5 and @10, per-source recall@5, 4-support breakdown, candidate-full-coverage for fast32, 64 and 192, paired bootstrap 95% intervals (3000), wins/losses, exact source-span validity, model loading+offline indexing vs query CPU time including actually gated inference, mean and p95. No fixed answer reader, no contradiction adjudicator, no official IRCoT/HippoRAG2 head-to-head, no SOTA claim.
- **Decision:** preserve fast V7.1 as fallback unless the held-out paired comparisons and cost justify change. Any edits after observing results are exploratory only. Public dev families and MoreHopQA preceding contexts are not sealed independent end-to-end benchmarks.

## Reproduction

```bash
git clone --single-branch --branch v84-recall-funnel-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install -r requirements.txt
python -m unittest discover -s . -p 'test_pger_v84.py' -v
python benchmark_v84.py smoke
python benchmark_v84.py run --datasets 2wiki musique morehop --out results-v84
```

One-time GitHub Action on branch push only, with no cron. GitHub result artifacts include per-query IDs, rankings, candidate coverage and costs; failures and negative results must be reported.
