# V6 BEIR development run — 2026-10-27

**Run:** https://github.com/vjgits/Research-Papers/actions/runs/40594176112  
**Status:** GitHub Actions success. Official checksum-verified SciFact and NFCorpus downloads completed.  
**Partition:** SHA-256 deterministic development half ONLY. Sealed evaluation NOT opened.  
**No paid AI APIs used.**

## Metrics

| Dataset | Queries | Corpus documents | Method | nDCG@10 | Recall@10 | Recall@100 | MRR@10 | Search calls per question | Retrieval latency ms / question |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| SciFact | 148 | 5183 | BM25 | 0.661489 | 0.785698 | 0.874775 | 0.626008 | 1.000 | 1.514 |
| SciFact | 148 | 5183 | TF-IDF | 0.645515 | 0.783784 | 0.895045 | 0.607853 | 1.000 | 4.886 |
| SciFact | 148 | 5183 | Proof-Gap | 0.556315 | 0.756982 | 0.881532 | 0.496225 | 1.791 | 2.800 |
| NFCorpus | 152 | 3633 | BM25 | 0.298755 | 0.157757 | 0.253108 | 0.495768 | 1.000 | 1.085 |
| NFCorpus | 152 | 3633 | TF-IDF | 0.281773 | 0.147254 | 0.251683 | 0.475457 | 1.000 | 3.411 |
| NFCorpus | 152 | 3633 | Proof-Gap | 0.285128 | 0.150932 | 0.253097 | 0.465850 | 1.408 | 1.645 |

## Paired error diagnostic vs BM25

| Dataset | Proof-gap gains | Proof-gap regressions | Equal | Triggered second search |
|---|---:|---:|---:|---:|
| SciFact | 14 | 48 | 86 | 117 of 148 |
| NFCorpus | 12 | 19 | 121 | 62 of 152 |

**Finding:** Current proof-gap's lexical concept-coverage trigger is too eager on SciFact, and the RRF second-stage fusion can reorder initially relevant documents downward. This is a failure of the current prototype, not a demonstration that proof-gap reasoning as a research idea cannot work.

## Next experiment

1. Preserve the dev baseline above unchanged.
2. Add a search-action gate that estimates *expected* improvement over the existing ranking, including explicit search cost.
3. Evaluate counterfactual candidates without overwriting the original ranking; retain original top documents if improvement is unverified.
4. Check entity preservation, uncertainty and contradiction handling independently.
5. Compare again on development data, then freeze settings and open the final partition once. Also test against stronger open-weight dense baselines.
6. Add a frozen common answer-generation model before making answer-accuracy claims.

These figures are from a restricted **three-method** cloud deployment of the V6 prototype, not a full reproduction of top research systems. Per-query latency excludes building the index and downloading files; it is not end-to-end user latency.
