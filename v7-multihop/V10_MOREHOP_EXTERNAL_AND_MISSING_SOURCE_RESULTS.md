# PGER V10: MoreHopQA external human-verified corpus transfer + 15% missing-source stress

Date: 2026-10-28. Completed GitHub Actions: https://github.com/vjgits/Research-Papers/actions/runs/40712715965 . Full per-question artifact: https://github.com/vjgits/Research-Papers/actions/runs/40712715965/artifacts/12827122027 .

**External source:** alabnii/morehopqa, 1,118 author human-verified QA records, CC BY 4.0. Downloaded and SHA256-manifested official `with_human_verification.json`; built a **pooled 601 unique source-document corpus** from the question contexts, NOT a web-scale open-world collection. All 1,118 records had at least two annotated gold supporting-context titles present. The evaluation maps each document to its title, and reports *complete annotated supporting-title chain@5*, **not** exact source-passage chain@5, factual answer correctness, relation entailment, or calibrated abstention. This is an original PGER out-of-corpus transfer pilot, not a known leaderboard protocol.

## Original pooled corpus

| Arm | Complete supporting titles@5 | @10 | Avg gold title recall@5 |
|---|---:|---:|---:|
| BM25 | 63.3274% | 68.4258% | 81.1717% |
| V7.1 fast (no added searches) | 83.3631% | 85.0626% | 91.1896% |
| V9.5 two additional sparse searches | 84.3470% | 86.0465% | 91.6816% |

Paired V9.5 vs V7.1: **+0.984 percentage points**, bootstrap 95% interval [+0.179,+1.789], **17 per-question wins/6 losses**. This small improvement is not yet a better *accuracy/compute frontier*; the additional CPU/index costs are not established as worthwhile.

## Deterministic hash-blind 15% document-source blackout

Initial **601** unique documents, retained **524** after a SHA-based blackout (77 docs missing). The blackout is selected solely by source text hash, **not gold documents, dataset hop count or query outcomes**. 255/1,118 QA questions now lacked at least one required supporting source *title*; complete evidence-chain@K becomes impossible for those questions.

| Arm | Complete titles@5 after blackout | @10 |
|---|---:|---:|
| BM25 | 48.8372% | 52.4150% |
| V7.1 | 63.9535% | 64.5796% |
| V9.5 | 64.2218% | 66.1002% |

V9.5 vs V7.1: +0.268 pp, CI [-0.449,+1.073], 11 wins/8 losses. Evidence absence is not addressed by simply searching the same diminished corpus more. No successful detection of missing evidence/abstention was measured.

## True hop-count caution

All 1,118 records have **three question-decomposition entries**; the `no_of_hops` field is the dataset's **extra reasoning-step count** (distribution: 1=444, 2=416, 3=154, 4=13, 5=91). These fields are NOT direct proof of five independent retrieval hops or eight distinct supporting documents. MoreHopQA adds arithmetic/symbolic/commonsense reasoning atop earlier multi-hop questions. Our system did not generate answers or check these deductions. We categorically make **no 5/6/8-hop success claim** from this experiment.

## Feedback to next stage

V7.1's title graph can transfer to a small pooled external corpus. Extra BM25 searches may yield tiny title-recall gains but are not worth universal extra cost without a stronger gain on a compute-normalized frontier. Missing source information calls for external source acquisition and calibrated refusal, not more searches of the same corpus. For genuine 4–8-hop retrieval, build a separately human-audited dependency/path dataset and evaluate answer correctness + relation/citation entailment; do NOT fabricate synthetic depth as independent validation.

All original V7–V9 negative findings preserved; PGER novelty remains unproven against SAG2, ScalableRAG, S2G-RAG, GroundRAG and SPARE-RAG. No paid APIs, recurring automation or main-branch changes.
