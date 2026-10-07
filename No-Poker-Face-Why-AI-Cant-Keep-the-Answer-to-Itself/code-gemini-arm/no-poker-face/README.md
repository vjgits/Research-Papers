# No Poker Face — experiment code

Tests whether telling an AI model about the learner (goal, weak areas, error notes, emotion)
makes the practice questions it writes leak their answers.

## Run
```
pip install requests pandas numpy scipy statsmodels tabulate matplotlib
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=... ANTHROPIC_WORKSPACE_ID=...   # workspace ID only for account-level keys
python run.py estimate --phase calibration          # cost estimate, no calls
python run.py run --phase calibration --mock         # offline test; synthetic outputs, never data
python run.py run --phase calibration --budget 65    # real run; hard stop at the cap
python run.py secondary --phase calibration --budget 65
python run.py analyze --phase calibration
```
Every response is cached under `runs/<phase>/cache/` (re-runs are free) and every paid call is
logged with its cost in `runs/<phase>/ledger.jsonl`.

## Layout
- `data/` blueprint (fixed slots), synthetic learner profile and notes, invented-domain reference (Tessellate 4)
- `npf/config.py` models, prices, conditions, phases · `npf/prompts.py` all prompts
- `npf/pipeline.py` write → solve → code → features, plus secondary arms
- `npf/features.py` deterministic cue features · `npf/analysis.py` contrasts, GEE, cluster bootstrap, power simulation
- `npf/secondary_analysis.py` novelty / self-audit / pressure · `notebooks/analysis.ipynb`
- `runs/calibration/` the 2026-10-06 calibration: items, solver answers, judge codes, features, report, ledger, raw responses
- `docs/` plan PDF, findings log, ledger entry, figures

No real certification exam content is used. Model IDs and dates are recorded per call; rates are timestamps.

## Part B v2 (expanded sessions; built 2026-10-06/07)
```
python tests/test_v2.py                                            # 101 offline checks (mock; never data)
python run.py sessions --phase pilot_sessions_v2 --budget 25        # done 2026-10-07: $19.01, all checks pass
python run.py sessions --phase main_sessions --budget 270.99        # ONLY after the OSF pre-registration is posted
python docs/build_prereg.py                                        # rebuilds the pre-registration PDF
```
Keys from the environment: OPENAI_API_KEY, ANTHROPIC_API_KEY, ANTHROPIC_WORKSPACE_ID, GEMINI_API_KEY.
- `npf/sessions_v2.py` 7 session types, counterbalanced difficulty orders, learner panel, readiness turn, reply judge
- `npf/session_analysis_v2.py` pre-registered B1/B2 tests and secondary estimates · `npf/estimate_v2.py` cost from measured pilot costs
- `npf/pilot_v2_checks.py` feasibility checks fixed before the v2 pilot · `runs/pilot_sessions_v2/` the v2 pilot (not part of the main sample)
- The main run executes in three replicate waves; a wave starts only if its high-case cost fits in the remaining cap.
