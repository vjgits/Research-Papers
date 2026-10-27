# V7: Real Multi-hop Evidence Retrieval Comparison — 27 October 2026

## Executive result
A manually developed, bounded proof-gap/title-link policy produced a **large and repeatable improvement** over BM25 and simple title-following on two samples of 2WikiMultiHopQA; the improvement **did not fully generalize** to a different multi-hop dataset (MuSiQue), where it was effectively tied with a standard dense retriever and failed completely on 4-hop questions.

**Do not claim victory over IRCoT or HippoRAG2. Neither official system was run.**
**Do not equate evidence retrieval with final-answer correctness.**

## 2WikiMultiHopQA: two disjoint samples, 480 questions
Gold unit: all supporting Wikipedia **page titles** must be in the first five retrieved documents. Same retrieval corpus for each method within each 240-question sample (1,758 and 1,788 title-deduplicated passages).

| Method | Sample 1 (240) | Sample 2 (240) | Both (480) |
|---|---:|---:|---:|
| BM25 | 28.75% | 38.33% | 33.54% (161/480) |
| MiniLM dense | 30.42% | 39.17% | 34.79% (167/480) |
| BM25 + dense hybrid | 32.92% | 43.75% | 38.33% (184/480) |
| Basic title-link | 52.50% | 64.58% | 58.54% (281/480) |
| **V7 proof-gap/title-link** | **65.83%** | **71.67%** | **68.75% (330/480)** |

Paired Top-5 complete chain score:
- V7 vs BM25: 170 wins, 1 loss, 309 ties (+35.21 percentage points).
- V7 vs hybrid: 162 wins, 16 losses, 302 ties (+30.42 pp).
- V7 vs simple title link: 59 wins, 10 losses, 411 ties (+10.21 pp).

**Hard 3+-page subset (104 questions):** BM25 1/104, hybrid 2/104, basic title-link 12/104, V7 13/104. Hence the stronger advantage mainly concerns two-page chains, not the hardest category.

**Cost caveats:** BM25 mean ~0.97ms/query; the V7 link step added ~1.49ms (total ~2.46ms nominal per query). Link-following was invoked in 470/480 questions; this is NOT yet a cost-efficient selective method. Graph neighbor caches are shared between sequential methods; detailed speed ratios are confounded by execution order and should be independently rebenchmarked. Dense index time (15.6-22.5 sec per sample) is separate.

## MuSiQue: 160 questions, 2,621 pooled documents
Gold unit: individually supporting **paragraphs**, identified by SHA-256 of title + paragraph text. Dataset: `awinml/musique` validation, deterministic unseen-for-project sample. V7 method's retrieval code remained unchanged.

| Method | Chain@5 | Chain@10 | Supporting paragraph Recall@5 |
|---|---:|---:|---:|
| BM25 | 10.00% | 18.12% | 46.88% |
| Dense MiniLM | 21.25% | 33.75% | 55.05% |
| Hybrid | 16.88% | 26.25% | 54.06% |
| Basic title-link | 16.88% | 26.88% | 48.02% |
| **V7 proof-gap/title-link** | **21.88%** | **28.12%** | **52.66%** |

V7 vs BM25: 20 paired wins, 1 loss, 139 ties (+11.88 pp).
V7 vs dense: 20 wins, 19 losses (+0.625 pp, one extra success): **no meaningful advantage established**.
V7 vs basic title-link: 12 wins, 4 losses (+5 pp).

By hop count:
- 2-hop (74 questions): V7 32/74 (43.24%), dense 25/74 (33.78%), BM25 13/74 (17.57%).
- 3-hop (53): V7 3/53 (5.66%), dense 9/53 (16.98%), BM25 3/53 (5.66%).
- 4-hop (33): V7 0/33, dense 0/33, BM25 0/33.
Thus the current method fails to provide the necessary multi-step chaining for difficult 3- and 4-hop problems. This is the research direction to improve.

MuSiQue nominal CPU query timing: BM25 ~1.58 ms; V7 adds ~2.76 ms; dense ~14.51 ms, index embedding ~55.31s; caching and sequential execution confound precise comparisons.

## Method and originality audit
- Our bounded V7 algorithm: use an initial BM25 shortlist, examine document-title references in the initial passages, select one new candidate using source-link strength and lexical relevance, and insert it conservatively into the ranked set.
- **Not new in general:** BM25, semantic retrieval, RRF hybrid search, graph or hyperlink traversal, and multiple retrieval passes.
- The custom scoring rule was written for this project rather than copied verbatim from another paper; **scientific novelty is not established**.
- The complete envisioned project—competing hypotheses, dependent-source provenance, calibrated proof-gap value, final-answer correctness and justified abstention—has NOT been implemented by this test.
- In these pooled corpora each sampled question's gold evidence was originally included among its source passages. That creates a closed-world retrieval problem, not a test of searching truly unavailable information.
- These are public validation examples and repeated development evaluations, not independently sealed challenge sets. There was no answer generator or factual correctness grader.

## Reproducing results
- 2Wiki sample 1 https://github.com/vjgits/Research-Papers/actions/runs/40601976548
- 2Wiki sample 2 https://github.com/vjgits/Research-Papers/actions/runs/40602553021
- MuSiQue https://github.com/vjgits/Research-Papers/actions/runs/40603116225
- Baseline implementation: `v7-multihop/benchmark_v7.py`
- Cross-dataset MuSiQue wrapper: `v7-multihop/benchmark_musique.py`
- Official IRCoT https://github.com/StonyBrookNLP/ircot (requires LLM reasoning setup)
- Official HippoRAG https://github.com/OSU-NLP-Group/HippoRAG (requires graph indexing and LLM setup)
- 2Wiki repackaging https://huggingface.co/datasets/framolfese/2WikiMultihopQA
- MuSiQue repackaging https://huggingface.co/datasets/awinml/musique

## Next research task
**V7.1 — true multi-source proof-gap planner.** Choose a specific missing relationship or subquestion after each retrieved passage, traverse two or more independent evidence transitions, verify whether the gathered chain can justify the conclusion, and stop when additional retrieval is not worth its cost. Train or select only on development data, then evaluate on an untouched set. Benchmark latency with isolated caches and index amortization. Compare with an authentic IRCoT and HippoRAG2 reproduction once common model/inference and indexing costs are available. Do not reuse the present title-link score as evidence of SOTA parity.
