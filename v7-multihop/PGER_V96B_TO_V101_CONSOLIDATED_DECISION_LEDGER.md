# PGER V9.6B–V10.1 Complete Research Decision Ledger

**Date:** October 28, 2026. **Status:** All requested stages V9.6B, V9.7, V9.8, V9.9, V10 and independently motivated follow-up V10.1 executed, with negative results retained. This document is an outcome ledger, NOT a new experiment, and not a SOTA/novelty claim.

## Evaluated stages and explicit gate outcomes

| Stage | Research decision | Evidence / process |
| --- | --- | --- |
| V9.6B source-witness chain assembly | **FAIL universal improvement.** Unchanged V7.1 still preferable. | V9.6B 2Wiki confirmation AE@5 65.83% vs fast 61.67% but paired CI crossed zero; MuSiQue 21.67% vs 20.83%, with zero 4-source complete chains out of 21. CPU witness ~9–14ms vs fast ~1–2ms. |
| V9.7 MIT BGE-small dense candidate retrieval | **PARTIAL component learning, FAIL retrieval/efficiency gate.** | MuSiQue full source candidate pool 65/120 V7.1 → 90/120 dense fusion, but AE@5 only 22.50% → 23.33%; four-support AE@5 0/17. 2Wiki AE@5 regressed 66.67% → 51.67%. Dense corpus indexing ~377/915 CPU-seconds (2Wiki/MuSiQue). Pretrained semantic retrieval is prior art. |
| V9.8 gold-independent cheap-first gate | **Correct protective no-op, not an algorithm gain.** | Development 7 dense-fusion wins vs 25 losses; fixed policy disabled routing. Confirmation 0/240 routed, unchanged V7.1 44.58% chain@5. No real wall-latency gain established. |
| V9.9 logistic retrieval completeness confidence proxy | **Promising proxy, not answer-truth confidence.** | Confirmation Brier 0.19575 vs constant 0.24818; ROC AUC .77914, 5-bin calibration error .09522. Top 40% confidence ~69.79% support-complete@5 vs 44.58% overall. No answers or true calibrated abstention tested. |
| V10 MoreHopQA human-verified corpus + source blackout | **Valid external 2-source title retrieval and missing-source stress, invalid for >2 source claims.** | Exactly 2 unique required source titles in all 1,118 examples, 601 pooled docs. V7.1 title@5 83.36%, V9.5 84.35%. Hash-blackout 77/601 removed; 255 questions lost source evidence. Corrected audit publicly recorded. |
| V10.1 MultiHop-RAG external news 2–4 source documents | **FAIL hard external transfer, key negative result.** | On 323/400 unambiguously mapped confirmation questions, BM25 AE@5 40.56%, V7.1 39.63%, V9.5 35.91% (V9.5 -3.72pp vs fast, CI [-7.43,-0.31]); four-required-source n=54, **only 1/54 complete Top5** for each method, V7.1 15/54 in Top10. 77 questions excluded from mapping—selection bias must be audited. |

### Scientific decisions

1. **Baseline retained:** V7.1 BM25 + title graph is a fast dataset-specific engineering baseline, NOT globally best. On external news MultiHop-RAG it loses slightly to plain BM25.
2. **Missing candidate vs chain ranking are separate, measured bottlenecks:** Dense fusion gives MuSiQue candidate recall, but not reliable complete chains; neither candidate expansion nor lexical title witnesses are enough.
3. **No universal improvement accepted:** All changes either regress some domains, cost too much, or fail four-required-source cases. Do not deploy any as a new default.
4. **No unsupported 5/8-hop claim:** MoreHopQA examples have two unique supporting sources; MultiHop-RAG four-source counts are not independently verified logical reasoning hops. No 5/6/8+ empirical retrieval success here.
5. **No factual answer verification demonstrated:** All main numbers are complete annotated document/title retrieval, not source-text semantic entailment, answer correctness, causal necessity or real abstention.
6. **Gold labels never used in online ranking or routing.** Used only in offline metrics and diagnostics. Public repeatedly examined SAG2 cohorts are not sealed unseen tests; external MultiHop-RAG selected only 323/400 unambiguously mapped confirmation cases.
7. **Prior-art boundary:** set workspaces (ScalableRAG), evidence-gap scheduling (S2G-RAG), proof/edge verification (GroundRAG), pruning/repair (SPARE-RAG), dense retrieval, BM25 expansion, and chain/link heuristics are established; no independently novel PGER theorem or system demonstrated.

## Verified GitHub action runs and reports

- V9.6B successful run https://github.com/vjgits/Research-Papers/actions/runs/40711525115 ; written negative report https://github.com/vjgits/Research-Papers/blob/v96b-source-witness-chain-assembly-2026-10-28/v7-multihop/V96B_RESULTS_NEGATIVE_FEEDBACK_V97_PLAN.md
- V9.7–V9.9 successful corrected run https://github.com/vjgits/Research-Papers/actions/runs/40712854582 ; report https://github.com/vjgits/Research-Papers/blob/v97-semantic-recovery-and-gated-cost-2026-10-28/v7-multihop/V97_V99_RESULTS_COST_AND_GATES.md
- V10 successful run https://github.com/vjgits/Research-Papers/actions/runs/40712715965 ; corrected report https://github.com/vjgits/Research-Papers/blob/v10-morehop-humanverified-missing-source-2026-10-28/v7-multihop/V10_MOREHOP_EXTERNAL_AND_MISSING_SOURCE_RESULTS.md
- V10.1 successful run https://github.com/vjgits/Research-Papers/actions/runs/40715038235 ; report https://github.com/vjgits/Research-Papers/blob/v101-external-multihoprag-2to4-docs-2026-10-28/v7-multihop/V101_EXTERNAL_MULTIHOPRAG_NEGATIVE_RESULTS.md

**Next strongly indicated stage, not performed:** Create independent *source-identity and typed relationship annotations* for genuine four-distinct-source and higher-depth chains, audit the 77 unmapped MultiHop-RAG confirmation cases, benchmark transparent source-edge verification with human assessment and matched CPU, then explicitly test missing-evidence detection and justified answer abstention. If no verifier improves edge correctness, stop that line rather than layering unverified scheduler heuristics. For six or eight distinct support documents, AE@5 is mathematically impossible; evaluate @10/adaptive K and answer correctness separately. Only claim efficiency/novelty after matched official open baselines and a new sealed evaluation.

**Safeguards:** No paid APIs, automated reviewers, recurring scans, merging, deployment or main-branch writes. Every PGER V7–V10.1 negative result remains part of the scientific record.
