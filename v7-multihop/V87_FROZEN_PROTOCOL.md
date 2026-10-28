# PGER V8.7 — Frozen Natural-Document Relation Probe

**Frozen before first DocRED run:** 2026-10-27 Pacific; branch `v87-natural-relation-probe-2026-10-27` separate from `main`. No scheduled task, reviewers, paid APIs or model fine-tuning.

## Primary research question

Can a pre-trained, frozen natural-language inference model identify the relationship between *a supplied pair of human-annotated entities* in a naturally written Wikipedia document, and can combining evidence from two source sentences outperform selecting a single sentence at **exactly the same NLI model-call budget**?

**This is not full open-ended relation extraction**: the subject and object entity identities and mentions are provided by the human-annotated DocRED data; the algorithm must select a relation from an explicit fixed ontology of 16 Wikidata properties. **No gold relation ID or gold evidence sentence ID enters model inference, candidate-window selection or ranking.** Gold labels are read only to select the positive relation-annotated evaluation cohort and to measure accuracy afterward. Annotations may be incomplete; unannotated pairs are NOT treated as negatives. Therefore **open-world relation precision, contradiction/neutral rates, and extraction recall on all possible relations are NOT assessed**.

## Data and locked cohort

- Official source: `thunlp/docred` validation split converted to Parquet, downloaded from Hugging Face dataset viewer API. Record SHA256 hash for every downloaded source file.
- Positive entity-pair cohort: deterministic SHA256 sort by title and row position with seed `20261027`, up to first **100** eligible positive annotated entity pairs from at most 95 distinct documents; at most two positive pairs per document; exact size reported.
- Only relation IDs in **P19 P20 P27 P17 P131 P159 P57 P50 P26 P36 P108 P69 P40 P22 P25 P161** are tested. Ontology and English hypotheses locked in `pger_v87_core.py`. This is a subset of DocRED relations and cannot be generalized to all properties.
- No train set, fine-tuning, or supervised threshold selection. This is **new benchmark family** to PGER but public validation, not a sealed final test. DocRED is human annotated, but the independent reliability of each gold claim is not re-adjudicated.

## Equal-NLI-budget arms

1. `single_lexical`: keyword relation heuristic on 4 top entity-conditioned source sentences.
2. `single_nli_ungated`: NLI scores all 16 relation hypotheses in the same 4 sentences, 64 premise/hypothesis pairs per example; choose max entailment score.
3. `single_nli_abstain`: same scores, P(entailment)>=0.70 and margin>=0.10 over contradiction and neutral, else abstain.
4. `bridge_lexical`: same lexical scoring on 4 source windows, each including at most two real source sentences if needed to join head/tail mentions.
5. `bridge_nli_ungated`: exactly 64 NLI pairs, matching single-window inference budget.
6. `bridge_nli_abstain`: same bridge scores with the identical fixed abstention threshold.

Both arms use a frozen pretrained open-weight model `cross-encoder/nli-MiniLM2-L6-H768` at revision `9aa22b250d25a10ac39ab4a6b2bc28213507cb0c` (three output classes C,E,N). Sentence IDs and source hashes are preserved; a valid source sentence is not necessarily a correct claim. Every sentence window is constructed using entity mentions and source text only, not annotated gold evidence sentence IDs.

## Primary and secondary metrics

- **Positive-pair relation recovery:** among gold-labeled entity pairs selected as described, fraction for which the top predicted property matches one of that pair's annotated relations. This is NOT DocRED official F1, nor real-world precision.
- Abstention coverage and accuracy among answered **on annotated-positive pairs** (selective accuracy only; unannotated source relations are not reliable negatives).
- Citation overlap with gold supporting sentence IDs, measured only after prediction; all/any evidence rates, and full/partial candidate evidence availability. Multi-sentence evidence labels are inherently challenging.
- Cluster bootstrap 95% intervals **resampling documents**, paired across methods with 4,000 draws; per-pair wins/losses; explicit subgroup counts.
- CPU model-init and per-example inference mean/p95, plus corpus download and index costs separately where applicable.
- Preserve error examples, relation-category confusion, source identifiers, and actual immutable relation-pair identifiers. Do not treat evaluation-text quotes as unrestricted for redistribution.

## Decision and limitations

A win on this DocRED positive-pair diagnostic is only evidence for a relation-conditioning component. It **does not establish** that PGER improves four-source MuSiQue Top 5, automatically proposes the right entity pair, detects false/contradictory claims, generates correct final answers or beats IRCoT/HippoRAG2. Those require separate sealed end-to-end evaluation against verified official competitors with equal compute and a fixed reader.

If NLI/bridges fail, report a negative result. If positive, the next step (not part of this frozen first run) is to add independently verified *natural negative/unanswerable controls* and derive missing subclaims from questions without gold relation-pair hints, then run a matched-budget 3/4+ source evaluation.

## Reproduce

```bash
git clone --single-branch --branch v87-natural-relation-probe-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install numpy pyarrow torch sentence-transformers
python -m unittest discover -s . -p 'test_pger_v87.py' -v
python benchmark_v87_docred.py smoke
python benchmark_v87_docred.py run --pairs 100 --windows 4 --out results-v87
```

Test stage has no costs. One-time Actions job is triggered by branch push; **no cron**.