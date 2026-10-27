# V6.1 BEIR development results — 2026-10-27

This experiment evaluated a **precommitted, conservative proof-gap controller**, whose BM25 top two documents remain undisturbed by any follow-up search.

**Run:** https://github.com/vjgits/Research-Papers/actions/runs/40596220675  
**GitHub result artifact:** truth-v61-dev-results (artifact id 12776281527).  
**Commit:** ec71e306ca84aab4ab4c9ee658d2c4ee45c5aaf5.  
**Official datasets:** SciFact, NFCorpus (checksum-verified public BEIR).  
**Data partition:** SHA-256 development split only. **Sealed evaluation untouched.**  
**No paid AI APIs; no dense/LLM models in this run.**

## Results

| Dataset | Dev queries | Method | nDCG@10 | Recall@10 | Recall@100 | MRR@10 | Search calls/query | Retrieval latency ms/query | Second searches | Ranking changes |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SciFact | 148 | BM25 | 0.661489 | 0.785698 | 0.874775 | 0.626008 | 1.000 | 1.556 | 0 | 0 |
| SciFact | 148 | V6 | 0.556315 | 0.756982 | 0.881532 | 0.496225 | 1.791 | 2.869 | 117 | 117 |
| SciFact | 148 | V6.1 | 0.659722 | 0.784009 | 0.874775 | 0.624405 | 1.655 | 2.693 | 97 | 46 |
| NFCorpus | 152 | BM25 | 0.298755 | 0.157757 | 0.253108 | 0.495768 | 1.000 | 1.121 | 0 | 0 |
| NFCorpus | 152 | V6 | 0.285128 | 0.150932 | 0.253097 | 0.465850 | 1.408 | 1.672 | 62 | 62 |
| NFCorpus | 152 | V6.1 | 0.297836 | 0.157500 | 0.253108 | 0.493721 | 1.118 | 1.295 | 18 | 17 |

## Paired nDCG@10 against BM25

| Dataset | Method | Gains | Regressions | Ties | Mean nDCG delta |
|---|---|---:|---:|---:|---:|
| SciFact | V6 | 14 | 48 | 86 | -0.105175 |
| SciFact | V6.1 | 1 | 8 | 139 | -0.001768 |
| NFCorpus | V6 | 12 | 19 | 121 | -0.013627 |
| NFCorpus | V6.1 | 1 | 8 | 143 | -0.000919 |

V6.1 recovered almost all of the V6 decline, but did **not** beat BM25. In particular, 97 extra searches on SciFact produced only one nDCG improvement versus eight regressions. Preserving good initial rankings is necessary, but not sufficient.

## Design and failure analysis

- V6.1 estimates missing-query-term information from the top-ranked document, weighted by term scarcity, and discounts that gap according to first-second rank separation. This is a **heuristic search-value proxy, not a calibrated probability**.
- Before a second retrieval, it requires at least two missing query terms and sufficient estimated value. After retrieving, it promotes a candidate only if the candidate covers missing concepts and meets a first-query relevance gate.
- BM25 top two documents stay fixed; this sharply reduces catastrophic rank churn.
- **Observed weakness:** the proxy often treats lexical term mismatch as proof of missing evidence. It searches 65.5% of SciFact questions without improving relevance. The promotion gate cannot reliably distinguish genuinely useful evidence from merely topically related text.
- Metrics measure **retrieval**, not answer correctness, truth discovery, or source independence. Latency excludes indexing, download and answer generation.

## Planned V6.2 design (not implemented in this run)

1. Model the *counterfactual value* of the second search, not just token mismatch.
2. Include first-pass relevance stability, expected marginal gain, retrieval cost and source novelty as pre-search features. Calibrate with development-only training and separate validation folds.
3. Test method variants as **ablation**: baseline, search gate only, promotion gate only, and full method.
4. Keep net **nDCG improvement at matched search budget** and **Recall@10** as distinct metrics; measure end-to-end latency when generation is added.
5. Use previously untouched official datasets for independent evaluation after the controller is frozen.
6. Preserve our original hypothesis-oriented proof-gap mechanism rather than aggregating existing RAG techniques.

The sealed split is **not ready to be opened** because the development method is still inferior to the baseline and would spend extra search budget without a demonstrated payoff.
