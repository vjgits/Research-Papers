# PGER V8.9 — Frozen REBEL Source-First Relation Generator Pilot

**Status:** Pre-run protocol locked 2026-10-27 (Pacific), GitHub UTC 2026-10-28.  
**Branch:** `v89-rebel-generator-2026-10-27`, forked from `v88-source-first-relation-2026-10-27`; `main` untouched. No paid APIs, reviewer agents, cron or recurring monitoring.

## Pre-registered hypothesis and limits

V8.8's strict regex/spaCy typed-cue extractor recovered **5/386** and **4/386** human-annotated DocRED-positive 16-property relationships, respectively, despite finding many entities. A published open-weight *relation-generating* model (`Babelscape/rebel-large`; Huguet Cabot & Navigli, Findings of EMNLP 2021) may propose more plausible complete subject–predicate–object triples without gold entity-pair hints. REBEL is **existing prior work, not PGER originality**. Hugging Face model license `cc-by-nc-sa-4.0`; research-only/noncommercial restrictions apply. All predictions must retain cited original sentences; the existence of a quote or a surface match is **not** a proof of semantic entailment or factual truth.

## Fixed dataset and matched comparison

- Source: official DocRED public validation, 998 docs, same verified source dataset as V8.8; use the deterministic **first 20 documents of V8.8's already-inspected 60-positive-document sample**. Exactly **NOT a fresh or sealed test**. V8.7's 54 document IDs remain excluded. The pilot is exploratory, **not** a leaderboard or independent claim.
- Document input: **first up to six source sentences** of character lengths 20–500, in source order. Both REBEL and regex cue baseline see *the identical six sentences* with the same source sentence IDs. No gold entity names, relation labels, or gold evidence IDs are supplied to either method.
- REBEL weights: `Babelscape/rebel-large`; tokenizer/input truncated to **256 tokens**; CPU two threads, greedy `num_beams=1`, deterministic `do_sample=False`, **max_new_tokens=96**, one generation per sentence. Report exact resolved revision if available; otherwise explicitly state model revision *not pinned*.
- REBEL's published special tokens `<triplet>`, `<subj>`, `<obj>` are parsed into raw head–predicate–tail outputs. Explicit fixed **16-property** REBEL relation-name→DocRED Wikidata map; unrecognized relations are retained in raw logs but cannot score as known positive. Preserve two views: **raw mapped proposals** and **hard source-surface-anchored mapped proposals**; anchoring requires both head and tail names literally present in the same original sentence. The latter will have lower recall for pronouns, abbreviations and cross-sentence facts by design.
- Baseline: V8.8 regex mention + typed cue extraction run on the exact same selected sentence set, not its original full-document score (5/386 is historical context **not directly comparable**).
- Metrics: number of annotated gold-positive 16-ontology triples in the 20 docs; positive-gold exact head alias, relation ID, directed tail alias recovery for regex, raw REBEL and anchored REBEL; gold supporting-sentence overlap; candidate mapping/anchoring rejection counts, source SHA and sentence offset invariant; 3,000-source-document paired bootstrap 95% CIs; model-load time, total inference, mean/p95 per document. Emit raw per-doc JSONL, results JSON, and **unreviewed** human-label queue with no invented judgement.

## Interpretation safeguards

The sample contains only source documents selected to have known-positive annotated triples. **Do not treat unannotated emitted triples as false or calculate open-world precision**; DocRED label coverage is incomplete. Exact-head and tail name matching is strict and may miss correct aliases. Document-level relations requiring coreference/indirect reasoning will be missed by this six-sentence, single-sentence anchoring pilot. REBEL generator predictions have no calibrated contradiction or abstention semantics; dropping an unsupported candidate cannot prove it false.

No MuSiQue 3-/4-hop retrieval, final answer generation, official IRCoT/HippoRAG2 comparison, sealed evaluation, PGER novelty or NeurIPS-ready performance is established by this standalone pilot. Promotion criterion: **evidence of substantially better naturally expressed relations, with actual source grounding and acceptable CPU cost**; if poor, reject deployment and analyze model mapping and window/citation failures before integrating into PGER.

## One-time commands

```bash
git clone --single-branch --branch v89-rebel-generator-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install 'numpy>=1.24,<3' 'transformers==4.52.4' 'safetensors'
python -m pip install 'torch>=2.3,<3' --index-url https://download.pytorch.org/whl/cpu
python -m unittest discover -s . -p 'test_pger_v89.py' -v
python benchmark_v89.py smoke
python -u benchmark_v89.py run --out results-v89
```

No scheduled run. Preserve successes, regressions and failures.
