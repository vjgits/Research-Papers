# V6.3 — Independent reviewer study protocol and novelty boundary

**Date:** 2026-10-27. **Experimental phase:** development and ablation, NOT sealed evaluation.

## Research goal
Determine whether (1) a retriever using different representations uncovers documents outside BM25's top 100, and (2) independent reviewers can improve evidence quality *and* measured cost compared with both BM25 and conventional reranking.

**User hypothesis:** independent blind reviewers may expose errors or alternate approaches that a searcher misses. The hypothesis is tested, not presumed true.

## Fixed protocol (written before first V6.3 evaluation)
- Datasets: official BEIR SciFact and NFCorpus, from the same controlled development questions as V6.2, with an internal fit/validate split.
- **Do not score the official sealed partition.** The V6.3 loader filters sealed query IDs before materializing relevance judgments.
- Two independent systems access deliberately distinct information:
  - **Blind reviewer:** frozen `cross-encoder/ms-marco-MiniLM-L-6-v2`, given just (question, candidate passage). It does not see the searcher's ranks, self-explanations, the other critic's output, or gold relevance.
  - **Context reviewer:** deterministic independent checklist of gaps in the first two BM25 passages and whether an additional candidate fills those gaps. It does not see cross-encoder scores or gold relevance.
- **Different retrieval perspective:** frozen `sentence-transformers/all-MiniLM-L6-v2` embedding search on full corpus. This is a challenger source, not an oracle. It may produce documents outside BM25 top 100.
- **Coordinator:** changes only a bounded initial ranking slot when candidate wins context and blind critic thresholds. Rank slots 1–4 are protected. Thresholds fixed in code, not chosen by validation outcomes.
- No reference answers, LLM API, external agent messages or paid model. The reviewers are lightweight modules, **not** two autonomous language-model agents.
- Comparators: BM25, dense, conventional hybrid RRF, BM25 plus blind critic, dense+BM25 union plus blind critic, union plus context critic, and both reviewers coordinated.
- Report nDCG@10, Recall@10/100, MRR@10, paired wins and regressions, new documents outside BM25 top 100, embedding index time and per-query CPU inference time. Document exact model identifiers.
- If the baseline gains come solely from a standard pretrained reranker, attribute the gain to that established reranker. A novel proof-gap method must beat that ablation at matched cost.

## Originality and prior-art boundaries
- **Not novel:** BM25; embedding retrieval; hybrid rank fusion; cross-encoder reranking; independent critics/verification as a general idea; retrieval quality gates.
- These are diagnostic instruments and baselines. Their code and architectures are not claimed as our invention.
- **Potential novel method not yet established:** compute the *consequence* of a missing premise for competing conclusions, select independent evidence to discriminate those conclusions, and accept a revised answer only if a calibrated benefit exceeds search/review cost.
- V6.3's first experiment isolates whether the two reviewer perspectives help retrieval. It does **not** yet implement full competing-hypothesis reasoning, source copying detection or calibrated factual answer verification.

## Relevant prior literature (to cite, not replicate)
- Yan et al. (2024), **Corrective Retrieval Augmented Generation**, https://arxiv.org/abs/2401.15884 (evidence-quality evaluator, corrective routing).
- Thakur et al. (2021), **BEIR**, https://arxiv.org/abs/2104.08663 (cross-domain zero-shot evaluation).
- Sentence Transformers, MS MARCO Cross-Encoders, https://www.sbert.net/docs/cross_encoder/pretrained_models.html (established independent reranker).
- Lewis et al. (2020), **Retrieval-Augmented Generation**, https://arxiv.org/abs/2005.11401 (retrieval-based answer grounding).
- We must complete a more extensive 2025–2026 prior-art sweep and evaluate against current leading methods before any claim of scientific novelty.

## Interpretation safeguards
- nDCG/recall is not truth-finding or final-answer accuracy.
- Scores on these reused development-validation questions are exploratory, not newly sealed or truly blind.
- Pretrained reviewers were trained on external data; their scores may reflect pretraining overlap. No claim of a clean new-model evaluation.
- If a combined reviewer approach performs no better than blind-only reranking, our coordinator adds no verified value and should be simplified or replaced.
- If reviewers improve nDCG but add substantial latency/cost, compare Pareto outcomes rather than claiming better efficiency.
