# PGER V9.0 — Frozen New-Document Relation-Generation Efficiency: Negative Novelty Result

**Date:** October 28, 2026  
**Branch:** `v90-decision-gap-budget-2026-10-28` (forked from `v89-rebel-generator-2026-10-27`; `main` untouched)  
**Successful one-time Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40649302368  
**Full per-document results and dependencies:** https://github.com/vjgits/Research-Papers/actions/runs/40649302368/artifacts/12798324480  
**Pre-run protocol:** [V90_FROZEN_PROTOCOL.md](V90_FROZEN_PROTOCOL.md)  
**Algorithmic prior art:** [V90_NOVELTY_PRIOR_ART_AND_GATES.md](V90_NOVELTY_PRIOR_ART_AND_GATES.md)

## Executive decision

**The new greedy sentence-coverage heuristic did NOT beat inexpensive same-call controls.** On 36 new-to-PGER gold-positive DocRED public-validation documents (308 annotated 16-property relations), the standard lexical Top-2 selection (41/308 correct, 13.31%) outperformed both greedy coverage Top-2 (37/308, 12.01%) and first-two (39/308, 12.66%). Coverage Top-2 was also slightly **slower** than lexical Top-2 in measured shared-run sentence-inference CPU sums. Preserve the simple control; **no improved novel PGER algorithm or best-in-class efficiency proven**.

The new dependency-aware, source-hash-validated *decision-sensitivity gap scheduler* is implemented and passes synthetic mechanical tests, but has **not** undergone a real-question retrieval experiment, answer-generation evaluation, independently judged semantic support test, or matched-budget SOTA comparison.

## Frozen setup

