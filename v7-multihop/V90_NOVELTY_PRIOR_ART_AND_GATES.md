# PGER V9.0 — Novelty boundary, open-source choices, and falsification gates

**Research note** — frozen prior to observing the V9.0 natural-document benchmark. This document maps the hypothesis to established work; it does **not** declare PGER novel or more efficient.

## Closest prior art

1. **S2G-RAG (Li et al., ACL 2026)**: explicit evidence sufficiency judgment, structured missing information, query reformulation and compact evidence context. https://aclanthology.org/2026.acl-long.1185/
2. **AdaKG-RAG (Yuan et al., July 2026)**: hypothesis-verification loop, KG expansion, path-aware evidence and matched-budget retrieval comparisons. https://doi.org/10.1007/s44443-026-01028-3
3. **A2RAG (Liu et al., 2026)**: adaptive, evidence-sufficient, provenance-aware graph retrieval and cost/latency reduction. https://arxiv.org/abs/2601.21162
4. **REBEL (Huguet Cabot & Navigli, 2021)**: pretrained relation generator. V8.9 used `Babelscape/rebel-large`; weights CC-BY-NC-SA 4.0, so research-only/commercial license review required. https://huggingface.co/Babelscape/rebel-large
5. **GLiREL (Boylan et al., 2025)**: efficient generalist relation classifier suitable as a comparative model, but model-weight license must be checked separately from the PyPI package. https://aclanthology.org/2025.naacl-long.418/
6. **IRCoT / HippoRAG**: official source-code comparators for retrieval and multihop baseline reproduction, not yet independently reproduced by PGER. https://github.com/StonyBrookNLP/ircot and https://github.com/OSU-NLP-Group/HippoRAG

## Distinctive hypothesis to test (unproven)

Maintain an exact-sourced **claim-to-answer dependency graph**; for each unknown fact, evaluate whether its verified versus refuted outcome would change the feasible/supported answer set, then route the *lowest-cost discriminating retrieval* action. Continue until there is exactly one supported and no alternative feasible answer, otherwise abstain. Rank by **decision effect per measured search cost**, not by co-mention or query keyword score. Prevent verified claims without an exact source span and hash. Simulated counterfactual branches never become evidence.

The individual pieces — set coverage, source provenance, verification, value-of-information, DAG inference, and query gating — are known. The **entire combination may also have prior art**. Only a thorough related-work evaluation, theoretical distinctness and independently reproduced matched-budget wins can support an originality claim.

## Explicit empirical gates

- 1. **Component efficiency:** on previously uninspected 36 public DocRED dev documents, compare identical two-call `first2`, `lexical2`, `coverage2` sentence selectors, along with `coverage3` and `full6`. Hold REBEL revision and evidence grounding rules constant; quantify annotated-positive triple recall versus measured CPU seconds. This is **not** an evaluation of the decision-gap controller.
- 2. **Semantics and citations:** human-adjudicate generated relations (entailment/neutral/contradiction, correct direction and attribution) against source; do not convert unlabelled DocRED outputs into false labels. Independent human checks must be real and cannot be fabricated by an AI review agent.
- 3. **Proof-gap decision utility:** on a genuinely locked 2-, 3-, 4-, 5-8+ hop problem set with manually audited dependencies, compare decision-change-per-cost to cheapest-first, shortest-gap, original-query repeated retrieval, generic evidence sufficiency, S2G and AdaKG. Same *total* BM25/embedding/cross-encoder/generator budget. No gold answer or supporting facts used in online decisions.
- 4. **End-to-end:** chain@5/10, final answer exact match/F1, evidence precision, citation entailment, contradiction/abstention calibration, average/p95 query latency, indexing cost, model load and dollars/tokens. Use sealed independent corpus, not pooled gold support documents.
- 5. **Novelty claim:** only after prior-art sweep and genuine independently reproduced non-inferior outcomes for easy tasks and superior accuracy–cost frontier for hard tasks. If failure, preserve it.

## Immediate decision

Keep `V7.1` fast sparse+indexed graph as simple-title fallback. REBEL is currently a research candidate generator, not an appropriate latency-sensitive default. This V9.0 experiment is a budgeted *candidate generation* study plus a formal, unit-tested scheduler; it does not yet implement complete end-to-end counterfactual evidence retrieval.
