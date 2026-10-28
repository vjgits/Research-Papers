# Never Miss the Narrows: release package v0.5.3

Data, code and outputs for the working paper *"Never Miss the Narrows: What a Short Instruction Does and Doesn't Fix When AI Assistants Plan Trips Over Long Conversations"* (Vijay Suresh, 2026; `docs/Never_Miss_the_Narrows_v4.3.pdf`).

**Status.** All outcome labels are from AI models (three LLM judges; two AI readers and an AI grader in the dry run). Human annotation is in progress. The arm key for the blinded human pack is withheld until annotation is complete.

## What's here

| Path | Contents |
|---|---|
| `docs/` | Paper v4.3, preregistration with deviation log (v0.5.1) and the independent pre-data review (public copies, with budget amounts redacted), decision-outcome dry-run report, prior-art sweep |
| `data/` | 36 scenarios (`cases_v05.jsonl`), gold labels (`gold_v05.jsonl`), fact ledger with official sources and access dates, run manifests |
| `src/`, `run_v05.py` | Scenario builders, arms (baseline / protocol / protocol + state), runner and engine (hard cost caps, no automatic retries) |
| `models_v05.json`, `models_v053_sens.json` | Model and generation settings. The original price snapshot is not included: recreate it with `python3 tools/make_pricing_snapshot.py` before any paid re-run |
| `scoring/` | Judges, analysis, screening, human-pack builder, human-agreement script, dry-run reader and analysis |
| `tests/` | Dataset validation (356 checks), runner mock test, pipeline mock test |
| `outputs/main/` | Every model reply in the main run (755 of 756 runs), with provenance |
| `outputs/judge_main/`, `outputs/analysis_main/` | Per-judge labels, majority labels, leave-one-judge-out labels, inter-judge agreement, analysis |
| `outputs/sens_v053/`, `judge_sens_v053/`, `analysis_sens_v053/`, `sens_combined/` | v0.5.3 sensitivity re-run (Sonnet, memory arm) |
| `outputs/dryrun_v06/`, `analysis_dryrun_v06/` | v0.6-dry decision-outcome check (AI readers + grader) |
| `outputs/smoke/`, `outputs/pilot/` | Smoke and pilot runs (pilot not analysed) |
| `outputs/human_pack_v05/` | Blinded, paired annotation pack (192 items, two annotator files) and guide |
| `outputs/figures/` | Paper figures |

## Not included

- The private motivating conversation and its counterfactual replay (personal data).
- The arm key for the human pack (released after annotation).
- Account-level budget files and run logs.

## Versions

Results from different versions are never pooled:

| Version | What it is |
|---|---|
| v0.5.2 | The preregistered main run |
| v0.5.3 | Sensitivity re-run |
| v0.6-dry | Decision-outcome dry run |

## Reproduce

```
pip install requests markdown playwright matplotlib --break-system-packages
python3 tests/validate_v05.py                      # dataset checks
python3 tests/test_run_v05_mock.py                 # runner, no API calls
python3 scoring/analysis_v05.py --help             # re-run the analysis on outputs/judge_main
export OPENROUTER_API_KEY=...                      # only for new live runs
python3 run_v05.py --phase smoke --max-cost-usd <your cap> --global-cap <your total cap>
```

## Licence

- Code: MIT.
- Data, outputs and documents: CC BY 4.0.

Scenario facts cite their official sources in `data/FACT_LEDGER_v05.csv`. Model outputs are provided for research use.

## Cite

Suresh, V. (2026). *Never Miss the Narrows: What a Short Instruction Does and Doesn't Fix When AI Assistants Plan Trips Over Long Conversations.* Working paper v4.3. ORCID 0009-0004-1471-0561. DOI: https://doi.org/10.5281/zenodo.23721946

## Public-package notes (27 Oct 2026)

- **Cost fields removed.** Per-call cost and spend fields were removed from the released outputs, and the provider price snapshot and cost projections are not included. Nothing else in the data changed: re-running `scoring/analysis_v05.py` on the released files reproduces the published results exactly.
- **Price snapshot for re-runs.** To re-run paid phases, first recreate the snapshot with `python3 tools/make_pricing_snapshot.py`. The mock tests use a placeholder snapshot (made-up prices) that is created and deleted automatically.
- **Redacted documents.** The preregistration and pre-data review are public copies with budget amounts redacted. The frozen originals, and their sha256 values, are kept by the author.
- **Private material.** The private motivating conversation and its replay outputs are not included.
