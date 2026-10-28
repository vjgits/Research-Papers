# PGER V14A–V14D authoritative handoff — external human proof trees and negative domain transfer

**UTC 2026-10-28.** Research branch: `v14d-science-dense-source-recovery-2026-10-28`. All earlier PGER V7–V13 decisions preserved; main untouched; no paid models or schedules.

## Source evidence and integrity

Dataset: EntailmentBank (Dalvi et al EMNLP 2021) task1 with 1313 official train, 187 validation and 340 test cases, containing explicit gold proof leaf facts, intermediate reasoning steps, proof-tree depth and answer hypothesis. Released 11,941 WorldTree/EntailmentBank fact rows, deduplicated to **11,472 unique canonical text statements**. CC-BY-4.0 mirrored sxiong/entailmentbank, revision 8c6c148f7a21c21ff037a42d9a22446c9d42debc.

Audit test stats: 196/340 annotated examples require >=4 distinct proof leaf IDs; 91/340 have inference depth>=4. They are distinct quantities: source fact count is not inference hop count. 233/340 have all gold exact statement texts present; an extra 54 can be associated by published UUIDs, making 287/340 potentially provenance-linked, but 70 questions have at least one rewritten premise not guaranteed equivalent, and 53 have some fact not resolved even by UUID. **Strict exact-source evidence only** for primary metric. All missing leaves and >K infeasibility remain in denominator; never silently filter. Candidate source evidence is not a generated or semantically verified proof.

## Completed experiments and decisions

V14A schema/depth audit successful: https://github.com/vjgits/Research-Papers/actions/runs/40728695794 .

V14B provenance and duplicates audit successful: https://github.com/vjgits/Research-Papers/actions/runs/40728941488 .

V14C new out-of-news-domain official test, trained frozen 23-feature PGER boosted on first 400 task1 train ONLY, question-only queries, no answer/hypothesis:
- BM25 complete exact source fact set @5 **9/340 (2.647%)**, V7.1 **8/340 (2.353%)**, boosted **8/340 (2.353%)**. Boosted @10 **16/340 (4.706%)**, @20 **22/340 (6.471%)**.
- Four-plus-fact n=196, **0 complete @5/@10/@20** for all methods. All exact facts were in the original sparse Top120 candidate pool for **1/196**, despite 117/196 source-available in full 11,472-doc corpus. Deep gold proof depth>=4 n=91, **zero full gold candidate pools**.
- **FAIL PGER transfer**; sparse methods cannot rerank facts they never retrieved. CPU post-index small but irrelevant without accuracy.
- Successful run https://github.com/vjgits/Research-Papers/actions/runs/40729260684 ; source negative report `V14C_EXTERNAL_PROOF_TREE_NEGATIVE_RESULTS_AND_NEXT_GATE.md`.

V14D **EXPLORATORY repeat on the same inspected official test** after observing V14C (not a new sealed confirmation). Adds MIT `BAAI/bge-small-en-v1.5`, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, offline 112 CPU-sec source embedding, 17.6 MB vector index, 22.473 ms/query batch-amortized query encode + scoring. Same released 11,472-doc fact bank and question-only query; same maximum 120 source candidate budget (60 sparse + 60 dense) in hybrid.
- Sparse120 full candidate 41/340 overall, **1/196** 4+ fact.
- Dense80 full 64/340, **6/196** 4+.
- Hybrid120 full **81/340**, **11/196** 4+; improves candidate discovery but still ~94% hard examples lack full candidate set.
- Final exact source complete@5/@10/@20: PGER sparse boosted **2.647%/4.706%/6.471%**; dense-direct **3.529%/6.176%/9.706%**; sparse+dense RRF **3.235%/6.176%/9.412%**; PGER trained hybrid **2.059%/4.118%/6.176%** (regression).
- **All arms 0/196 complete 4+-fact chain at Top5/Top10**; one dense direct chain complete at Top20. Deep >=4 proof depth groups remain zero @5/@10/@20.
- Dense direct @10 vs sparse boosted +1.471 pp, paired 95% bootstrap CI [-0.882,+4.118] (12 wins/7 losses), not robust general superiority. PGER hybrid trained reranking is worse than simple sparse model; reject as default.
- Successful run https://github.com/vjgits/Research-Papers/actions/runs/40729726941 ; full results https://github.com/vjgits/Research-Papers/actions/runs/40729726941/artifacts/12834442696 .
- Source report `V14D_DENSE_SCIENCE_PROOF_RECOVERY_RESULTS_AND_GATES.md`.

## Scientific interpretation and nonclaims

No credible 4–8-hop *generated* reasoning, proof truth, relation entailment, answer correctness, current SOTA comparison, or universal performance is established. Published human gold annotations allow counting what the system **failed to retrieve**; they do not imply PGER inferred proof edges. Number of gold leaf facts can exceed 5 so AE@5 can be structurally impossible. Exact input answer/hypothesis not passed online. No test labels used to fit rankers; V14D test reuse after V14C limits its independent status.

Domain-specific bottleneck shift:
- Prior news MultiHop-RAG: near-saturated full source candidate pool but poor Top5 listwise four-source evidence selection.
- New EntailmentBank science: largely **missing source discovery**; even the hybrid only 11/196 complete four-plus candidate sets.
These two failure classes must be identified from **observable**, gold-independent signals, never oracle source counts.

Retain V11.3/11.4 boosted ranking as a news-domain experimental component; do not promote it as a universal retriever. Dense retrieval can be a costly source discovery component but should be gated by objective proof gaps and independently assessed. V13B MiniLM NLI had 70.4% false entailment on HANS adversarial non-entailment and remains forbidden as a proof validator; V13C default-deny provenance/contradiction ledger remains separately valid as a software safety mechanism.

## V15 next predeclared research direction (NOT executed)

1. Build source- and topic-disjoint human-labeled fact dependency evaluation; reserve a truly new test split not inspected during algorithm design. Try a new science proof corpus rather than continue selecting on EntailmentBank test.
2. Freeze a bounded **missing-fact hypothesis generator** with strict source quotes, provenance and typed relation slots; benchmark precision of proposed missing facts independently against gold proof edges. Avoid unverified lexical name/title matches from V8.5/V9.6B/V11 or unsafe MiniLM HANS behavior.
3. Compare 0/1/2/3 extra targeted searches to same-budget BM25/dense and simple independent baselines; report complete annotated source set@5/10/20, candidate coverage, per-question CPU/p95 wall, all offline embedding costs, and source-missing abstention.
4. Promote only if prior-art-aware and robust across separate corpora, matched hardware budgets and statistically supported answer correctness / evidence proof metrics. Do not claim novelty for generic dense retrieval, graph diffusion, boosted ranking, DPP, PPR or standard NLI.
5. Maintain all prior negative findings, deterministic per-question archives, no paid APIs, no scheduled jobs, no main modifications or merge.

The user-requested project goal (best across easy and 4/5/6/8+ logical hops) remains **unachieved**. The new human proof benchmark is valuable because it exposes limitations that old news retrieval scores obscured.
