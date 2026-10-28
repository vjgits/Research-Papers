# PGER V12: source-code review of three strong multi-hop architectures and matched three-proxy experiment

**Date:** 2026-10-28. **Scope:** Review real official code, implement three *distinct architectural inspiration probes* on a fixed PGER selection budget, NOT import, reimplement or directly benchmark the full original three systems. Preserve PGER proof-gap concept, source identity/provenance and zero-gold test-time behavior.

## I. Industry/state-of-the-art research review — exact code paths

### 1) SAG2 — Embedding-Free Multi-Hop Retrieval with BM25 and JEV, arXiv 2610.22588 (Oct 2026)
**Official code:** https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py ; published architecture/code MIT: https://github.com/Zleap-AI/SAG-Benchmark

- Offline: original source passages indexed via **SQLite FTS5/BM25**, with no embeddings or LLM extraction, compact and incremental-friendly.
- Initial online candidate_k 100 from the question. JEV `noul` scores **whether each candidate itself is necessary evidence for a fully supported chain**. This is NOT ordinary semantic cosine similarity.
- Maintain scored/protected previously retrieved documents, choose only unexpanded top evidence as frontier up to seed_k=10, select up to 20 **terms from source passages**, query BM25 by selected terms, rescore in original question + retained evidence context. Up to TWO additional expansion rounds. Deduplicate and carry forward earlier evidence; rank by JEV then fusion score.
- Greedy **DPP** diversity reorders the final top ten using JEV relevance/lexical similarity **without changing which ten items survive**. It is not a standalone four-source set selector.
- Official author paper reports MuSiQue R@5 **80.68%**; 2Wiki **97.35%**; HotpotQA **98.45%**, on original SAG2 1,000-question **macro evidence recall**, not PGER complete-source AE@5 and not MultiHop-RAG. JEV model/provider calls and judgments are material to cost (the MuSiQue H2 paper control reports 331,325 candidate judgments). The public SAG2 README describes a configured JEV endpoint; a literal faithful head-to-head requires that exact endpoint or an equivalent validated local judge and cannot be presented as a free stand-in.

**PGER-inspired proxy:** Keep PGER V11.4 trained passage utility (not JEV), use SAG2's **local DPP-only** diversity reranking on the SAME existing top ten PGER candidates. No new search, source dedup unchanged. This is only an ablation of one mechanism; previous V9.6 and V11 term expansions were weak or negative. Exact implementation is in benchmark_v12_architecture_ablation.py and preserves all source IDs.

### 2) HippoRAG 2 — From RAG to Memory (ICML 2025)
**Official code:** https://github.com/OSU-NLP-Group/HippoRAG/blob/main/src/hipporag/HippoRAG.py ; https://github.com/OSU-NLP-Group/HippoRAG (MIT)

- Offline OpenIE extracts entity/fact triples and creates a graph with fact-edges, passage-entity edges and synonym edges. Embeddings for facts, entities and passages are maintained.
- Online retrieve relevant query entities/facts, anchor the **Personalized PageRank** distribution on the query, and propagate relevance over a prebuilt association graph; the returned sources are original passages, not graph hallucinations. Dense passage retrieval may provide fallbacks. Graph construction is **not free**; cannot equate online PPR milliseconds to full index cost.
- Official HippoRAG2 has a heavy OpenIE/data processing and embedding dependency (local GPU or hosted models), and is far more than a plain TF-IDF document graph.

**PGER-inspired proxy:** Build low-cost TF-IDF document adjacency once, take a **query-local 120-candidate induced graph**, seed on PGER learned top eight, perform 10-step sparse/dense Personalized PageRank, mix 22% graph score with original learned scores. **No OpenIE, typed fact edges, dense embedding or actual relation verification**. The graph probe tests whether network diffusion yields useful four-evidence improvements without replacing PGER's controller.

### 3) S2G-RAG — Structured Sufficiency and Gap Judging, ACL 2026
**Official code:** https://github.com/nianaaa/S2G-RAG/blob/main/inference/inference_bm25.py ; ACL source https://aclanthology.org/2026.acl-long.1185/

- At each turn a **LoRA-trained sufficiency judge** receives original question + accumulated compact evidence context, outputs `sufficient` plus structured missing fact/gap items.
- Missing gap items feed targeted BM25/E5 searches, with source dedup and sentence-level evidence extraction, not unlimited all-topic expansion. Stop when sufficient or max_turns (default 4); only then answer. Different objective: **end-to-end generated answer EM/F1**.
- Local GPU with model + LoRA (base 3B judge, larger answer reasoner) or configured remote inference is needed for faithful reproduction. The source code itself warns of input limits/CPU/GPU; this is not the lightweight lexical-only gap proxy.

**PGER-inspired proxy:** Keep PGER's own proof-gap/necessity concept and *test only* a cheap marginal **uncovered question-term** selection rule over existing top-120 documents, with learned passage score dominant. Never claim the lexical proxy is S2G's trained sufficiency/contradiction judge.

## II. Exact matched experiment protocol (not official external system run)

Training is fixed as PGER's existing V11.3 boosted 23-feature classifier on MultiHop-RAG question offsets 0:400, with frozen hyperparameters, 316 properly mapped gold-support cases. Three proxies and the unchanged boosted, V7.1 and BM25 baselines evaluate on the SAME previously unused PGER question IDs 2000:2400, same 609 original article corpus, identical fixed 120 candidate source pool, identical 2 facet-search calls, labels withheld until after selection, Top5/Top10 and actual source ID ground truth. Track source count=2/3/4 separately, paired bootstrap, postindex CPU and offline TF-IDF cost. No confirmed claim of semantic relation, answer truth, verified logical hops or calibrated abstention.

**Comparison boundary:** This allows an ablation of three architectural ideas **at the same candidate / search budget**, not an empirical claim that PGER beat SAG2, HippoRAG2, or S2G-RAG. To literally rank all four systems one must execute their official full implementations with **same corpus, source mapping, answer model, JEV/LLM budget, offline indexing/memory and common metrics**. At present those conditions are not available without large model costs or user-authorized service spending; do not invent scores. Public leaderboard recall and PGER AE@5 cannot be directly compared.

## III. Scientific decision gates

- Keep PGER's provenance ledger and learned candidate scoring regardless of ablation; do not replace its truth-seeking policy with a lexical graph.
- **Only promote a mechanism if** it improves 4-support AE@5 or AE@10 against the learned boosted baseline without broad regressions, with paired uncertainty and measured CPU index/rank costs. A change that merely shuffles easier 2-source cases is not enough.
- If all three fail, record failures, retain boosted PGER, and prioritize a **genuine typed source-edge verifier with human supervision** or official open benchmark head-to-head. Do not continuously tweak source-title/term-co-occurrence thresholds.
- If a proxy wins, require source-/topic-disjoint confirmation and official baseline runs before novel/SOTA claims.
- Dense/graph/iterative techniques have substantial prior art. Originality, if any, must be demonstrated in falsifiable proof-gap behavior and cost-normalized reliability, not from combining established parts.

Sources and exact algorithm traces are in the official repositories above; user-owned PGER originals and all previously recorded failures remain untouched. No paid APIs, recurring scanning, merges, production deployment or main writes.
