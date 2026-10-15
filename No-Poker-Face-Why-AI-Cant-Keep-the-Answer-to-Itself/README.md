# No Poker Face: Why AI Can't Keep the Answer to Itself

Do AI models write practice questions that give away their own answers, and does knowing the learner (goal, weak areas, results, claims of mastery) make that worse?

**Paper:** *No Poker Face: Why AI Can't Keep the Answer to Itself*, v1.1 (15 Oct 2026), preprint on Zenodo:
**[doi.org/10.5281/zenodo.23398343](https://doi.org/10.5281/zenodo.23398343)**, with the full data and code release.

**Key results:**

- **Pre-registered main study** (168 sessions, 11,760 questions). Both confirmatory nulls. Writers did not ease
  after scripted failure (−3.4 pts, 95% CI −7.2 to +0.4), and none declared a learner ready on a claimed mastery
  (0/24 vs 0/24).
- **Leakage.** A solver with no study material answered about half of invented-subject questions correctly
  (chance 25%).
- **Confirmatory follow-up** (112 sessions, new subjects).
  - "Harder" requests raise no-material accuracy: +5.9 pts [1.9, 9.5], p = 0.002.
  - Telling writers to match distractor length to the key removes the longest-option cue (37.6% → 25.6%) but not the
    leakage (+2.2 pts, p = 0.95).

**Pre-registrations (OSF):**

- main study: [osf.io/uya5q](https://osf.io/uya5q)
- Addendum 1, Gemini writer arm: [osf.io/93vpn](https://osf.io/93vpn)
- Addendum 2, confirmatory follow-up: [osf.io/3z64e](https://osf.io/3z64e)
- associated project: [osf.io/y5vcu](https://osf.io/y5vcu)

**Contents:**

- `paper/v1.1/`: the paper (PDF and its Markdown source); `paper/fig/`: figures
- `results/`: analysis outputs for the main run, the Gemini arm, the follow-up, and the labelled exploratory
  additions
- `preregistration/`: the registered documents (v0.2 = osf.io/uya5q; Addenda 1 and 2)
- Frozen code, one folder per registration:
  - `code/no-poker-face/`: main run, commit `a53ed958`
  - `code-gemini-arm/no-poker-face/`: Gemini writer arm, commit `b3f473b`
  - `code-followup/no-poker-face/`: follow-up, commit `af87a27`
- `docs/findings-paper1.md`: full execution log, including every AI error and who caught it (account details
  removed)

Transcripts, item-level solver outputs and per-call cost ledgers are in the data zip on Zenodo.

No real certification exam content is used. Author: Vijay Suresh · ORCID 0009-0004-1471-0561
