# V7 Multi-hop Retrieval Baseline — Completed 2026-10-27

**GitHub Actions run:** https://github.com/vjgits/Research-Papers/actions/runs/40601976548 (SUCCESS)  
**Download artifact:** truth-v7-multihop-retrieval (artifact 12778514000).  
**Dataset:** 2WikiMultiHopQA validation sample (240 deterministic SHA-256 selected examples), 1,758 pooled question-context passages de-duplicated by title.  
**Question type:** 182 required 2 documents; 58 required 3+ documents. This is **not** full Wikipedia retrieval.

## Complete gold supporting-document chain in Top 5

| Retriever | Chain@5 | Mean supporting document recall@5 |
|---|---:|---:|
| TF-IDF | 25.00% | 61.46% |
| BM25 | 28.75% | 64.90% |
| MiniLM dense | 30.42% | 65.10% |
| BM25 + dense RRF | 32.92% | 67.40% |
| Basic title-link baseline | 52.50% | 79.17% |
| **V7 bounded proof-gap/title-link** | **65.83%** | **86.46%** |

## Stricter 3+ supporting document questions (58)
- BM25: 1/58 complete chain@5 = **1.72%**
- Dense: 0/58 = **0%**
- Hybrid: 2/58 = **3.45%**
- Basic title-link baseline: 8/58 = **13.79%**
- V7 proof-gap/title-link: 9/58 = **15.52%**

At Top 10, BM25 is 40.42%, hybrid 41.67%, title-link 65.00%, V7 73.75%.

### Per-question paired comparisons (binary chain@5)
- V7 vs BM25: **89 wins, 0 losses, 151 ties** (net +37.08 percentage points).
- V7 vs conventional hybrid: **86 wins, 7 losses, 147 ties** (net +32.92 points).
- V7 vs basic title-link: **36 wins, 4 losses, 200 ties** (net +13.33 points).
- The binary 'complete chain' metric is NOT answer accuracy and does NOT measure factual claim validity.

### Cost and speed caveats
- BM25 alone: mean ~1.09 ms/query.
- V7 incremental proof-gap/link procedure: mean ~1.66 ms/query **in addition to BM25**, roughly ~2.75ms/query combined.
- Dense query embedding + dot product: ~8.90ms/query. Dense indexing of all 1,758 docs: 15.62 sec (separate).
- 236/240 questions invoked title-link follow-up; 150 changed rankings. This method is **not selectively frugal** yet.
- The benchmark performs all methods sequentially in one Python process and caches link neighbors across queries and methods. Precise latency comparisons are **confounded by cache order**, so the timing figures are exploratory, not rigorously controlled performance estimates.

## Important scientific boundaries
1. **Data design:** The searchable corpus pools passages provided alongside 240 questions; gold documents are guaranteed by the selection rule to exist in the corpus. This is an artificial pooled-document retrieval evaluation, **not an open-web search**. It may favor link-following approaches because Wikipedia page titles occur explicitly in source paragraphs.
2. **Novelty:** Using title mentions or link traversal is an established retrieval idea. The current V7 rule is not an established novel algorithm or complete "consequences of missing evidence" mechanism.
3. **Competitors:** No official IRCoT or HippoRAG2 implementation ran. Our title-link baseline is not HippoRAG2. Official models require a compatible LLM and heavier indexing/inference; their published numbers are not commensurate with this pooled-corpus result.
4. **Training/test hygiene:** The selection was fixed before execution, and no gold relevance was supplied to the ranker. However, the sampled *validation* dataset is public and is development evidence, not a sealed independent test.
5. **Reader:** We did not generate any final answers. Gains in evidence retrieval may or may not translate into final QA accuracy.
6. **Cost:** No paid API; open-weight MiniLM and scikit-learn CPU-only benchmarking on a public GitHub repository.

## Next check
Without retuning the algorithm, evaluate a **disjoint next 240-question sample**, then a genuinely different dataset (MuSiQue), and compare to strong graph/multi-hop retrievers with matched corpus and budgets. Isolate cache effects in an honest latency study. Do not open the final sealed challenge until the method is frozen.

Source: https://huggingface.co/datasets/framolfese/2WikiMultihopQA
Official dataset: https://github.com/Alab-NII/2wikimultihop
IRCoT: https://github.com/StonyBrookNLP/ircot
HippoRAG2: https://github.com/OSU-NLP-Group/HippoRAG