- Dataset: official DocRED `dev.json.gz`, SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`; **36 previously uninspected PGER source documents** at deterministic V8.8 eligible positions 61–96, excluding the previous 54 V8.7 and 60 V8.8/V8.9 DocRED development documents. Selected document ID SHA256 `eb2ec5d8235d9a1008a242f7b6df96d1bd04bf370f90e07c75fac4b4cd79d3aa`. Public development dataset, **NOT sealed independent or model-unseen**; gold-positive eligibility known.
- Open model: pinned `Babelscape/rebel-large` revision `44eb6cb4585df284ce6c4d6a7013f83fe473c052`, greedy generation of 96 tokens per sentence, input truncated to 256 tokens, PyTorch CPU 2 threads, fixed 16-property relation projection. **CC-BY-NC-SA-4.0** licensed weights; this research-only checkpoint is not a production licensing recommendation.
- Gold entities/labels/evidence IDs were excluded from sentence selection and generation, read only after predictions. Each method selected from same first 6 eligible sentences, 20–500 characters, source IDs preserved. All source quote hashes matched. Quotation correctness **does not imply semantic entailment**.
- Exact directed positive-gold head/relation/tail recovery, not official DocRED F1, open-world relation precision, answer accuracy, real 4/8-hop ability, or contradiction/abstention calibration.

## Matched budget scores

| Method | Generator calls | Annotated true triples recovered / 308 | Recall | CPU inference total on shared-run timed sentences | Per-doc mean |
|---|---:|---:|---:|---:|---:|
| First2 | 72 | 39 | 12.662% | 104.313 s | 2.898 s |
| **Lexical2** | 72 | **41** | **13.312%** | 107.462 s | 2.985 s |
| Coverage2 (new heuristic) | 72 | 37 | 12.013% | 108.095 s | 3.003 s |
| Coverage3 | 108 | 45 | 14.610% | 143.072 s | 3.974 s |
| Full6 | 204 | 51 | 16.558% | 218.300 s | 6.064 s |

All recall is **positive annotated exact triple** recall among 308 total. Full6 also found only 51/308, indicating major absolute semantic extraction weakness. All source hashes valid. Full6 model total after loading excludes ~9.880 seconds startup.

**Efficiency insight:** lexical2 uses ~49.23% of full6 generation CPU and recovers **80.39%** of full6 known-positive hits (41/51), but is still worse than full6 in absolute recall. Coverage3 retains **88.24%** (45/51) at ~65.54% of the CPU. The different methods generated different lengths and counts of text and results; 'percentage of full6 hits' is a yield fraction, not a new accuracy benchmark.

## Paired document-cluster uncertainty (4,000 resamples)

| Pair | Recall difference (pp) | 95% bootstrap CI (pp) | Per-document wins / losses |
|---|---:|---|---|
| Coverage2 vs first2 | -0.649 | [-4.445, +2.894] | 4 / 4 |
| Coverage2 vs lexical2 | **-1.299** | [-3.869, +0.664] | 1 / 2 |
| Coverage3 vs full6 | -1.948 | [-3.729, -0.518] | 0 / 5 |
| Coverage2 vs full6 | -4.545 | [-8.077, -1.592] | 0 / 8 |

These intervals are exploratory and not multiple-comparison adjusted. The new method failed the advancement gate.

## Synthetic scheduler sanity check (separate; not real semantic evidence)

A local 500-case, random proof-DAG oracle simulation with a 24-cost-unit cap and perfect hidden verification found:

| Policy | Cases resolved correctly / 500 | Avg cost units across all cases |
|---|---:|---:|
| Decision-change-per-cost gap scheduler | 167 | 21.56 |
| **Simple frontier-per-cost** | **167** | 21.95 |
| Cheapest unknown first | 66 | 22.50 |
| Random | 60 | 23.42 |
| Common-first graph traversal | 74 | 22.44 |

**Key negative novelty finding:** The decision-aware controller **ties the simple existing-style frontier-per-cost heuristic in solved-case count** on this authored distribution. All methods use a perfect hidden ground-truth oracle. This is **not natural language retrieval**, is not independent, and cannot prove correctness or novelty. The simulator source is a separate local artifact; the branch's 14 unit tests cover actual source-hash invariants and the 8-edge graph behavior.

## Prior art and original contribution boundary

- S2G-RAG (ACL 2026) already models structured missing information and evidence sufficiency.
- AdaKG-RAG (2026) already performs hypothesis-verification retrieval, adaptive graph expansion and matched-budget comparisons.
- A2RAG (2026) already addresses cost-aware escalation, provenance and evidence loss.
- Greedy coverage, value of information, source hashing, NER, REBEL and graph traversal are known. **They are not PGER inventions.**

**Proposed, unproven** distinctive direction: rank unknown *sourced relationships* by whether verified-vs-refuted outcomes change the answer decision, measure *actual evidence-search cost*, and stop only with one justified supported answer or abstain. Whether this whole combination is new **has not been established** and whether it performs better is still untested.

## Reproducibility and next gate

- Source code committed on isolated branch: `pger_v90_core.py`, `proof_gap_controller.py`, `benchmark_v90.py`, seven tests each, the frozen protocol, and one-time GitHub workflow. No recurrent schedule.
- The matched-budget full-generation experiment and raw predictions are preserved in the Actions artifact. Open source model revision and Python dependencies recorded. No paid APIs, review agents, main updates, or production deployment.
- **Next**: a genuinely query-conditioned, end-to-end proof-gap selection experiment with verified claim-to-answer dependencies; matched source-search/CE/generation budgets vs cheapest/frontier, V7.1 fast, and actual external S2G-RAG/AdaKG-RAG/A2RAG implementations. Include 4+ gold-source tasks, a fixed answer reader, citation entailment and abstention calibration. Independent blinded natural-document relation annotation required. If no win against frontier or named published systems, reject novelty/performance hypothesis.

**Bottom line:** V9.0 improves evaluation discipline but does **not** deliver a new winning algorithm. The lexical two-sentence control is the efficient baseline on this test, and the broader PGER vision remains a research hypothesis.
