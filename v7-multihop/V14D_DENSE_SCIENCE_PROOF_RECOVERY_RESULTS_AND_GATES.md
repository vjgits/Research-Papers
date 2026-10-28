# PGER V14D: external science proof-chain source discovery improves modestly, full chain remains UNSOLVED

**UTC date:** 2026-10-28.
**Successful GitHub Actions:** https://github.com/vjgits/Research-Papers/actions/runs/40729726941
**Full per-question artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40729726941/artifacts/12834442696
**Branch:** v14d-science-dense-source-recovery-2026-10-28. Main and all earlier V7–V14C negative results unchanged.

## Provenance and protocol

New science domain from Dalvi et al. EMNLP 2021 EntailmentBank v2, official task1 train/validation/test sizes 1313/187/340, 11,941 original WorldTree fact rows and 11,941? text-deduplicated corpus size is recorded EXACTLY in the source JSON. CC-BY-4.0 mirror sxiong/entailmentbank revision 8c6c148f7a21c21ff037a42d9a22446c9d42debc. Gold proof tree leaf fact texts, proof inference depth/steps and expected reasoning hypothesis are published. **No answer or hypothesis text is passed to query generation**, only the original science question.

V14C already inspected the official 340-question public test, so **V14D is explicitly exploratory repeat**, not a sealed test. Train two unchanged V11.3-spec balanced boosted rankers on first 400 original science *training* question labels, one on sparse 120 candidate pool, one on capped hybrid 120 candidates (60 sparse + 60 dense). Pretrained BGE-small-en-v1.5 (MIT) pinned Hugging Face SHA `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. Dense-only top80, RRF hybrid, and sparse BM25/V7.1 controls, all same source corpus and question IDs. Evaluation annotations applied **only after producing rankings**. Exact canonical fact text dedup prevents duplicate identical sources from creating artificial chain depth. Rewritten or corpus-absent facts are not counted as available; UUID provenance is recorded separately but not treated as semantic equivalence.

## Official TEST 340 questions: exact proof-leaf retrieval

| Arm | Complete @5 | Complete @10 | Complete @20 | Four-plus leaf cases complete @5/@10/@20 |
|---|---:|---:|---:|---|
| BM25 | 2.6471% | 4.4118% | 6.4706% | 0/196 at every K |
| V7.1 fast | 2.3529% | 4.4118% | 6.4706% | 0/196 |
| PGER sparse boosted | 2.6471% | 4.7059% | 6.4706% | 0/196 |
| Dense BGE direct | **3.5294%** | **6.1765%** | **9.7059%** | 0/196 @5, 0/196 @10, **1/196 @20** |
| Hybrid sparse/dense RRF | 3.2353% | **6.1765%** | 9.4118% | 0/196 @5/10/20 |
| PGER hybrid boosted | 2.0588% | 4.1176% | 6.1765% | 0/196 @5/10/20 |

Dense direct vs sparse boosted @10 +1.471 pp, 95% paired bootstrap CI [-0.882,+4.118], 12 wins/7 losses. No clearly verified broad superiority. Hybrid boosted regressed vs sparse boosted (-0.588 pp @10; CI [-1.471,0]). **Do not promote hybrid boosted model**. Ranking gains remain far below 4+ fact proof success.

### Pool discovery: 340 test questions, same source corpus

| Pool budget | Full gold source fact set in candidate pool (all 340) | Four-plus gold proof leaves (n=196) |
|---|---:|---:|
| Sparse-only 120 | 41/340 | 1/196 |
| Dense-only 80 | 64/340 | 6/196 |
| **Hybrid 120** | **81/340** | **11/196** |

Absolute gains: +40/340 full candidate sets vs sparse, +10/196 four-plus complete candidate chains. Of the four-plus questions, only **117/196** have all strict exact-text gold facts available even in the complete corpus. Nevertheless, hybrid has only 11/117 full pools on this recoverable subset: major retrieval discovery failure remains. Gold proof inference depth>=4 (n=91) was zero complete at all Top5/10/20 final rankings.

**Important**: Number of proof leaf facts != annotated inferential depth. Retriever output is not a generated proof and does not validate fact-to-fact implications. For >5 required distinct facts, exact @5 is impossible; @10/20 and full-pool diagnostic are necessary for fair interpretation.

## CPU/efficiency

BGE-small full fact corpus pretrained encoding **111,868 process CPU ms (~112 CPU-seconds)**, query batch encode+similarity **22.473 ms/query amortized** (training+validation+test batch), vector index **17,620,992 bytes (~16.8 MiB)**, 384-dimensional, cold model CPU load ~1.082 s. V14D test additional observed CPU components: sparse retrieval and dense topK extraction ~7.358ms, hybrid 23-feature extraction ~3.707ms, dual boosted prediction+rerank ~2.250ms. The additive process CPU estimates are NOT production p95 or end-to-end query latency, and above 22.473ms dense encoder cost must be included in any matched inference budget. Index CPU and memory remain material.

## Research feedback and gating

1. **Sparse architectural transfer failed** on this independently gold-annotated science domain even after retraining: V14C BM25/V7.1/PGER @5 ~2–3%, four-plus complete 0.
2. **Pretrained dense helps candidate discovery but not enough**: hybrid full pool 41 -> 81 out of 340, hard 1 -> 11/196, with expensive offline embedding.
3. **Hybrid boosted ranker worsened results**; no automated promotion. Generic similarity and boosted relevance are not a proof verifier. Previous V13B MiniLM HANS model failed false-entailment safety gate and stays prohibited.
4. Distinct failure types now depend on domain: news benchmark 4-source candidate pool nearly saturated with poor Top5 set selection; science proof benchmark has largely ABSENT gold candidates. PGER controller must recognize which bottleneck exists from observable uncertainty features WITHOUT using gold.
5. The genuine next experiment should be a fixed-budget **fact-level dependency-guided targeted retrieval** leveraging only source quotes and extracted tentative missing relationships, with real named-entity/relation verifier precision measured against independent human proof edges. Do not reuse failed lexical co-mention, source-title DAG shortcuts or unvalidated MiniLM entailment.
6. Need genuinely new topic/source-disjoint annotations to avoid repeatedly searching publicly inspected EntailmentBank test. A source availability-aware abstention/refusal gate is required: unavailable 107/340 exact-test proof examples are intrinsically unrecoverable in this corpus.
7. External SOTA comparison not established: no matched official SAG2, HippoRAG2, S2G-RAG, GroundRAG etc with identical sources, answer model, objective, CPU budget. No novelty or best-in-industry claim.

No paid APIs, recurring scans, merges, main writes, unverifiable proof/answer outputs or background jobs.
