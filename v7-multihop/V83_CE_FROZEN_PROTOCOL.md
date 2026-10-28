# PGER V8.3 — Frozen open-weight semantic reranking evaluation

**Status:** Pre-run protocol; not a proven improvement. Branch `v83-ce-provenance-2026-10-27` is isolated from `main`, forked from `v8-adaptive-proofgap-2026-10-27`. No paid APIs, reviewer agents or recurring schedules.

## Hypothesis

A pretrained cross-encoder might rank the supporting documents more accurately than lexical/graph heuristics. Existing off-the-shelf cross-encoder methods are not PGER inventions. Cross-encoder per-passage relevance is **not** evidence-chain correctness or logical entailment. Test whether protecting V7.1 anchors and independently verified source *span offsets* reduces regressions. Exact spans show a statement was present, **not** that it is true or entails the inferred relationship.

## Locked retrieval and scoring ablations

1. `bm25`: unchanged sparse retrieval.
2. `v71_fast`: unchanged V7.1 BM25+offline title graph.
3. `lexical_rescue32`: no-CE lexical reranking of the **same rescue32 candidate pool**.
4. `ce_fast32`: CE reranks only V7.1 Top 32.
5. `ce_rescue32`: CE reranks first 16 V7.1 anchors + up to 16 rescue candidates, no protection.
6. `ce_protected32`: identical rescued 32 passages/scores, original first two fast sources protected.
7. `ce_sourced32`: identical protected pool/scores plus fixed +0.08 for exact-source-span directional cue connecting candidate to already selected evidence. This heuristic is not semantic entailment.
8. `ce_adaptive`: fast V7.1 for pre-declared simple well-covered questions, else sourced reranking; benchmark still computes CE for **all questions**, so routing CPU savings are modeled, not measured end-to-end.

Rescue uses two extra BM25 queries; CE-fast does not need rescue searches for deployment, though benchmark generates and scores the union once for paired ablation. FAST_N=32, RESCUE_N=32, PROTECT_N=2. Common CE scores are reused without per-arm recomputation. Model `cross-encoder/ms-marco-MiniLM-L6-v2` using sentence-transformers CrossEncoder, sigmoid, CPU, two PyTorch threads, batch=32, max_length=192 tokens, title + first 1,000 characters. **No fine-tuning**, no paid inference. Record model init and query latency separately from indexing and downstream selection. If model download fails, mark incomplete; no silent replacement.

## Fresh public-validation windows (not independent sealed benchmark)

- **2Wiki:** valid deterministic sorted positions 1,201–1,440, n=240, pooled title-deduplicated documents.
- **MuSiQue:** valid deterministic sorted positions 641–800, n=160, pooled question-supplied distractor and support paragraphs.
- Earlier PGER development/guarded V8.3 evaluated the preceding positions, including 2Wiki 961–1,200 and MuSiQue 481–640. This cohort has **disjoint question IDs**, but the **same public benchmark families repeatedly analyzed**. Gold supporting docs exist by construction; this is not full Wikipedia/open-web retrieval.
- Supporting IDs are read only after retrieval/ranking for metrics and posthoc candidate audits.

## Metrics and interpretation

Chain-complete@5/10, per-source evidence recall@5, per 2/3/4 gold source count, candidate-pool oracle coverage for fast32 and rescue32, paired bootstrap 95% confidence intervals (5,000 resamples), paired wins/losses, source-span validity, source-edge trace counts, individual regressions and rescues, index vs query vs model-load/warmup CPU time (means and p95). Four supporting documents do not automatically prove four-step reasoning. No fixed answer reader, contradiction adjudicator, answer correctness, calibration, IRCoT/HippoRAG2 official comparison, SOTA or PGER originality claim.

## Commands

```bash
git clone --single-branch --branch v83-ce-provenance-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install -r requirements.txt
python -m unittest discover -s . -p 'test_pger_v83_semantic.py' -v
python benchmark_v83_semantic.py smoke
python benchmark_v83_semantic.py run --datasets 2wiki musique --out results-v83-semantic
```

One-time, branch-scoped GitHub Actions run; no cron. Preserve measured negative results. Changing the method after seeing scores on these question IDs is exploratory only and cannot be represented as fresh evidence.
