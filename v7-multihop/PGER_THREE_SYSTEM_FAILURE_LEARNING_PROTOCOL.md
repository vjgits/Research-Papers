# PGER: mandatory three-architecture failure review (V15)

Adopted: 2026-10-28, after V14 EntailmentBank science-domain failure.
Status: review policy and proposed design, NOT an implemented or validated new retrieval algorithm.
Research branch: v15-three-architecture-failure-gate-2026-10-28.

## Persistent three-reference comparison

After EVERY failed experiment or material regression, review all three:
1. SAG2: https://github.com/Zleap-AI/SAG-Benchmark/blob/main/sag2/scripts/sag2.py and https://arxiv.org/abs/2610.22588
2. HippoRAG 2: https://github.com/OSU-NLP-Group/HippoRAG/blob/main/src/hipporag/HippoRAG.py (ICML 2025).
3. S2G-RAG: https://github.com/nianaaa/S2G-RAG/blob/main/inference/inference_bm25.py and https://aclanthology.org/2026.acl-long.1185/

Use exact official code/papers rather than just abstracts/marketing claims. Capture source commit when possible. Never present our small proxies as faithful implementations or official head-to-head runs. SAG2's recall@K and S2G's answer EM/F1 are not PGER's full-gold-chain@K.

## Past failure in our process

V12 only approximated three SUBCOMPONENTS:
- SAG2 local DPP reordering WITHOUT JEV contextual necessity judging, retained evidence-driven BM25 term expansion or iterative query-time association.
- HippoRAG2 local PPR over TF-IDF document similarity WITHOUT OpenIE fact/entity graph, typed fact edges, passage association and query-conditioned fact retrieval.
- S2G-RAG lexical uncovered question words WITHOUT a trained sufficiency judge, explicit missing FACT proposals, compact evidence memory or conditional next-turn targeted search.

All three simplified ranking probes failed to improve PGER overall. They do NOT disprove the full systems. V13A learned pair co-necessity failed; V13B MiniLM falsely accepted 95 of 135 HANS non-entailment items; V13C software guard passed unit tests but has no approved fact verifier.

V14 external EntailmentBank test required 4+ exact proof leaf facts on 196 cases. Sparse top120 pool had complete facts for 1/196, sparse+dense top120 for 11/196, despite 117/196 having all exact facts actually present in the full corpus. The critical bottleneck changed from final-ranking selection (previous news results) to candidate discovery (science). Repeated unverified lexical reranking is not an adequate response.

## Mandatory failure-to-design procedure

1. CLASSIFY: missing candidates; wrong ranking; unsupported/contradictory relation; redundant search; missing external sources; CPU/cost; source mapping/annotation; out-of-domain transfer. Record measured numbers and exact cohort.
2. REVIEW ALL THREE: for each official architecture, state exact code/paper, key DIFFERENT mechanism, its offline/online costs/trust dependencies, what our prior approximation omitted, and a credible reason why it might or might not correct THIS failure.
3. FORM A CAUSAL HYPOTHESIS: identify one observably detectable (never gold-derived at runtime) gap, the component to replace/add, predicted gain, falsifier and expected cost.
4. DESIGN PGER-NATIVELY: preserve competing hypotheses, typed proof gaps, source text/provenance hashes, independence checks, contradiction tracking, bounded retrieval, justified abstention. No wholesale system copying or rebranded existing algorithm.
5. NAME PREVIOUS NEGATIVE CONTROLS: do not re-run old lexical co-mention, DPP, TF-IDF PPR or HANS-unsafe NLI simply by changing weights.
6. PRE-REGISTER matched costs and evaluation: same corpus and questions, exactly controlled candidate/search/LLM budgets; candidate coverage versus complete@5/10/20 versus true proof depth; human edge entailment and answer correctness when available; p50/p95 wall, CPU, indexing/storage/token costs; paired CIs and all regressions; source/topic-disjoint untouched test.
7. DECISION: accept only after meaningful frozen gains and independent replication, otherwise record negative and repeat review. Never automatically promote by merely passing this document checklist.

