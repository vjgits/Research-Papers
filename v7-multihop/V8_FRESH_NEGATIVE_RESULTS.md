# PGER V7.3-V8.2: Fresh-cohort results - FAILS TO BEAT FAST V7.1

Date: 2026-10-27 PT / 2026-10-28 UTC. Branch: `v8-adaptive-proofgap-2026-10-27`.
Run: https://github.com/vjgits/Research-Papers/actions/runs/40616913946
Artifact: https://github.com/vjgits/Research-Papers/actions/runs/40616913946/artifacts/12786125478

## Protocol

Question-disjoint 2Wiki validation positions 721–960 (n=240; pooled documents=1,806) and MuSiQue validation positions 321–480 (n=160; pooled paragraphs=2,643). Same public validation sources used across previous project versions; no sealed evaluation, no correct generated answer scoring. Zero paid APIs. All variants scored on the same question subsets. V7.3 lexical and rescue both perform two extra BM25 searches; V8.0 joint and V8.1 proofgap use the **same** rescue candidate pool. Per-query costs and offline index times are separate.

## Complete supporting-document chain retrieval

| Method | 2Wiki @5 | 2Wiki @10 | MuSiQue @5 | MuSiQue @10 |
|---|---:|---:|---:|---:|
| BM25 | 37.50% | 47.50% | 13.75% | 20.63% |
| **Unmodified V7.1 fast BM25+title graph** | **73.33%** | **83.75%** | **21.88%** | **36.25%** |
| V7.3 lexical control | 40.00% | 53.33% | 13.13% | 22.50% |
| V7.3 semantic candidate rescue | 40.42% | 53.75% | 13.13% | 22.50% |
| V8.0 joint chain selection | 65.83% | 82.50% | 18.75% | 28.75% |
| V8.1 proofgap scorer | 72.92% | 82.92% | 20.00% | 27.50% |
| V8.2 adaptive gate | 72.92% | 82.92% | 20.00% | 27.50% |

## What worked

- Gold evidence candidate coverage increased from **95.42% to 98.75%** on 2Wiki (+3.33 pp, paired bootstrap 95% CI [+1.98,+4.90]) and **88.28% to 91.35%** on MuSiQue (+3.07 pp, CI [+0.68,+5.47]). This is an **oracle-candidate recall diagnostic**, not complete-chain@5.
- Relative to the *weak* rescue scorer, joint chain selection improves Top5 retrieval, and source-gap scoring improves 2Wiki joint scorer by +7.08 pp (CI [+3.75,+10.83]). Neither beats the established strong fast graph, so these are not product wins.
- Offline source-dependency traversal and provenance invariants passed 6 tests, including representing eight linked transitions without cycles. This is synthetic mechanical proof of implementation, **not** an evaluation of natural-language >4-hop correctness.

## What failed

- V8.1 versus fast baseline at Top5: **2Wiki -0.42 pp** (bootstrap 95% [-5.42,+4.17], 15 paired wins /16 losses); **MuSiQue -1.88 pp** ([-6.25,+2.50], 5/8). MuSiQue Top10 regressed by **8.75 pp** ([-14.38,-3.13]).
- MuSiQue four-source @5: fast baseline **1/28**, V8.1 **0/28**; @10 fast **5/28**, V8.1 **3/28**. No general long-hop solution.
- V8.2's gate took cheap fast path in only 7/240 2Wiki and **0/160 MuSiQue** questions. Unacceptable reduction in work.
- Mean post-index query CPU path (ms): 2Wiki fast **0.64**, V8.1 **7.67**; MuSiQue fast **0.83**, V8.1 **9.41**; ~12x/11x slower. Shared-process measurements exclude serving, startup, downloads and answer generation.

## Diagnosis

Strong source-aware BM25+graph ranking is lost when V7.3 source candidates are naively re-ranked using simple term-score features; broad candidate pools alone are insufficient. Introducing more search queries and a nearly always-on controller substantially increases cost without beating fast retrieval. An appropriate next experiment is **selective high-precision promotion** of evidence only when both relation and question entity anchors are source-observed, leaving the V7.1 ranking intact for other queries. A new question-disjoint validation cohort is required to test this additional design. No claims of algorithm originality, official IRCoT/HippoRAG2 parity, full-web search, or answer accuracy.