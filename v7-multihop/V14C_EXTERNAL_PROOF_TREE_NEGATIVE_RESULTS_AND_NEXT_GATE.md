# PGER V14A–V14C: genuine human proof-tree external science evaluation — major NEGATIVE transfer

Date: 2026-10-28.
Audit runs: V14A https://github.com/vjgits/Research-Papers/actions/runs/40728695794
Provenance: V14B https://github.com/vjgits/Research-Papers/actions/runs/40728941488
Official held-out model run: V14C https://github.com/vjgits/Research-Papers/actions/runs/40729260684
Full v14C question-level results artifact https://github.com/vjgits/Research-Papers/actions/runs/40729260684/artifacts/12832579742
**Branch:** v14c-entailmentbank-heldout-retrieval-2026-10-28 ; main unchanged.

## Independent published benchmark and proof annotations

Dalvi et al, EMNLP 2021 EntailmentBank v2, open CC-BY-4.0 mirror sxiong/entailmentbank pinned to Hugging Face revision 8c6c148f7a21c21ff037a42d9a22446c9d42debc. Official task1 train/validation/test: 1,313 / 187 / 340, original source fact bank 11,941 WorldTree+additions. Original test 340 gold proof trees include 196 questions requiring >=4 proof-leaf facts, 91 questions with annotated depth>=4. **Proof leaves and depth are not the same thing.** Test labels used only OFFLINE after ranking for metrics; no answer text or hypothesis injected into retrieval questions.

V14A initial strict unique-text audit yielded 121/340 test questions fully mapped; V14B corrected that by deduplicating identical WorldTree fact text (valid exact information equivalence). This yields **233/340** exact-complete source availability, including **117/196** four-plus-fact cases. UUID provenance can link a further 54 test questions (287/340 potentially source-linked), but 70 questions have rewritten source fact wording and UUID links are **not guaranteed exact entailment**, so V14C DID NOT count them as exact-available. Remaining 53 questions had some unmappable facts even by UUID. All this is reported in source availability; never silently filter out unavailable ones.

## Frozen actual retrieval and first 400 train examples

117? No: in **all official 340 test** questions (including all missing-source and >K infeasible queries), strict complete facts@K:

| Method | All annotated proof leaves @5 | @10 | @20 |
|---|---:|---:|---:|
| BM25 | **9/340 = 2.647%** | 15/340 = 4.412% | 22/340 = 6.471% |
| V7.1 title graph fast | 8/340 = 2.353% | 15/340 = 4.412% | 22/340 = 6.471% |
| Two-facet BM25 | 8/340 = 2.353% | 15/340 = 4.412% | 22/340 = 6.471% |
| PGER cached boosted (frozen V11.3 ML spec; trained first 400 task1 train queries) | **8/340 = 2.353%** | 16/340 = 4.706% | 22/340 = 6.471% |

Paired boosted vs V7.1 complete@5 0.00 pp, 95% bootstrap CI [-1.176,+1.176], 2 wins / 2 losses. Boosted does NOT improve proof-leaf source retrieval out-of-domain.

**Four-plus-fact** 196 gold test questions, only 117 have ALL gold exact source facts available in corpus, only **1/196** has all exact gold facts somewhere in broad 120-candidate PGER retrieval pool; every arm complete@5/10/20 is **0/196**. Deep proof depth>=4: 91 questions, 58 source-complete in corpus, ZERO full gold pools and ZERO complete@5/10/20 across all arms. By the nature of proof leaves, for gold leaf count >5 complete@5 is impossible and >10 complete@10 impossible even with an oracle.

The new domain exposes an almost absolute **source discovery** bottleneck, not primarily ranking. Earlier MultiHop-RAG 4-source pool recall near 100% must not be used to generalize to this science benchmark. Prior V14 provenances and performance are independent of user-provided simulated 8-hop graphs.

## Efficiency caveats

Official test mean additive process CPU ms: initial retrieval 0.828, cached features 1.284, extra 2 facet queries 0.574, model prediction+ranking 0.522; ~3.208ms excluding indexing, not interactive end-to-end p95. Cheap but accuracy fails catastrophically. Improvement cannot be claimed.

## Next V14D hypothesis, pre-registered after observed V14C failure

Different mechanism: **dense evidence discovery** using a frozen, openly licensed BGE-small-en-v1.5 from prior V9.7, with measured offline CPU embedding cost and identical question-only input. Compare BM25, V7.1, dense-only, BM25+dense hybrid 120-pool, and frozen/strict development-trained hybrid boosted. Preserve exactly the test 340 cases, exact-text gold availability, true proof depth and missing fact accounting; all confirmation outcomes disclosed as post-hoc future benchmark development because V14C already inspected test. Do not claim sealed generalization on repeat. Do not call dense cosine similarity entailment proof. No API keys or background monitoring.

A truly general 4–8 logical-hop answer system still needs independently verified intermediate edge reasoning and controlled abstention with correct answer scoring. A gold proof structure is an annotation, not a generated PGER proof.

No merges, main writes, scheduled tasks, paid API calls or model safety gate relaxation.
