# PGER V9.7–V9.9: semantic candidate discovery, no-cost routing and retrieval completeness confidence

**UTC 2026-10-28. Successful fixed run:** https://github.com/vjgits/Research-Papers/actions/runs/40712854582 . **Full archive:** https://github.com/vjgits/Research-Papers/actions/runs/40712854582/artifacts/12827194530 . Frozen code: benchmark_v97_v99.py on branch v97-semantic-recovery-and-gated-cost-2026-10-28. Previous run 40712378261 was **cancelled** before scoring acceptance because an initial routing feature depended on dense model outputs and invalidated 'cheap-first' measurement; the corrected run uses only BM25/V7.1 signal features.

## V9.7: Frozen, MIT-licensed BGE-small-en-v1.5 CPU semantic retrieval

120 development and 120 distinct public confirmation questions each for official SAG2 2Wiki and MuSiQue source corpora. All public questions have been examined in earlier V7.1 experiments, so NOT independently sealed generalization. Full source corpora, no gold online, no paid APIs. Dense retrieval alone, rank-fused with unchanged V7.1, original V7.1 and two-query sparse control, all evaluated on matching questions. Embedding means known established prior art, NOT PGER original algorithm or actual verified evidence chain.

**Confirmation (120 each):**

| Method | 2Wiki complete chain@5 | MuSiQue complete chain@5 | MuSiQue complete source candidate pool |
|---|---:|---:|---:|
| V7.1 fast | 66.67% | 22.50% | 65/120 |
| Two-search BM25 expansion | 58.33% | 19.17% | 78/120 |
| Dense BGE direct | 40.00% | 17.50% | 67/120 |
| V7.1 + dense rank fusion | 51.67% | 23.33% | 90/120 |

MuSiQue candidate pool completeness improved by **25/120 cases vs V7.1**, but chain@5 gain was **+0.83 pp**, 95% paired bootstrap CI **[-5,+7.50]**, 8 wins/7 losses. 2Wiki dense fusion regressed **-15.00 pp vs V7.1**, CI [-22.50,-8.33]. **Novel success claim rejected**. On four-source MuSiQue confirmation cases n=17: complete pool rose from **3/17** V7.1 to **6/17** dense-fusion; complete chain@5 stayed **0/17**. This cleanly demonstrates candidate recall is distinct from evidence-chain selection.

**Compute and reproducibility costs:** BGE 384 dimensions, model card declares MIT; model revision recorded as null/unresolved, so source weights must be explicitly pinned before independent reproduction. 2Wiki offline dense corpus embedding **376,581 process CPU ms** plus model-loading 702ms, 9.4 MB vector index. MuSiQue offline corpus embedding **914,651 CPU ms** plus loading 129ms, 17.9 MB vector index. Batch-amortized question encoding + scoring **17.00ms** (2Wiki) / **20.91ms** (MuSiQue), NOT interactive p95 latency; compare V7.1 earlier ~1-2ms post-index only. BGE costs do not yield best-in-class efficiency and violate any zero-ingestion claim.

## V9.8: cheap-first development gate correctly DISABLED semantic retrieval

Gold-independent cheap features computed only from initial BM25/V7.1 outputs. On pooled 240 development questions, always-on dense fusion had **7 wins and 25 losses** against V7.1. Predeclared gate requires wins>losses plus at least two positive examples, therefore **no expensive routing was enabled**. On 240 confirmation questions, same V7.1 output: chain@5 44.58%; always-dense-fused counterfactual chain@5 37.50%. Routed count 0; **no accuracy improvement** and no demonstrated production wall-time savings. The safety gate is a negative-result protective fallback, NOT a novel self-correction policy.

## V9.9: retrieval-chain completeness (NOT answer truth) proxy

Regularized logistic classifier trained on 240 development cases using only cheap observable features, evaluated on separate 240 public confirmation cases. Target was **all annotated supporting documents in retrieval Top 5**, not correct factual answer, relation entailment or valid abstention. Brier **0.195752** versus constant development rate baseline **0.248177**; ROC AUC **0.779144**, five-bin calibration error **0.095218**. Selecting the top-confidence 40% gave **67/96 = 69.79%** complete-support retrieval, against full-set **107/240 = 44.58%**. Selective success on 60%/80%/100% coverage: 63.89% / 53.65% / 44.58%. Observational signals likely include dataset-specific text patterns even without explicit dataset identity; hold-out by corpus is required before general reliability claim.

## Decision and feedback

Retain V7.1 as fast default; do NOT promote dense fusion globally. Semantic source recovery in hard MuSiQue is a useful component but is extremely CPU-expensive and needs a better source-dependency-aware chain assembly algorithm to realize candidate gains. Neither exact title links nor generic semantic similarity verify relationships. No claimed improvement over official SAG2 author-reported 92.9%/59%/97% AE@5 (different cohorts/hardware), ScalableRAG, S2G-RAG, AdaKG-RAG, GroundRAG or SPARE-RAG. No demonstrated 4+ source chain general success, real abstention, open-world sourcing or independent answer correctness.

V10 already established that MoreHopQA released 1,118 human-verified cases each require only TWO gold support titles, regardless of extra reasoning. Therefore v10.1 external 2–4 document evaluation is the necessary correction. Future work must prioritize a genuinely human-audited logical 4/5/6/8+ hop corpus with source spans, calibrated truth and end-to-end matched CPU/wall budgets, not incremental keyword threshold tweaking. All previous negatives retained, main untouched and no paid APIs.
