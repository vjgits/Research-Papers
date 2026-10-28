# PGER V8.8: Source-First Natural Relation Extraction — Negative Result
**Research date:** 2026-10-27 Pacific / 2026-10-28 UTC  
**Successful one-time run:** https://github.com/vjgits/Research-Papers/actions/runs/40642713518  
**Per-document data artifact:** https://github.com/vjgits/Research-Papers/actions/runs/40642713518/artifacts/12795964000  
**Branch:** `v88-source-first-relation-2026-10-27` — no changes to `main`.

## Decision
**V8.8 did not improve source-first subject–predicate–object recovery.** Starting with raw Wikipedia/DocRED sentences, the regex/cue system recovered **5/386 (1.30%)** annotated positive relationships in the 16-property ontology; pretrained spaCy NER plus the *same* source cue extractor recovered only **4/386 (1.04%)**. Filtering either set with pretrained NLI recovered precisely the **same** known correct relationships. No 4+ hop reasoning, end-to-end retrieval, final answer generation, or actual proof-gap resolution was measured. Do **not** deploy this as a reliable knowledge-graph or source-grounded truth extractor.

## Question and frozen sample
- Can we propose entity pairs and typed relations directly from natural documents **without supplying gold annotated entity pairs**, unlike V8.7?
- Source: official DocRED public validation `dev.json.gz`, 998 docs, source SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`.
- Frozen 60 gold-positive documents selected deterministically; **54 DocRED source document IDs previously inspected in V8.7 excluded**. Cohort SHA256 `2e4e4afef8efebc40d6fabc40f02309ce7ef0e90612d30d71e3481df53fe8b85`. **386 positive annotated 16-ontology triples** in these docs.
- Scope caveat: selection required a known annotated positive triple, and the simple regex baseline (5/386) was inspected *before* final spaCy+NLI controls were frozen. This is a **public development evaluation, not a sealed independent test**. Gold annotations were used to select source documents and score after extraction, not to construct extraction candidates.
- All methods share identical fixed local pair-proposal radius (same or next sentence), pair cap 300, relation cue patterns/negation guard, citation spans and 16 class ontology. Typed cue patterns are narrow and incomplete. Pretrained `en_core_web_sm` (spaCy 3.8.11; pipeline 3.8.0) is the only NER replacement.
- The two NLI filter arms use `cross-encoder/nli-MiniLM2-L6-H768` pinned revision `9aa22b250d25a10ac39ab4a6b2bc28213507cb0c`, three-class logits [contradiction, entailment, neutral], P(entailment)>=0.70 and margin>=0.10, up to **48** candidate triples/doc. NLI can **only filter** already proposed triples; it cannot discover unproposed evidence. No paid API or model fine-tuning.

## Stage-wise positive-gold recovery (exact head alias, tail alias, directed relation ID)
| Stage | Regex baseline | spaCy NER + same cues |
|---|---:|---:|
| Both annotated entities named in proposed mentions | 286/386 (74.09%) | 280/386 (72.54%) |
| Pair included among local candidate pairs | 212/386 (54.92%) | 212/386 (54.92%) |
| Correctly typed relation found | **5/386 (1.30%)** | **4/386 (1.04%)** |
| Correct relation **and** matching annotated evidence sentence | 4/386 (1.04%) | 3/386 (0.78%) |
| All proposed triples emitted (not correctness or precision) | 26 | 26 |
| Proposed triple count after NLI | 22 | 23 |
| Correct triples retained after NLI | **5/386** | **4/386** |

Of the 60 documents, **38** had no proposed triples at all from the regex arm. Gold sources have not been exhaustively hand checked for partial entity aliases or unannotated relations, so these are *strict annotated-positive* recovery measures.

**Paired spaCy minus regex**, document-cluster bootstrap (3,000 resamples; source-document clusters; seed 20261027):
- Both entities found: **−1.55 percentage points** (95% CI [−10.05,+7.04]).
- Candidate pairs: **0.00 points** (95% CI [−6.97,+6.94]).
- Correct typed gold triples: **−0.26 points** (95% CI [−0.85,0.00]), 0 improving documents and 1 regressing document.
- Individual annotated-triple recall: regex 1.295% (95% document-cluster CI [0.277%,2.500%]); spaCy 1.036% ([0.233%,2.162%]). These are exploratory intervals on a small selected cohort.

## Sampled successes and failures
- **Correct mention/cue:** `Paul Beliën`, the source sentence "Beliën is married to Alexandra Colen..." correctly proposed `Beliën — P26 (spouse) — Alexandra Colen`.
- **Correct mention/cue:** `Elwood Buchanan`, "Buchanan was born in St Louis..." correctly proposed P19 birthplace.
- **Correct mention/cue:** `Durán, Ecuador`, "Durán ... located in the province of Guayas..." produced the locally supported P131 administrative location.
- **Recall gap:** `Essingen Islands` had 17 annotated positive ontology triples and no regex cue triplets, illustrating the inability to infer many implied/document-level relations from plain co-occurrence and indirect evidence.
- **Legacy misattribution case:** `Kalank` director/producer is protected in a narrow unit test, but source-position rules still are not a general dependency parser or proof of complete clause attribution.

## Provenance, cost and limitations
- **100% exact byte/source-hash validity on proposed quoted sentences**. This establishes quote location **only**, not entailment or worldly truth.
- Regex proposed **1,321** entity mentions, **6,413** local pair candidates and **26** relation triples across 60 documents. spaCy proposed **1,097**, **4,445** and **26**, respectively. Large pair inventories did not solve relationship interpretation.
- The additional NLI filters made **26** relation-verification model calls in each arm; combined NLI inference measured around **1.0 second total for 60 documents per arm** in this shared-process GitHub CPU run, excluding model load and NER costs. NER+NLI model initialization took 10.806 sec total. Per-document latency and production end-to-end time were not separately benchmarked; do not infer serving throughput from these figures.
- **Do not estimate precision** by treating unlabeled triples as false. DocRED's annotations are not exhaustive; unannotated predictions may be correct. The study is positive-gold exact recovery only. The fixed 16-property ontology, strict alias comparison, rule templates, proximity cap, no entity coreference, and no cross-sentence relation inference create low coverage.
- A document's number of annotated support sources does not equal logical hop count. There is **no** new multi-hop QA benchmark, answer reader, contradiction adjudication, calibrated abstention, official IRCoT/HippoRAG2 reproduction, or independent final generalization result.
- NER, BM25, typed cue matching, NLI and source-span hashes are standard components, not novel PGER algorithms.

## Scientific conclusion and next gate
**V8.8's main bottleneck is relation candidate generation**, not relation filtering. The strict lexical/one-sentence triple extractor proposed too few triples: an NLI filter cannot increase recall. Do not expend another iteration on filtering these same 26 proposals.

For **V8.9**, compare a genuine free open-weight, document-aware relation generator (for example REBEL or a DocRED-trained model), coupled with sentence provenance and an explicit *no-relation* option, against the same public baseline **without supplying gold entity pairs**. Add a small independently manually adjudicated sample for entailment / neutral / contradiction including unlabeled predictions. Only if real typed-relations improve should the resulting components enter a **matched-budget MuSiQue 3/4-hop** proof-gap retrieval ablation, followed by a fixed answer reader and sealed benchmark.

**No SOTA claim, NeurIPS readiness upgrade, paid APIs, reviewer agents, recurring runs, or changes to main.**
