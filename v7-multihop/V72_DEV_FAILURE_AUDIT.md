# PGER V7.2 pre-code failure audit (historical V7.1 samples)

**Status:** Baseline diagnostic only. Based on the untouched (for this analysis) V7.1 archived `Truth_V71_Lean_BM25_Comparison.zip` per-question records supplied in the research handoff. No new benchmark or claim of V7.2 improvement.

## Hard-chain recovery, complete source set found within Top K

| Existing development group | BM25 Top5 / Top10 | BM25 + indexed 1-hop Top5 / Top10 | Hybrid + indexed 1-hop Top5 / Top10 | Hybrid + four-hop retained keyword ledger Top5 / Top10 |
|---|---:|---:|---:|---:|
| 2Wiki, 4 supporting pages, n=46 | 0 / 0 | 23 / 30 | 25 / 32 | 25 / 32 |
| MuSiQue, 3 supporting paragraphs, n=53 | 3 / 8 | 3 / 8 | 2 / 11 | 4 / 11 |
| MuSiQue, 4 supporting paragraphs, n=33 | 0 / 0 | 1 / 1 | 0 / 0 | 0 / 0 |

## Diagnoses the supplied artifact can justify

1. **Ranking displacement exists:** 2Wiki four-source fast indexed graph rises from 23 to 30 complete chains when K increases from 5 to 10 (seven additional chains); the hybrid variant rises from 25 to 32. Some complete chains are therefore within Top 10 but outside Top 5.
2. **Four-source MuSiQue bottleneck is not Top-5 truncation alone:** fast BM25+graph remains at 1/33 at both Top 5 and Top 10. Its mean gold-paragraph recall is ~0.288 @5 and ~0.333 @10, so most missing sources remain outside output.
3. **More graph hops without better relations do not resolve the problem:** V7.1 hybrid retained memory resolves 0/33 MuSiQue four-source questions; matched reset is also 0/33. Across all 400 original questions the compact term-ID ledger has no binary complete-chain@5 wins vs reset.
4. **Positive results are dataset-conditional:** Four-source 2Wiki has stronger exact title edges and provides an easier link-discovery task than paragraph-specific MuSiQue.

## What cannot be inferred from the V7.1 archival JSON

The per-question output has method, gold-source count, TopK completeness, partial recall and traversal aggregate counts, but **not** the ranked source-ID list, all candidates considered, gold source IDs/evidence spans, reasons for candidate pruning, or per-edge source citation. Thus each missed source **cannot reliably be assigned** to (a) absent from the candidate pool, (b) no title edge, (c) implicit entity relation, (d) candidate present but ranked too low, or (e) spurious transition using archived data alone.

V7.2 instrumentation must log candidate IDs, top-10 rankings, missing gold sources and gold-only diagnostic classification after the query. The gold labels MUST NOT enter indexing, candidate generation, the gate or ranking. Inspect concrete misses manually before claiming semantic reasoning.

## Pre-registered design guardrails

- **Fast:** unchanged V7.1 BM25 + indexed 1-hop graph. Preserve a true fast path for easy questions.
- **Equal work:** same offline indexes, initial BM25 ranking, shared follow-up candidate pool and max 2 extra BM25 queries for V7.2 reset and retained ledger; same 3 graph expansions, beam 8, fanout 8, Top 5 and 10. Only memory retention affects scoring.
- **Provenance:** source ID, exact document-offset and quote, relation cue label, target ID, assertion/association qualifier, and dependency predecessor. Never promote an unsourced co-mention to a verified fact.
- **Data:** first 480 eligible 2Wiki validation questions and 160 MuSiQue validation questions already used; freeze code before evaluating questions 481–720 in the same deterministic 2Wiki ordering and 161–320 in the MuSiQue ordering. This is a **question-disjoint public-development cohort**, NOT a sealed external test or open-Wikipedia evaluation. Document pooling continues within each fresh cohort.
- **Statistics:** paired bootstrap 95% intervals for change in complete-chain@5/10, by-hop strata, losses as well as wins; report whole-path query and offline index latency separately. Log failures even if negative.
- **Not yet evaluated:** correct generated answers, claim entailment/citation accuracy, IRCoT and HippoRAG official baselines.

## Related work that bounds originality

- IRCoT (Trivedi et al., ACL 2023) interleaves reasoning and retrieval.
- HippoRAG and HippoRAG2 provide graph-style long-term retrieval frameworks.
- Q-DREAM (Ye et al., ACL 2025) explicitly models subquestion dependency and dynamic retrieval.
- SDRAG (Wang et al., Findings EMNLP 2026) explicitly models subquestion dependencies as a graph.
- Mo et al. (EMNLP 2026) identify per-hop retrieval-versus-fact-extraction failures.

The V7.2 prototype tests a combination of **conditional sourced subclaim gaps, differentiating retrieval, dependency/provenance recording, and cost gating**, not novel basic components. Any genuine novelty requires harder ablations and verification against these related systems.