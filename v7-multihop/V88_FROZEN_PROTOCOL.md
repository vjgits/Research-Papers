# PGER V8.8 — Frozen Source-First Natural-Document Relation Probe

**Date:** 2026-10-27 Pacific (run can be 2026-10-28 UTC).
**Branch:** `v88-source-first-relation-2026-10-27`, forked from `v87-natural-relation-probe-2026-10-27`. Main is untouched. No paid APIs, reviewer agents, cron, or scheduled scans.

## Scientific question

Can inexpensive off-the-shelf named-entity recognition (spaCy), local typed relation cues and a frozen NLI accept/reject verifier recover correct *subject–predicate–object* relationships from **raw natural sentences without gold entity-pair inputs**? Why did V8.7 (provided gold entity pairs) only identify 25/100 natural-DocRED positives correctly?

This is a narrow extractor diagnostic, **NOT** full PGER retrieval, a new neural model, official DocRED leaderboard metric, an open-world precision estimate, an end-to-end QA reader, a four/eight-hop reasoning solution, or a novel method. Relation extraction via NER, cue heuristics, NLI, and sentence-level provenance are all preexisting techniques.

## Audited disjoint corpus

- Use the official DocRED validation `dev.json.gz`, source SHA256 `6ae4d7f5b0b9d2cbe74b9634ed43b35b7cb5b7c0dc3a16226dbe343139a4ae05`, 998 source documents.
- Deterministically select **60 eligible gold-positive documents**, SHA256 sort key `v88-sealed-v1:20261027:index:title`, requiring at least one annotated relationship from V8.7's original 16-class frozen ontology. These are **gold-selected positives**, not randomly sampled all documents; don't use unannotated pairs as negative.
- Explicitly exclude the **54 DocRED document IDs examined in V8.7**. The V8.8 selected source IDs SHA256 are `2e4e4afef8efebc40d6fabc40f02309ce7ef0e90612d30d71e3481df53fe8b85`. This is an additional public-validation development cohort, not a sealed independent final test.
- The **regex-only 60-document baseline was already inspected on this cohort before freezing the full spaCy+NLI comparison** and achieved 5/386 exact annotated triples. Do not subsequently claim the entire cohort was unseen at method specification. No further threshold tuning permitted after full methods run.

## Predeclared pipeline and arms

1. `regex`: surface capitalized-span proposals; locality-based directed entity-pair candidates, fixed cap 300/doc, with a one-sentence neighborhood. Predicate cue patterns for 16 ontology relations and negation/competing-cue guards. Each proposed triple includes exact sentence ID, quote, character offsets, and SHA256.
2. `spacy`: pre-trained `en_core_web_sm` NER; the **identical** pair-proposal logic, identical local cue extractor and caps. No gold DocRED `vertexSet`, entity mentions or annotated relations are provided to extraction.
3. `regex_nli`, `spacy_nli`: run the same pinned `cross-encoder/nli-MiniLM2-L6-H768` revision `9aa22b250d25a10ac39ab4a6b2bc28213507cb0c` on **up to first 48 proposed triples per document**, one NLI pair per proposed triple. Three-way label order contradiction/entailment/neutral; accept only P(entailment) >= 0.70 and margin >= 0.10. NLI can only **filter** proposed triples, not generate missing relations. Does not validate worldly truth.
4. No threshold adaptation, no fine-tuning and no paid model API. Should the spaCy model or NLI fail to load, report incomplete; do **not** silently substitute regex as the spaCy comparator. The baseline-only `--no-spacy --no-nli` diagnostic is distinct.

The benchmark code must extract both arms' mentions, pair proposals, triples, and NLI decisions **before reading any gold relation, gold entity, or gold evidence label** inside scoring. Labels may only select the **document-positive** evaluation cohort and calculate post-hoc accuracy.

## Evaluation

- Count gold annotated ontology triples, gold head+tail exact-name detection, gold matching candidate pairs, correctly typed gold triples recovered (with exact-name head/tail, relation and direction), and correctly typed triples whose citation sentence matches annotated evidence.
- Record total proposed mentions, pairs, triples, exact source-offset/hash validity, NLI calls and CPU time; calculate **document-cluster bootstrap 95% intervals**, 3,000 resamples seeded 20261027, for known-positive triple recall. Compare NLI-filtered versus unfiltered with paired examples.
- **Never** label the ratio of detected annotated triples to emitted triples `precision`: DocRED incomplete annotations mean unlabelled proposed triples may be correct. This is *known-positive recall* and citation-overlap only. Full semantic entailment is not established by matching a quote, and exact alias equality is a strict metric.
- Do not compare number of 2-, 3-, 4-annotated supporting documents directly to true logical hop count. No 4+ source chain improvement is established by this DocRED study.

## Fixed run

```bash
git clone --single-branch --branch v88-source-first-relation-2026-10-27 https://github.com/vjgits/Research-Papers.git
cd Research-Papers/v7-multihop
python -m pip install spacy==3.8.11 torch sentence-transformers
python -m spacy download en_core_web_sm
python -m unittest discover -s . -p 'test_pger_v88.py' -v
python benchmark_v88_docred.py smoke
python benchmark_v88_docred.py run --docs 60 --out results-v88
```

The GitHub Actions job is **one-time branch push or manually dispatched**, never cron. Preserve all failures and per-document records in artifacts; no SOTA claim. Prior-art context: DocRED (Yao et al., ACL 2019), spaCy NER, cross-encoder NLI, REBEL. Standard primitives are not original PGER work.

## Advancement gate

Proceed to a more sophisticated *open-ended relation extractor* or source-gap ranker only if real natural-data identification/recall improves substantially, with acceptable CPU cost and no semantic-scope leakage. If NLI mostly filters false or true positives without meaningful net recovery, report as a negative result and keep V7.1 fast plus V8.5 CE as existing retrieval comparators. Independent manual relation annotation is still needed before NeurIPS originality claims.
