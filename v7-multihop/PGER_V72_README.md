# PGER V7.2 — Provisional source-backed relation ledger

This branch forks `v71-context-ledger-2026-10-27`, NOT `main`. **Status: controlled retrieval-only prototype.** Code was frozen before the next public-validation question-disjoint cohort. No paid APIs, no reviewer agents, no scheduled scans, no official IRCoT/HippoRAG reproduction, no answer generation or SOTA claim.

## Measured outcome (fresh-cohort run, 2026-10-27 Pacific)

**Retained relation memory did NOT beat the matched reset/no-memory method.** Across all 400 fresh validation questions, Top-5 and Top-10 complete-chain results were identical on a paired per-question basis. 2Wiki V7.2 @5/@10: 75.42%/86.67% versus cheap V7.1 graph 76.25%/82.50%. MuSiQue V7.2 @5/@10: 16.88%/27.50% versus cheap V7.1 graph 16.88%/25.63%; MuSiQue four-support @5 remains 0/28. Extra searches/latency remove any claim of a better fast-path default. Full results, paired CIs, indexing/query timing and concrete misses: [V72_FRESH_RESULTS_AND_LIMITATIONS.md](V72_FRESH_RESULTS_AND_LIMITATIONS.md). [Successful Actions run](https://github.com/vjgits/Research-Papers/actions/runs/40610829554); [per-query artifact](https://github.com/vjgits/Research-Papers/actions/runs/40610829554/artifacts/12782766998).

## Research question

Does a *retained, source-verifiable surface-relation/dependency ledger* improve complete multi-document evidence chains compared with (a) fast BM25 + V7.1 indexed one-hop title graph and (b) the same V7.2 controller with relation memory reset? Does any benefit survive on MuSiQue three-/four-source cases at Top 5/10 when extra BM25 search work is matched?

The ledger is deliberately **not** an LLM or learned semantic parser. It recognizes a narrow inventory of literal relation cues; a title mention with no defensible predicate is recorded as `association` and never treated as a proven triple. An asserted cue additionally requires observed local mention ordering. Every observed edge has source/target IDs, exact source quote offsets, normalized cue label and a dependency predecessor. All quoted offsets are programmatically checked against source text. Contradictions are only potential conflicts in a small set of functional predicates, not truth adjudication.

## Comparative design (frozen)

- `bm25`: retrieval-only sparse baseline.
- `bm25_graph_v71`: **exact unchanged** V7.1 indexed one-hop graph, seeded by BM25; no dense embedding stage.
- `v72_no_memory`: a shared-candidate, 3-expansion controller that scores local source-linked relations but clears past relation coverage every step.
- `v72_relation_ledger`: same indexes, candidate pool, gate, seeds, 2 additional BM25 calls maximum, fanout 8, beam 8, 3 expansions and TopK; remembers previously encountered source-linked predicates and entities during scoring.

Candidate generation is shared between the memory/reset arms to isolate retention. A cheap lexical gate prevents the more expensive path when the first source already covers 75%+ of non-stopword question tokens; the same gate applies to both arms. Any quality difference is not automatically novel. The relation index is built offline from passages/titles only. The query-specific followups use source spans and question words, never gold support labels.

## Evaluation

The older two 240-question 2Wiki cohorts already occupy the **first 480 eligible** deterministically sorted 2Wiki validation questions; V7.2 takes positions 481–720. Earlier MuSiQue occupies the **first 160** deterministically sorted eligible validation questions; V7.2 takes 161–320. The fresh cohort has **new query IDs**, but all questions belong to the same public validation datasets. Thus it is *not* an external sealed final test, and the pooled documents make results incomparable to full-corpus retrieval benchmarks.

Outputs: per-query Top5/Top10 binary chain, per-source recall, gold IDs only in post-retrieval diagnostics, full ranked IDs, shared candidates, sourced evidence dependency trails, gate activations, ranking-vs-candidate-miss diagnostics, 5,000 replicate paired bootstrap 95% confidence intervals, 3-/4-hop breakdown, offline index times and per-query post-index CPU path costs. Do not call this final-answer correctness or provenance entailment fidelity: those require fixed-reader human/automatic evaluations not yet implemented.

## Run

```bash
git clone --branch v72-proof-gap-relation-ledger-2026-10-27 --single-branch https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install 'numpy>=1.24,<3' 'scipy>=1.10,<2' 'scikit-learn>=1.3,<2' 'pyarrow>=17,<27' 'pyahocorasick>=2,<4'
python -m unittest discover -s . -p 'test_pger_v72_core.py' -v
python benchmark_v72.py smoke
python benchmark_v72.py run --datasets 2wiki musique --out results-v72
```

GitHub Actions `.github/workflows/pger_v72.yml` supports a **single new-branch push** and manual `workflow_dispatch` only; there is no cron. The V7.1 branch and `main` are untouched. Download `pger-v72-fresh-retrieval` from the successful Actions run to inspect per-query JSONL, summaries and negative results. If the pipeline fails, *do not* report improvement until repaired/re-run on the same frozen questions with transparent protocol deviations.

## Important limitations and prior work

- Fast title graph and Aho-Corasick pattern matching, BM25, search gating, graph traversal and standard reviews are not original inventions.
- Cues are rule based, weak, high risk of missing implicit relations; `asserted=true` is only a surface-level orientation heuristic, not natural-language entailment.
- The trained or open-source LLM-based relation extractor needed for genuine implicit 3/4-hop proof gaps is a **future ablation**; V7.2 cannot be called a complete semantic ledger.
- Question-disjoint public development cohorts do not justify independent generalization claims; a sealed split must be held out after further version tuning.
- Related work includes IRCoT (ACL 2023), HippoRAG, Q-DREAM (ACL 2025), SDRAG (EMNLP Findings 2026), and studies of the per-hop fact-grounding gap (EMNLP 2026).

See `V72_DEV_FAILURE_AUDIT.md` for the pre-code audit (original V7.1 results) and exact limitations.