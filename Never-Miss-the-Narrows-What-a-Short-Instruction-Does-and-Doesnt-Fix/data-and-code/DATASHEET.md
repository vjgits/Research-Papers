# Datasheet: ICP v0.5 scenario set and outputs

Structure follows "Datasheets for Datasets" (Gebru et al.).

## Motivation

The dataset tests whether AI planning assistants preserve informed choice. Do they raise decision-critical information at the moment of decision, avoid silent tradeoffs, resurface self-recorded deadlines, and flag idle time, without over-intervening when nothing is at stake?

It was created by Vijay Suresh, an independent researcher, with no external funding.

## Composition

There are 36 scenarios:

| Stratum | Count | Description |
|---|---|---|
| Long-horizon, triggered | 6 | 120–248 messages each, with six live decision points |
| Long-horizon, control | 2 | |
| Real-case-derived | 10 | Decision structures from documented AI-travel incidents |
| Constructed | 11 | |
| Short controls | 7 | |

- **Long conversations** have scripted ("frozen") middles: hand-written key turns plus template-generated trip chatter, identical across models and arms. The middles are 6–11k tokens long.
- **Gold labels** give per-decision-point checklists for each metric (SCD, STR, DR, AoC, ISD, RoC, DCC, NAG, OVER).
- **Facts** are re-verified against official sources, with access dates (`FACT_LEDGER_v05.csv`).
- **Outputs** are 1,595 decision-point replies from 7 models × 3 arms. 1,530 were judged; the exclusions are logged.
- **Personal data:** none. All traveler personas are fictional. The motivating real conversation is excluded.

## Collection process

- Replies were generated via OpenRouter between 24 and 25 October 2026.
- Settings: reasoning effort "low", no tools, provider data collection denied.
- Every call records the model, parameters, hashes of the system prompt and frozen history, cost and timestamp.

## Labelling

- **Judges:** three LLM judges from different model families, using per-field yes/no checklists, with majority vote. Inter-judge κ is reported per field (0.12–0.95).
- **Dry run (v0.6-dry):** two AI readers and an AI grader.
- **Human annotation:** pending; the pack and guide are included.

All current labels are model-generated and should be treated as supplementary.

## Known limitations

- Six triggered long cases, one trial each.
- Travel domain only.
- Decision points are staged at the moments the protocol targets.
- No strong-prompt baselines.
- The low-agreement fields (over-intervention, silent cut, nagging) should not be used without human calibration.

## Uses

**Intended uses:**
- evaluating disclosure timing and intervention costs in planning assistants;
- replicating or extending the protocol study;
- calibrating LLM judges against human labels.

**Not intended for:** training models to game the metrics, or claims about live multi-day agents.

## Distribution and maintenance

- Released on Zenodo (DOI https://doi.org/10.5281/zenodo.23721946) with the paper, under CC BY 4.0 (paper and data) and MIT (code).
- Maintained by the author. Later versions (v0.7 onward) will be released as separate, versioned packages and never merged into this one.
