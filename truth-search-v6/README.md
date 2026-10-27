# Proof-Gap Search — V6 development benchmark

This isolated experimental branch compares keyword BM25, TF-IDF and the proof-gap query policy over official BEIR evidence corpora.

- Stage 1: official SciFact + NFCorpus **development-only** (stable 50/50 split of BEIR test queries).
- All labels are used only by evaluation, never supplied to the retrieval methods.
- The workflow **does not** run sealed evaluation, cannot change the published papers on `main`, and performs no paid API calls.
- Metrics: nDCG@10, recall@10, mean number of retrieval calls, query latency. Index-building time recorded separately.
- The branch workflow uses only a bounded push-trigger on this branch and a manual trigger.
- Artifacts are uploaded as JSON/JSONL and don't include the full benchmark corpora.
- This is a relevance-retrieval test, **not** fact-checking accuracy or a state-of-the-art claim.

The standalone runner is `truth-search-v6/benchmark_v6.py`.

To run locally:
```bash
pip install -r truth-search-v6/requirements.txt
python truth-search-v6/benchmark_v6.py --datasets scifact nfcorpus --methods bm25 tfidf proofgap --partition dev --output results-v6
```
Official source: https://github.com/beir-cellar/beir
