# Altitude Lock: More How, Still No Why

**Unprompted framing critique in LLM assistants, measured twice**
Current version: **v2.5 · September 2026**

Every work request fixes choices nobody states — which outcome counts, over what
horizon, for whom, by what measure, and whether the task is worth doing at all.
None of them is false, so none trips a correction. This paper measures how often
an assistant names one of those choices **and still does the work**, across two
model generations three months apart on identical items.

- **Project folder:** [Altitude-Lock-More-How-Still-No-Why](./)
- **Current PDF v2.5:** [Download manuscript](./paper/v2.5/Altitude-Lock-More-How-Still-No-Why-v2.5.pdf)
- **Paper (all versions, concept DOI):** [doi:10.5281/zenodo.22847056](https://doi.org/10.5281/zenodo.22847056)
- **Data, code and figures (concept DOI):** [doi:10.5281/zenodo.22847075](https://doi.org/10.5281/zenodo.22847075)
- **arXiv:** pending endorsement


## Cite this work

Canonical citation DOI: **10.5281/zenodo.22847056**

```bibtex
@article{suresh2026altitudelock,
  title   = {Altitude Lock: More How, Still No Why},
  author  = {Suresh, Vijay},
  year    = {2026},
  version = {2.5},
  doi     = {10.5281/zenodo.22847056},
  url     = {https://doi.org/10.5281/zenodo.22847056}
}
```

**Keywords:** large language models; LLM evaluation; model behavior; problem framing;
premise critique; proactive assistance; LLM-as-a-judge; construct validity;
benchmarking; reproducible research.

## What it measures

Six framing dimensions — scope, horizon, unit of optimisation, metric, task
existence, means. A five-level scale separates a *horizontal* probe (what is
needed to execute the task) from a *vertical* one (what the task is for), and
records task completion independently of level. A response counts only if it
names the specific choice the item fixes **and** completes the requested work.

2,496 generated responses, 4,992 judgements, two frozen cross-family judges that
must agree, item-clustered bootstrap intervals throughout.

## Findings

- Unprompted surfacing rose **5.2% → 23.3%** between generations. Paired on
  identical items: +18.1 pp, 95% CI [+11.5, +25.4]; 33 improved, 4 worsened,
  23 unchanged; sign test p = 1.1e-6; cluster-robust logistic OR 5.5, p = 2.4e-8.
- **Read that with its spread.** The frontier panel ranges 12.5%–43.3%. The
  highest model supplies 46.4% of all frontier positives, and the leave-one-out
  rate is 16.7%. Dispersion between siblings of one generation exceeds the
  dispersion between generations.
- **The obvious intervention fails.** An arm whose prompt explicitly invited
  critique reached an asserting level in 52.7% of responses and completed the
  task in 0%. Framing engagement and task completion are separable, so an
  evaluation scoring critique alone can reverse intervention rankings.
- **One sentence beats a model generation.** Told to do the work *and* name one
  choice, surfacing rises to 53.1% within the prior generation, with completion
  rising too.
- **Task existence did not move**: 7.5% → 6.3%. The largest single-item reversal
  in the study is an existence item, EXI-03, at 62.5% → 0.0%.
- The direction survives every collapse rule: both judges 5.2 → 23.3, either
  judge 15.8 → 42.7, Claude alone 6.7 → 26.0, GPT alone 14.4 → 40.0.

## Reproducing

Everything is in the Zenodo data record. The offline analysis needs no API access
and no credentials:

```bash
unzip altitude-lock-v2.5-package.zip
python3 code/v21_analysis.py
```

`sha256sum -c SHA256SUMS` verifies the archive. Re-running generation or judging
needs API keys of your own; the harness plans and prices a run before spending.

Every number in the paper is computed by one statistics module and checked by a
build gate that refuses any figure not resolving to it.

## Limitations worth knowing before citing

- **No human has checked any label.** Every rate rests on two language models
  agreeing. A human-labelled subsample is the single most valuable addition this
  work could receive, and it does not exist yet.
- The two generations differ in provider-default inference behaviour as well as
  in weights, so this compares what a user gets out of the box, not matched
  inference budgets.
- Items, rubric and framework were written by one person.
- An ordering by altitude and an ordering by training-data prevalence predict the
  same six rates on this item set; nothing in this design separates them.

## Licence

Paper CC BY 4.0. In the data record, code is MIT and data and documentation are
CC BY 4.0.

The 60 loaded items are released for benchmark reuse. **Please do not train on
them** — doing so destroys their value as a measurement instrument for everyone,
including you.
