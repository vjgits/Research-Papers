# PGER V11 frozen facet and lexical witness experiment — NEGATIVE confirmation

**UTC 2026-10-28. Successful GitHub Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40720291234
**All question-level data:** https://github.com/vjgits/Research-Papers/actions/runs/40720291234/artifacts/12829784500
**Branch:** v11-facet-witness-evidence-2026-10-28 (isolated; main unchanged).

Initial attempt 40720132774 failed its smoke test because the facet parser required three non-stopword tokens per clause and rejected short, valid clauses. No benchmark was run. Commit 873b646 corrected the clause minimum to two and the accepted job ran successfully. It was a pre-benchmark input-handling correction, not confirmation tuning.

## Design, comparison, and scientific boundaries

Reused official released MultiHop-RAG 609-article corpus and identical question offsets as V10.1 (0–399 development, 400–799 public confirmation). Reused existing gold URL/unique-title mapping, excluding 84/400 and 77/400 unresolved cases, respectively. Evaluable 316 and 323 questions. This is not a sealed validation; prior V10.1 already examined those questions. Gold source identities used only in offline scoring.

Arms: unchanged BM25, unchanged V7.1, V9.5 two-search lexical expansion; frozen 2-facet and up-to-4-facet BM25 fusion; each with optional sentence-level lexical witness selection; and a four-source-phrase query control. Comparison reports actual number of BM25 calls (facet average **1.77** versus V9.5 **2**, source phrase control **4**). No paid APIs or models, no gold-derived online routing, and no source-edge entailment verification.

**Important:** lexical source-sentence similarity and a retained hash demonstrate only that text exists in a passage, not that the passage supports the question's relation or answer. Question decomposition, evidence diversity and lexical sentence overlap have extensive prior art (ChainRAG 2025; DEC 2025; QD-ECS 2026; AdaKG-RAG 2026; SPARE-RAG 2026). Do not claim invention or SOTA.

## Confirmation complete source evidence@5 (n=323)

| Arm | AE@5 | AE@10 | 4-distinct-source cases AE@5 |
|---|---:|---:|---:|
| BM25 | 40.5573% | 63.1579% | 1/54 |
| unchanged V7.1 | 39.6285% | 62.8483% | 1/54 |
| V9.5 2-query lexical | 35.9133% | 59.4427% | 1/54 |
| V11 2-facet fusion | 39.9381% | 62.2291% | 1/54 |
| V11 2-facet + lexical witness | 37.1517% | 62.2291% | 1/54 |
| V11 4-facet fusion | 39.9381% | 61.9195% | 1/54 |
| V11 4-facet + lexical witness | 37.4613% | 62.2291% | 1/54 |
| V11 source phrase 4 extra searches | 35.2941% | 60.0619% | 2/54 |

- V11 2-facet fusion vs V7.1: **+0.31 pp**, paired 95% CI **[-1.55,+2.17]**, 5 wins/4 losses: **not a meaningful improvement**.
- 4-facet fusion same AE@5, no gain despite extra logic.
- Lexical witness selection loses to simple fusion. Witness scanning alone averaged **34.54–35.45 ms** CPU per question, whereas V7.1 has been ~1–2ms in this setting. 2-facet fusion has 1.77 query calls on average; another four-query source phrase arm regressed substantially overall.

### KEY post-hoc opportunity — 4 distinct document questions

The shared candidate diagnostic pool (`fast Top80 + BM25 Top80 + facet hits`, truncated to 120 documents) contains *all four* annotated documents on **53/54** evaluable four-source confirmation questions, but only **1/54** is selected in final Top5. That is an optimistic high-recall candidate pool, NOT a top-5 solution and not a novel retrieval method. A further 13/54 complete chains appear in facet fusion Top10. The high pool completeness is partly because 120/609 (~20%) of the entire small corpus may be admitted, which incurs real evidence selection cost. New research must explicitly budget pool size and rerank compute.

## Decision and research feedback to V11.1

**Fail V11**: no generic improvement and relation claims unverified. Retain prior V7.1/BM25 baseline, do not add unbounded searches or retain sentence heuristics as a production selector. No support for 5/8-hop claims; 4 *document* is not automatically 4 *logical hops*. No generated answers, source-support entailment evaluation, confidence or refusal gate.

**Next single grounded hypothesis V11.1:** Candidate coverage suggests a separately evaluated *trained lightweight passage reranker* may recover complete source chains more effectively than fixed lexical weights. Train on **development question annotations only**, not confirmation. Keep exactly the SAME fixed candidate pool, report candidate oracle ceiling as offline diagnostic, compare unchanged BM25/V7.1/rank-fusion and a no-learning feature control; score 2/3/4 source chain@5 with paired CIs, cold feature cost, p95, and model fit time. Establish evidence sentence and relation verifier validity by independent human judgments before any 'proof' claim. If improvement not meaningful, reject; do not repeatedly tune confirmation. Test cross-corpus transfer to avoid publication on a public repeatedly inspected dataset. Supervised ranking and source metadata matching are prior art.

No paid APIs, recurring automations, merges, main writes, or reviewer agents. Previous V7–V10.1 negative results preserved.
