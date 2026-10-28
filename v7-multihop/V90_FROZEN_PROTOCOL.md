# PGER V9.0 — Budgeted Relation Generation + Decision-Sensitive Proof-Gap Prototype

**Protocol frozen:** 2026-10-28, prior to the V9.0 REBEL GitHub benchmark.
**Branch:** `v90-decision-gap-budget-2026-10-28` forked from `v89-rebel-generator-2026-10-27`; `main` untouched.
**No paid APIs, no reviewer agents, no recurring monitoring.**

## Research purpose, limits, and prior art

This is **two distinct pieces of work**:

1. **Natural-document efficiency experiment:** does question-independent source-sentence selection preserve more of an existing open-weight relation generator's true annotated relationships per unit CPU than equally budgeted first-two and lexical-top-two controls? Selection is a standard greedy/set-cover heuristic; **not claimed as novel**. Reports gold-positive recall, source overlap and measured inference time, not open-world precision or answer correctness.
2. **Formal proof-gap controller prototype:** a provenance-invariant, bounded-cost decision-sensitivity scheduler. It maintains separately sourced, refuted and unknown dependencies and tests whether resolving an unknown edge as supported versus refuted would alter the *set of feasible or supported answers*. Its output is a proposed retrieval target, not a verified fact. **Only 2–8-edge synthetic unit tests are executed here; no real multi-hop algorithmic performance claim.** The counterfactual decision-impact idea is also related to known value-of-information methods; novelty is not proved.

Closest 2026 prior art: **S2G-RAG** (ACL 2026) already produces structured gaps and next search queries; **AdaKG-RAG** (July 2026) already uses evidence sufficiency, targeted hypothesis verification and graph-guided expansion; **A2RAG** (2026) already adaptively escalates with provenance. Even combining these ideas is not automatically original. A future algorithmic claim requires a more specific mechanism with matched-budget head-to-head experiments, demonstrated correctness and priority evidence.

## Frozen REBEL data selection / models

- Official **DocRED** public development/validation `dev.json.gz` of 998 Wikipedia documents, SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`.
- Deterministically selected **36 new gold-positive documents** at eligible V8.8 positions **61–96**, which do not overlap V8.7's 54 previously tested documents or V8.8/V8.9's first 60; selected index SHA256 `eb2ec5d8235d9a1008a242f7b6df96d1bd04bf370f90e07c75fac4b4cd79d3aa`.
- Cohort selection uses known-positive 16-property DocRED annotations **for eligibility only**. Prediction and sentence selection are forbidden from looking at gold entities, gold triples, or annotated evidence IDs; gold data is used only for post-generation scoring. The cohort is *new to prior PGER inspection*, but remains public development data, not sealed or model-independent. REBEL pretraining exposure is unknown.
- For each document, candidate set is **the first six source sentences** with 20–500 characters, preserving native source sentence IDs. The same `Babelscape/rebel-large` checkpoint pinned at `44eb6cb4585df284ce6c4d6a7013f83fe473c052` is run *once per eligible sentence* for all comparisons, with first 256 input tokens, greedy (`num_beams=1`, `do_sample=False`), `max_new_tokens=96`, two CPU threads. Licence: **CC-BY-NC-SA 4.0**; check noncommercial / share-alike obligations.

## Frozen controls / ablations

- `first2`: first two eligible sentences, two generator calls.
- `lexical2`: two sentences with highest cheap relation-cue and entity-pair score, no gold.
- `coverage2`: **greedy marginal pair and entity coverage** plus lexical cue diversity; two calls, no gold.
- `coverage3`: identical selector, three calls.
- `full6`: all six eligible sentences (or fewer if document has fewer).
- Matched regex baseline computes exact-head/relation/tail triples only on the same selected sentences, per method.
- REBEL parsed labels are mapped to **the same frozen 16-property ontology as V8.9**. Evaluated raw mapped vs strict source-anchored mapped; anchoring requires both generated entities appear literally in cited sentence. Cited quote and SHA256 are validated, **but are NOT proof of entailment**.
- Per-arm CPU time = sum of *measured per-sentence inference durations* from a common frozen generator run, not actual separate deployed serving latency. Model loading and offline indexing remain distinct. If a later model is selectively invoked, measure the full actual gated path separately.

## Metrics, uncertainty, decision rule

- Exact directed positive-gold triple recall, raw mapped recall, gold annotated evidence-sentence overlap, emitted triples, source-span hash integrity, number of calls, mean/p95 per-doc CPU inference time and model load.
- 4,000 document-cluster paired bootstrap resamples for `coverage2 – first2`, `coverage2 – lexical2`, `coverage2 – full6`, `coverage3 – full6`, seeded 20261027. Count paired per-document wins/losses, and cost-versus-recall tradeoff.
- Generate independent HUMAN_REVIEW_PENDING annotations for generated triples. They are **not** declared entailed or false. DocRED lacks exhaustive annotations, so **no precision from unmatched predictions**. No NLI correctness, full 4–8-hop accuracy, final answer generation or abstention calibration can be inferred.
- Reject an efficiency-superiority claim if cheap candidate selection does not beat the equal-generation-call control, or if it loses too much gold-positive recall. Reject a PGER novelty/SOTA claim regardless of this component pilot: proof-gap scheduler has not been externally validated.

## Reproduce

```bash
git clone --single-branch --branch v90-decision-gap-budget-2026-10-28 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install 'numpy>=1.24,<3' 'transformers==4.52.4' 'safetensors'
python -m pip install 'torch>=2.3,<3' --index-url https://download.pytorch.org/whl/cpu
python -m unittest discover -s . -p 'test_pger_v90.py' -v
python -m unittest discover -s . -p 'test_proof_gap_controller.py' -v
python benchmark_v90.py smoke
python -u benchmark_v90.py run --out results-v90
```

A one-time branch-scoped GitHub Actions workflow runs the benchmark; **no cron**. Output includes full per-document results, review queue and dependencies. For next steps: compare a query-conditioned version of decision-sensitive proof-gap scheduling at equal BM25, CE and REBEL budgets against **S2G-RAG, AdaKG-RAG and A2RAG** plus the simple fast V7.1 baseline. Use an independent held-out corpus and a fixed answer reader; **4–8-hop performance not yet evaluated here**.