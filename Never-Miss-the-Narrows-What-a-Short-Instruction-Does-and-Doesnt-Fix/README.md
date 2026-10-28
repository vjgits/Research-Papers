# Never Miss the Narrows: What a Short Instruction Does and Doesn't Fix When AI Assistants Plan Trips Over Long Conversations

AI travel assistants can say something important once, early in a long conversation, and then fail to raise it again when the traveler actually decides. This project defines that goal as **informed-choice preservation**, proposes a short drop-in instruction block (the "Never Miss the Narrows" protocol), and tests what it fixes and what it costs.

**Paper:** *Never Miss the Narrows*, working paper v4.3 (28 Oct 2026). It is a preprint on Zenodo, deposited together with the full data and code package:
**[doi.org/10.5281/zenodo.23721946](https://doi.org/10.5281/zenodo.23721946)**

**Key results** (preregistered; 7 models × 3 arms × 36 scenarios; all labels from AI models, human validation in progress):

- **Reader outcome.** AI "travelers" reading a reply cold understood more after protocol replies: 0.42 → 0.59 points (+0.17, 95% CI 0.12–0.23), positive in all six long cases.
  - Deadlines the assistant recorded itself: 58% → 71% of readers.
  - Spare time in the plan: 6% → 38%.
- **Judge composite.** Preregistered: 0.49 → 0.76 (+0.27). Part of the gap with the reader outcome is rubric echo.
- **Mentioning is not informing.** Models mentioned the must-see far more often, but only 30% of readers could say why it mattered.
- **Costs.** Judges rated substantial over-intervention up from 10% to 26%, but AI readers barely felt it. Untargeted critical facts were disclosed slightly less often. Replies grew 11–14% longer.
- **Explicit memory.** A model-written JSON memory added little (+0.03 to +0.04) for about three times the compute.

## Contents

- `paper/v4.3/`: the paper (PDF).
- `data-and-code/`: the public package, identical to the one on Zenodo:
  - the 36 scenarios, gold labels and fact ledger;
  - model configurations and run manifests;
  - every model reply;
  - judge prompts and labels;
  - scoring, analysis and figure scripts;
  - mock tests;
  - the blinded human-annotation pack and guide;
  - the v0.6-dry reader check;
  - the preregistration and independent pre-data review (public copies).

  See `data-and-code/README.md` and `data-and-code/DATASHEET.md`.

## Reproduce

From `data-and-code/`:

```bash
python3 tests/validate_v05.py           # dataset checks (356/356)
python3 tests/test_run_v05_mock.py      # runner mock tests (31/31)
python3 tests/test_pipeline_v05_mock.py # end-to-end mock pipeline
python3 scoring/analysis_v05.py --responses outputs/main/responses.jsonl \
  --labels outputs/judge_main/labels_majority.csv --label-source judge \
  --labels-dir outputs/judge_main --out <your output folder>
```

The analysis reproduces the published results exactly from the released files.

## Notes

- **Cost fields removed.** Per-call cost fields and the provider price snapshot were removed from the public package. The preregistration and review are public copies with budget amounts redacted.
- **Private material.** The private conversation that motivated this work, and its replay outputs, are not included.
- **Licences.** Paper and data: CC BY 4.0. Code: MIT.

Author: Vijay Suresh · ORCID 0009-0004-1471-0561
