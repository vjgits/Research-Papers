# PGER V7.3–V8.2: frozen sequential ablations

**Status before execution:** new frozen public-validation question cohort; no reviewer agents, no paid API, no schedules, no changes to `main`.

**Hypothesis:** A better *evidence-candidate rescue* phase, followed by joint-chain-aware ranking and selective proof-gap pursuit, improves complete support recovery without unacceptable search cost. The V7.2 source-ledger's observed no-memory tie is accepted as a negative result. This is a diagnostic research prototype, not a general semantic parser or proof checker.

## Locked ablations

1. `bm25`: original sparse retrieval, same pooled collection.
2. `v71_fast`: **unchanged** indexed BM25 + 1-hop graph implementation from V7.1.
3. `v73_lexical_control`: common fast seeds, exactly TWO additional BM25 calls, lexical query expansion, simple document scoring.
4. `v73_rescue`: SAME two additional BM25 calls and SAME simple scoring, but use source-grounded title links, *reverse* source mentions, and missing-question-term relation-target queries.
5. `v80_joint`: IDENTICAL V7.3 rescue candidate pool and search calls, but greedy coherent-evidence selection with marginal coverage plus observed source edges.
6. `v81_proofgap`: IDENTICAL pool/search calls, with extra reward for sourced relation edges relevant to an unresolved query predicate and explicit dependency edges with exact original span offsets. No verified causal counterfactual inference.
7. `v82_adaptive`: route only short, well-covered noncomparative questions to `v71_fast`, others to V8.1. This method intentionally trades accuracy versus cost; it does not claim *equal total cost* with the others.

### Independent-measurement limitations

- Public **question-disjoint** 2Wiki validation positions 721–960 (n=240) and MuSiQue positions 321–480 (n=160), using V7 sorting/filtering and only those questions' pooled sources. Prior V7/V7.1/V7.2 questions are excluded. However, iterative tuning on different portions of these public datasets does **not** constitute a sealed independent evaluation or full Wikipedia benchmark.
- Gold IDs and annotations are used **only after** ranking to calculate per-question metrics, candidate recovery, and missing-source diagnostics. No gold in indexing, prompts, routing, retrieval, or scoring.
- Report `chain@5`, `chain@10`, `gold evidence recall@5`, by 2/3/4 supporting sources, oracle candidate coverage, paired wins/losses and 5,000 paired bootstrap 95% intervals, and index time versus query time. Source evidence relation ≠ entailed fact; no generator or answer correctness measured.
- Direct head-to-head for IRCoT and HippoRAG2 remains unimplemented and must not be implied.
- Two extra BM25 calls are matched across lexical control and rescue; extra offline graph/index lookups and CPU time may differ, and are reported. Comparing V8.0 and V8.1 holds candidate pools fixed, so any changes are ranking-only.
- `EvidenceMap.chain()` supports eight source-to-source transitions with exact source spans and cycle checks, tested on *synthetic deterministic* data. This does not establish five-to-eight-hop generalization on natural-language datasets.

## Hypothesis rejection criteria

- Candidate-rescue hypothesis fails if matched lexical candidate coverage does not improve or costs outweigh benefits.
- Joint-ranking hypothesis fails if retrieval chain@5 does not improve over candidate-rescue scoring with the exact same pool.
- Proof-gap hypothesis fails if it does not beat matched joint ranking with the same budget.
- Adaptive stopping hypothesis fails if it reduces answer-chain recovery for negligible cost savings.
- The entire V8 experimental family does **not** prove any new algorithm if results only reproduce known graph retrieval, keyword expansion or common reranking.

## Reproduce once

```bash
git clone --branch v8-adaptive-proofgap-2026-10-27 --single-branch https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install 'numpy>=1.24,<3' 'scipy>=1.10,<2' 'scikit-learn>=1.3,<2' 'pyarrow>=17,<27' 'pyahocorasick>=2,<4'
python -m unittest discover -s . -p 'test_pger_v8.py' -v
python benchmark_v8.py smoke
python benchmark_v8.py run --datasets 2wiki musique --out results-v8
```

Actions workflow only runs on **new-branch push** of the fixed files or manual dispatch, no cron. The measured results must be reported including failures.
