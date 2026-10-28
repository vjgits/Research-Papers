# V7.1 Context Retention and Latency Audit — October 27, 2026

## Executive verdict

**User hypothesis:** The decline in 3- and 4-hop retrieval may result from context being lost between passes. A compact ledger could retain previous evidence accurately and cheaply.

**Finding:** A minimal memory ledger containing previous document IDs and covered query-term identifiers **did not increase complete-chain recovery** compared with an identically budgeted reset-memory method, on either previously used development dataset. No evidence of a retrieval benefit from *this ledger design* was observed. This does not rule out more informative memory (facts, relations, source dependency, alternative hypotheses) or a different retrieval controller.

**Engineering improvement:** An indexed Aho–Corasick title-reference graph, source-path selection, and elimination of avoidable Python overhead produced an effective **BM25-only fast graph variant**. On 2Wiki, Top-5 complete-chain recall improved from **38.33% BM25** to **77.50% BM25+graph**, while query-path time was approximately 1.24 ms. Dense-seeded graph scored 78.75% but consumed much more query time (~16.6 ms).

This is **not** a new proven scientific algorithm, does **not** run official IRCoT/HippoRAG2, and scores evidence retrieval rather than generated answers.

## Protocol
- 2WikiMultiHopQA second sampled 240-question validation subset (1,788 title-deduplicated pooled source passages, reused from V7). 194 questions require 2 gold supporting pages, 46 require 4.
- MuSiQue 160 sampled validation questions (2,621 supporting/distractor paragraphs; 74 require 2, 53 require 3, 33 require 4).
- BM25 / MiniLM dense / hybrid / old V7 / new indexed graph 1-hop / indexed graph 4-hop resetting coverage memory / indexed graph 4-hop retaining the union of covered query terms.
- Every source-scoring method uses only documents and questions, never the gold relevance labels. The tests are **development diagnostics on previously inspected samples**, not new sealed evaluations.
- Same C-based Aho–Corasick graph, source budget, beam width 8, fanout 8, max depth 4, and output Top-5 across memory vs reset arms. The algorithms' actual expansions may differ when the retained state changes scores.
- The graph build contains 469 edges over 1,788 2Wiki sources and 3,004 edges over 2,621 MuSiQue sources. The build was approximately **26.5 ms and 45.9 ms**, respectively, on the GitHub CPU runner, excluding BM25 and dense index construction.
- This is an explicit sparse *term and document ID* ledger, **not** natural-language reasoning memory or complete semantic fact preservation.

## Complete supporting-document-chain recovery at Top 5

| Method | 2Wiki 240 | MuSiQue 160 |
|---|---:|---:|
| BM25 | 38.33% | 10.00% |
| MiniLM dense | 39.17% | 21.25% |
| BM25+MiniLM hybrid | 43.75% | 16.88% |
| Original V7 one-follow-up | 71.67% | 21.88% |
| **Indexed 1-hop seeded by BM25 (no dense query)** | **77.50%** | **19.38%** |
| Indexed 1-hop seeded by hybrid | 78.75% | 21.25% |
| 4-hop reset seeded by hybrid | 78.33% | 21.88% |
| 4-hop retained ledger seeded by hybrid | 78.33% | 21.88% |
| 4-hop ledger seeded by BM25 | 77.50% | 18.75% |

Memory vs reset had **0 paired wins and 0 losses** on binary complete-chain Top-5 for all 400 queries. The actual order of every retrieved document was not logged, so this does not prove that all ranking changes were identical; two MuSiQue items differed slightly in partial recall in the first execution. It does show zero answer-chain recovery improvement.

### Hard evidence chains, separately

| Dataset | Gold support count | Questions | BM25 | BM25+indexed 1-hop | Hybrid+indexed 1-hop | Hybrid+4-hop ledger |
|---|---:|---:|---:|---:|---:|---:|
| 2Wiki | 4 | 46 | 0/46 | 23/46 | 25/46 | 25/46 |
| MuSiQue | 3 | 53 | 3/53 | 3/53 | 2/53 | 4/53 |
| MuSiQue | 4 | 33 | 0/33 | 1/33 | 0/33 | 0/33 |

2Wiki improvements are within a *closed pooled-document universe*. This does NOT imply the system can reason through four facts, only that it puts all four annotated source documents in Top 5.

### Graph reachability
- 2Wiki four-hop retained controller actual depth: 49 questions no traversals, 147 depth 1, 41 depth 2, 2 depth 3, 1 depth 4. Most 2Wiki queries cannot exploit deeper graph walks from the chosen seeds.
- MuSiQue four-hop controller: 34 zero traversals, 30 depth 1, 19 depth 2, 15 depth 3, 62 depth 4. Even when deeper graph paths exist, source selection fails to recover the complete 4-paragraph chain. The bottleneck is not merely the memory reset.

