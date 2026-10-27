# V7 Fresh Multi-hop Evidence Retrieval: reproducible first-stage comparison

## Scope and evaluation claim
This is a first-stage **non-LLM retrieval comparison**, **not** an IRCoT or HippoRAG2 reproduction. It compares:
1. BM25 word matching,
2. TF-IDF word matching,
3. open-weight MiniLM dense embedding search,
4. reciprocal-rank fusion BM25+dense (conventional hybrid),
5. a title-link heuristic baseline, and
6. our project-specific bounded proof-gap/title-link intervention.

All six methods rank **the exact same corpus**, and none sees relevance labels before ranking. Gold supporting paragraph titles are used only for scoring complete evidence retrieval. No reviewer agents, no paid APIs, and no answer generation.

## Public data
- Repackaged 2WikiMultiHopQA validation data from https://huggingface.co/datasets/framolfese/2WikiMultihopQA, originally Ho et al., COLING 2020.
- First 240 well-formed records in a deterministic SHA-256 permutation are chosen. We pool only the context passages associated with these questions; deduplicate by normalized page title and preserve the longest passage without consulting gold relevance labels.
- This is NOT full Wikipedia retrieval. It is pooled distractor retrieval. Comparisons to published full-wiki leaderboard scores are invalid.
- This is an exploratory development benchmark, **not** sealed, independently administered final testing. Data split is publicly available.
- A document is credited if its page title is a gold supporting title. We do not evaluate sentence-level citations or answer correctness.
- Report chain@2/3/5/10, supporting document recall@2/5/10, paired wins/losses vs BM25, and retrieval latency. Dense index construction time is separated from query latency.
- The graph-style baseline in our script is a lightweight title-link heuristic. It is **not HippoRAG2**.
- The proofgap method is a bounded title-following and missing-query-term rule. It is **not IRCoT** and is not our complete proposed competing-hypotheses mechanism.

## Next expensive, full-reproduction benchmark
- IRCoT: official code https://github.com/StonyBrookNLP/ircot; multi-step LLM-generated reasoning and retrieval; demands a specified LLM reader and retrieval corpus.
- HippoRAG2: official https://github.com/OSU-NLP-Group/HippoRAG; build index/graph on the identical corpus; report index time and compute cost separately.
- Keep scoring identical before calling any result a head-to-head victory over these systems.

## Research originality
Do NOT claim originality for BM25, hybrid RRF, dense semantic search, or title-linking. The project's hypothesized contribution remains a cost-aware decision based on the consequences of missing evidence for competing claims, with source independence and justified abstention. Current V7 is a baseline study for that future system.

## Cost
GitHub-hosted public repository Actions, CPU inference with public open-weight models. No paid model calls or secrets. Existing reviewer jobs remain stopped and disabled.
