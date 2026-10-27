# V6.2 — Counterfactual Proof-Gap Search (development-validation)
**Run:** https://github.com/vjgits/Research-Papers/actions/runs/40597483043  
**Result artifact:** `truth-v62-dev-results`; artifact ID `12775894666`  
**Branch:** `v6-2-proofgap-2026-10-27` (separate from main)  
**Dates:** October 27, 2026. No paid API calls.

## Simple outcome
The new decision-maker reduced wasteful searching compared with V6.1, but **did not improve search accuracy beyond basic BM25**. It also increased measured latency because the new predictions and features require processing. We did **not beat state-of-the-art RAG systems**.

- Dev-fit training: 171 query IDs (78 SciFact, 93 NFCorpus). Of these, 151 have enough retrieved candidates to construct the gate's training examples; 20 were omitted from gate training.
- Dev-validation (not used to fit): 129 questions (SciFact 70, NFCorpus 59).
- Original BEIR sealed partition: **never evaluated**, and no relevance labels from that partition were used for model fitting. The original `load()` helper reads the qrels TSV into memory, so our earlier shorthand 'never read' should not be interpreted as a physical access control; the scoring and training code only selects development IDs. This distinction must be fixed in a later stricter harness.

## Paired comparisons (same 129 dev-validation questions)

| Dataset | Questions | Method | nDCG@10 | R@10 | R@100 | Calls/q | Measured retrieval milliseconds/q | Extra searches | Rank changes |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| SciFact | 70 | BM25 | 0.634227 | 0.771905 | 0.878095 | 1.000 | 1.695 | 0 | 0 |
| SciFact | 70 | V6.1 | 0.635076 | 0.771905 | 0.878095 | 1.629 | 2.890 | 44 | 24 |
| SciFact | 70 | V6.2 | 0.634227 | 0.771905 | 0.878095 | 1.300 | 3.006 | 21 | 10 |
| NFCorpus | 59 | BM25 | 0.288448 | 0.136788 | 0.237662 | 1.000 | 1.134 | 0 | 0 |
| NFCorpus | 59 | V6.1 | 0.289046 | 0.137066 | 0.237662 | 1.119 | 1.305 | 7 | 6 |
| NFCorpus | 59 | V6.2 | 0.288448 | 0.136788 | 0.237662 | 1.169 | 1.714 | 10 | 2 |

**Pooled across the 129 questions:** BM25 nDCG@10 = 0.476080, V6.1 = 0.476814, V6.2 = 0.476080. Search calls/q: 1.000, 1.395, and 1.240 respectively. Latency ms/q: 1.438, 2.165, 2.415 respectively. This pooled value weights the two domain samples by query count; it is not a macro average across domains and is *not* the standard BEIR leaderboard metric.

- V6.2 made **31 additional searches** on 129 queries, versus V6.1's **51**, a 39.2% reduction in second searches.
- V6.2 made 12 rank changes, all with zero observed impact on nDCG@10 or recall; no paired wins or losses against BM25.
- V6.1 had two tiny improvements but five regressions in this inner-heldout partition; the positive net nDCG is too small to regard as reliable.
- V6.2's measured per-query latency was approximately **68% greater than BM25** because of the features, model decision, and optional second search.
- No end-to-end LLM answering, source credibility, citation correctness, or final-answer truth test has been run.

## What we implemented, and how it differs from V6.1
1. Given the top-ranked evidence, make an explicit list of query concepts not covered by the first two sources.
2. Generate a targeted follow-up that retains a distinctive original-query anchor and asks for the highest-information unresolved concepts.
3. Enumerate actual counterfactual ranking actions that would promote a document to a limited slot while retaining the original top-1 hit.
4. On *development-fit* queries only, evaluate whether each hypothetical action would have improved rank quality. Fit a pre-search gate and a predicted rank-change value model.
5. At evaluation time, search only if a predicted opportunity passes a precommitted threshold; reject rank changes predicted not to pay for their extra cost.
6. Always preserve the original BM25 ranking when the evidence for intervention is weak.

The training-set evidence shows just 18 positive gate examples among 151 eligible questions (11.9%). Only 59/2,172 contemplated ranking actions improved training nDCG (>0), or 2.7%. The model had sparse positive signal, making reliable selection difficult.

## Why we did not win
The core methodological gap is **information not supplied by keyword overlap**. The follow-up mainly reshuffles documents already favored by BM25. In particular, the candidate acceptance rule demands nonzero original-query BM25 score, and so it effectively rejects genuinely new documents absent from the original shortlist. That protects rankings, but also removes the opportunity for a substantial novel-evidence discovery.

The method is also too slow for the quality it delivers: computing and scoring candidate actions outweighs the small reduction in second searches. A system that merely avoids changing the ranking cannot beat BM25 unless it also avoids additional costs.

## Originality and prior-art disclosure
The V6.2 code was developed in this project as a *response to our observed V6/V6.1 failures*, not copied from a third-party implementation or trained on other papers' source code. **This does not establish scientific novelty.** Generic adaptive retrieval gates, query rewrite policies, multi-hop planning and retrieval evaluators predate this project. Relevant closest work includes:
- CRAG (Yan et al., 2024), https://arxiv.org/abs/2401.15884 — lightweight retrieval-quality evaluator and corrective action.
- Q-PRM (Ye et al., EMNLP 2025), https://aclanthology.org/2025.findings-emnlp.817/ — adaptive query rewriting with stepwise supervision.
- Query Decomposition for RAG: Balancing Exploration–Exploitation (Petcu et al., EACL 2026), https://aclanthology.org/2026.eacl-long.322/ — selecting informative subqueries under budgets.
- INKER (Zhou et al., 2026), https://doi.org/10.1016/j.ipm.2025.104534 — deciding when and what to retrieve.
- CA-RAG (2026), https://www.mdpi.com/2673-2688/7/7/250 — cost-aware retrieval routing.

A *potential* contribution remains the specific **consequence-of-missing-evidence** value function spanning competing conclusions, independent-source provenance, and calibrated abstention, as initially proposed by this project. The current prototype **does not implement that full function**, so it cannot claim originality from it yet.

## Next experiment: failure-guided, not technique accumulation
1. Build *evidence-need* labels from question subgoals and judge actual missing conclusions, not missing words.
2. Allow a bounded independent second source not present in BM25 top-100, while still requiring primary-claim relevance.
3. Train/measure action-value with a cost penalty and a no-op fallback; use query-feature caching to lower overhead.
4. Develop and lock a distinct evaluation dataset (e.g., FiQA, ArguAna) and compare against a stronger dense retriever.
5. Run a fixed generator on both retrieval methods before claiming answer-quality superiority.
6. Before a sealed test, audit the harness to ensure withheld qrels are not even materialized.

**Conclusion:** V6.2 improves *caution*, not *retrieval accuracy*. It is a research checkpoint, not a best-model achievement.