## Concrete postmortem: V14 facts are missing from retrieval candidate pool

SAG2's missed mechanism: contextual JEV source NECESSITY -> previously selected source evidence as search frontier -> bounded extract-terms-to-BM25 search -> rescore with accumulated source memory. Our V12 DPP-only proxy did none of that. PGER hypothesis: bounded evidence-frontier queries could find intermediate leaf facts; JEV-equivalent judgments need independent validity checks, not mere boosted relevance.

HippoRAG2's missed mechanism: typed entity/atomic-fact associations, passage-fact source links and query-conditioned graph traversal. Our TF-IDF document similarity PPR cannot infer facts. PGER hypothesis: source-quoted, typed fact edges may suggest related missing premises; no graph edge is accepted as true without independent verification, and offline graph extraction cost is counted.

S2G-RAG's missed mechanism: structured missing proposition + trained SUFFICIENCY judgment and compact sentence-level evidence state. Our lexical-word coverage ignored relation direction and missing predicates. PGER hypothesis: generate a tentative missing atomic proposition (subject/predicate/object, direction/negation/time), select a bounded query targeting it, and check retrieved evidence; if the verifier is not trusted, label the proposed proposition UNVERIFIED and allow proof gate to refuse/abstain.

### PGER-native proposed integration — NOT YET IMPLEMENTED

Question and competing hypotheses
  -> cheap BM25 + learned ranking
  -> source-anchored evidence ledger and provisional typed proof obligations
  -> inspect observable unmet proof obligation (not gold label)
  -> select one of three bounded actions:
       (a) SAG2-inspired source-frontier expansion,
       (b) HippoRAG2-inspired grounded fact/entity neighbor exploration,
       (c) S2G-inspired missing-Fact query with compact evidence memory
  -> merge/retag source spans and independence
  -> independently authorized edge verification; unsupported edges remain UNKNOWN
  -> answer / targeted next pass / abstain within a finite budget

No automatic use of the MiniLM NLI checkpoint that failed V13B. Do not infer logical entailment from co-occurrence, graph connectivity, cosine similarity, DPP, or boosted classification.

## Different failure -> different architecture cue

- ALL gold already in pool but Top5 wrong (news four-source case): SAG2 necessity judge; Hippo fact relation links; S2G joint sufficiency. Invest in independently verified SET selection; don't just search further.
- Gold missing from candidate pool (V14 science): SAG2 evidence-driven frontier, Hippo typed graph neighbors, S2G concrete missing fact search; benchmark identical 0/1/2/3 search budgets.
- Proof false-positive: no SAG/Hippo connectivity is proof, and S2G sufficiency judge must be domain validated. Maintain V13C default-deny and no verifier until human-labeled adversarial evidence-edge evaluation passes.
- Excessive cost: SAG2 cheap initial SQLite/BM25 and necessity checks only when needed; Hippo offline graph amortized with explicitly measured build time; S2G compact evidence context/bounded turns. Select expensive work only on learned, validated, gold-independent uncertainty.

## Gate and limitations

- The accompanying machine-readable review and validator can test whether the required comparative discussion and cost/decision fields exist, not whether scientific claims are true.
- Every NEXT experiment workflow should invoke the validator before benchmarking. This is a repository process, not an enforced GitHub ruleset: a workflow not opting in can bypass it.
- Do not claim official SAG2 / HippoRAG2 / S2G performance comparisons without running the original implementations on matched sources/metrics/hardware/model budgets.
- PGER's distinguishing contribution must be proven via alternative-hypothesis handling, non-redundant proof gap targeting, grounded source independence and justified abstention—not by combining common components.
- No paid API, schedules, main writes, merges or deployment without explicit later instruction.

V15 next measurement: independent typed missing-fact proposal validity and bounded evidence-frontier source retrieval on new topic/source-disjoint human annotated proofs, before expensive graph and verifier integration. Previously inspected EntailmentBank test is exploratory ONLY.