## Latency improvement: same accuracy, less Python work
Three successive GitHub CPU executions under identical source-scoring logic (except the last one also adds BM25-only comparator outputs):

| Operation | Initial | Cache query vocabulary + BM25 | Constant-time de-duplication and Top-100 stop |
|---|---:|---:|---:|
| 2Wiki 4-hop ledger extra traversal ms/query | 20.519 | 13.960 | 0.176 |
| MuSiQue 4-hop ledger extra traversal ms/query | 39.941 | 30.247 | 0.415 |

Last additional BM25-only graph retrieval on **2Wiki**:
- BM25 query mean: **1.076 ms**
- BM25-seeded indexed one-hop graph addition: **0.167 ms**
- Approximate method path: **1.243 ms/query**, **77.50% chain@5**
- Dense query mean in the same shared-process run: **15.267 ms**
- Hybrid-seeded one-hop graph addition: **0.220 ms**
- Approximate hybrid method path includes BM25, dense, hybrid-rank fusion, graph: **at least 16.56 ms/query**, **78.75% chain@5**

On **MuSiQue**, BM25 mean **1.543 ms**, BM25 graph additional **0.203 ms**, approximate path **1.746 ms/query**, chain@5 **19.38%**. The dense query alone averaged **14.141 ms**, making the small quality gain from hybrid+dense comparatively expensive on this CPU setup.

**Caution:** These are CPU timings from the same combined program, not isolated repeatable serving measurements. Indexing, model download, network transfer, dataset load, Python process startup and answer generation are excluded. The graph is built offline; these values are per-query post-index latency. Shared caches, warm-up and sequential run order affect results. Do not market these numbers as end-to-end latency or absolute SOTA efficiency.

## Observed failure mode
The 2Wiki gain is largely from extracting explicit in-passage mentions of other known page titles and inserting linked source documents from a compact index. This is well-established graph/hyperlink-style retrieval. Replacing dense retrieval with indexed graph helps when textual links are abundant and reliably surface all supporting pages. For MuSiQue, supporting paragraphs are not consistently joined by explicit exact title references; moving deeper along available links frequently explores unrelated material.

Our retained ledger stores lexical query-term coverage, **not a representation of missing subclaims, named entities, relation triples, contradictory evidence, or the truth effect of each source**. Thus the memory ablation is a valid test of *this memory choice*, not a refutation of the user's broader context-retention hypothesis.

## Originality guardrails
- **Existing external methods used:** BM25, sentence-transformers MiniLM embeddings, reciprocal rank fusion, C-based Aho–Corasick string matching (`pyahocorasick`), bounded beam traversal, and title-reference graph linking.
- **Project-specific modifications:** heuristic page-mention candidate selection, compact query-term coverage ledger and reset ablation, conservative top-ranking protection and performance fixes; these do not constitute proven novelty.
- Official IRCoT (https://aclanthology.org/2023.acl-long.557/) interleaves LLM reasoning with retrieval. Official HippoRAG2 (https://github.com/OSU-NLP-Group/HippoRAG) uses richer graph and memory. Neither was reproduced in our tests.
- Source for the fast multi-pattern matching primitive: https://pypi.org/project/pyahocorasick/.

## Next technical priorities
1. **Do not spend more on lexical memory by itself**; it produced no benefit and more hops did not help 2Wiki.
2. Diagnose missing evidence paths. For every failed 3/4-support question, distinguish (a) an unindexed link between passages, (b) no shared entity or explicit title, (c) correct passage outside candidate set, (d) selection/ranking error.
3. Build *semantic subclaim* memory that stores: missing relation, sourced entity values, dependencies and alternative explanations. Do not just add an LLM agent; test the memory as an isolated ablation first.
4. Measure **easy, 2-hop, 3-hop and 4-hop** performance, answer correctness, evidence fidelity and cost under common model/compute conditions.
5. Freeze the approach then test fresh MuSiQue/2Wiki and authentic IRCoT/HippoRAG2 implementations, with per-query operation counts and index costs.

## Reproducibility
- Branch: `v71-context-ledger-2026-10-27`
- Script: `v7-multihop/benchmark_v71.py`
- Original run: https://github.com/vjgits/Research-Papers/actions/runs/40604440034
- Cached vocabulary optimization: https://github.com/vjgits/Research-Papers/actions/runs/40605055436
- List deduplication/early-stop optimization: https://github.com/vjgits/Research-Papers/actions/runs/40605585731
- Final BM25-only ablation: https://github.com/vjgits/Research-Papers/actions/runs/40606116376
- Final artifact `truth-v71-memory-ablation`, ID `12779849853`.
