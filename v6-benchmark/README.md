# Truth-Seeking V6 / BEIR development only

This is a restricted, **development-partition-only** benchmark runner uploaded to the public research repository on a separate branch. The main branch and citation monitor are untouched.

Run `pip install -r v6-benchmark/requirements.txt`, then `cd v6-benchmark && python -m unittest discover -s tests -v && python benchmark_v6.py smoke`.

To fetch official checksum-verified public BEIR SciFact and NFCorpus and score development queries:
`cd v6-benchmark && python benchmark_v6.py dev --datasets scifact nfcorpus`.

Metrics: nDCG@10, Recall@10, Recall@100, MRR@10, search calls, measured per-query retrieval latency. Comparators: BM25, TF-IDF, and the proof-gap search policy. The relevance judgments are accessed only after a ranking is finalized. The SHA-256 query split is deterministic and dataset-prefixed, using seed `v6-crossdomain-2026-10-27`. The **sealed half cannot be scored by this runner**.

Important: nDCG is not final-answer accuracy; search calls are not necessarily end-to-end cost. Index construction is not part of per-query latency. We do not claim to beat dense state-of-the-art methods with this limited experiment. No paid model API requests are made.

The GitHub Actions workflow runs on push to `v6-beir-development-2026-10-27`, limits execution to 25 minutes, and uploads reports even if a later step fails. A full sealed evaluation must use a separately frozen configuration and be performed only after dev method selection.
