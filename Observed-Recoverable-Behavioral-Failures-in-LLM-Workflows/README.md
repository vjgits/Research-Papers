# Observed Recoverable Behavioral Failures in LLM Workflows

A multi-session cross-platform case study, retry-probe pilot, and multi-model evaluation protocol.

**Author:** Vijay Suresh
**Current version:** 1.9 (May 2026) — supersedes v1.8
**Status:** Working paper (preprint stage). Pilot results reported in the paper are exploratory.

**v1.9 changes over v1.8:**
- Adds §8 "Intra-Vendor Pilot Results: Sonnet, Opus, and Haiku on the Experiment Pack" with real results from running the ten-task experiment pack against three Anthropic frontier models. Results are intra-vendor only; cross-vendor extension is deferred to future work.
- Includes the per-(model, category) comparison table and grouped bar chart (`paper/figures/comparison.png`).
- Notes a meta-finding: the RETRY_PROXY deterministic rubric uniformly under-scored all three models on retrieval-strategy responses that used different vocabulary than the required terms — useful evidence for the RFI mode itself.
- Raw outputs (`experiment_pack/results/raw_outputs.jsonl`) and scored results are committed; comparison.csv and the plot are reproducible from them.

**v1.8 changes over v1.7:**
- Restored the *p*<sub>1</sub> / *p*<sub>r</sub> / *S*<sub>1</sub> / *S*<sub>r</sub> convention throughout §3.1 and Table 1 (v1.7 had a duplicate-definition / undefined-*p*<sub>0</sub> bug).
- Strengthened §2.6 (long-horizon agent reliability and human-AI workflow reliability).
- Added §5.0 — explicit note on mode-overlap and granularity, with the rationale for keeping sixteen modes separate at this stage.
- Cleaned up Unicode subscript rendering (no more black-square missing-glyph artifacts).
- Restored the table of contents on both PDF and LaTeX versions (the previous v1.8 build had dropped it).
- Restored full per-mode depth in §5 — each of the sixteen modes has a six-paragraph treatment (definition / observed pattern / why it matters / differentiation / detection / mitigation) matching v1.7's content depth.

Both a reportlab-generated PDF (28 pages) and a LaTeX source + LaTeX-compiled PDF (28 pages) are included. Mode content lives in `paper/mode_content.py` so both generators share a single source of truth.

---

## What this paper studies

The paper introduces *recoverable behavioral failures* (RBFs): cases where a large language model appears capable of completing a task but fails to exercise that capability on the first pass, and then succeeds on a brief retry that introduces no new substantive information. The paper develops a sixteen-mode taxonomy, reports a retry-probe pilot, and specifies a controlled multi-model evaluation protocol.

The pilot finds, on a fifteen-item heterogeneous retrieval task: first-pass resolution 12 / 15 = 80% (Wilson 95% CI [54.8%, 93.0%]); after-retry resolution 15 / 15 = 100%; recoverability gap of +20 percentage points; Fisher exact test associating first-pass failure with one item structural class (two-sided *p* = 0.0022, exact, *n* = 15). The pilot is small and exploratory; the multi-model protocol below is the appropriate vehicle for population-level estimation and cross-model comparison.

## Repository contents

```
.
├── paper/
│   ├── paper_v1.9.pdf                       Current manuscript (30 pp, with multi-model results)
│   ├── paper_v1.9.tex                       LaTeX source for v1.9 (arXiv-submittable)
│   ├── figures/comparison.png               Multi-model pass-rate plot (embedded in §8)
│   ├── paper_v1.8.pdf                       Previous version, retained
│   ├── paper_v1.8.tex                       Previous LaTeX source
│   ├── paper_v1.8_latex_compiled.pdf        Previous LaTeX-compiled PDF
│   ├── mode_content.py                      Shared source of truth for §5 mode treatments
│   ├── generate_paper_v1_8.py               Reportlab generator (imports mode_content)
│   ├── generate_paper_v1_8_tex.py           LaTeX generator (imports mode_content)
│   ├── paper_v1.7.pdf                       Older version, retained for reference
│   └── experiment_pack_v1.0.pdf             Companion experiment-pack write-up
├── experiment_pack/
│   ├── README.md                            Original pack instructions
│   ├── requirements.txt                     Python dependencies
│   ├── run_eval.py                          Runs items against OpenAI, Anthropic, Gemini APIs
│   ├── score_results.py                     Deterministic scoring on raw outputs
│   ├── tasks/
│   │   └── evaluation_tasks.jsonl           10 items across QI, PPG, EBC, ACM, RETRY_PROXY
│   └── results/                             (empty — populated when you run the experiment)
├── analysis/
│   └── compare_models.py                    Cross-model comparison from scored results
├── CITATION.cff                             Citation metadata
├── LICENSE                                  CC-BY-4.0 for paper text; MIT for code
└── README.md                                This file
```

## Running the multi-model experiment

The experiment pack administers ten items across five RBF-proxy categories (QI, PPG, EBC, ACM, RETRY_PROXY) against any combination of OpenAI, Anthropic, and Google APIs.

**Requirements:**
- Python 3.10+
- API access to at least one of: OpenAI, Anthropic, Google Gemini

**Setup:**

```bash
cd experiment_pack
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."
```

**Run:**

```bash
# Pick the actual model identifiers enabled in each account.
# Examples below use placeholder names; update to your current model strings.

python run_eval.py \
    --models openai:gpt-5.5 anthropic:claude-sonnet-4-5 anthropic:claude-opus-4-7 google:gemini-2.5-pro \
    --tasks tasks/evaluation_tasks.jsonl \
    --out results/raw_outputs.jsonl
```

**Score:**

```bash
python score_results.py \
    --raw results/raw_outputs.jsonl \
    --tasks tasks/evaluation_tasks.jsonl \
    --out results/scored_results.csv
```

**Compare models across categories:**

```bash
cd ../analysis
python compare_models.py \
    --scored ../experiment_pack/results/scored_results.csv \
    --out ../experiment_pack/results/comparison.csv \
    --plot ../experiment_pack/results/comparison.png
```

The analysis script produces, for each (model, category) pair: number of items, pass rate, and 95% Wilson confidence interval. It also produces a grouped bar chart of pass rates across models for each category.

## Important caveats

- The pack contains ten items across five categories (two per category). Results from this pack should be reported as *pilot* evidence, not as model-comparison estimates.
- Model identifiers in `run_eval.py` are placeholders that need updating to currently-enabled models in your accounts.
- The QI scoring includes hard-coded expected numeric values for the two QI tasks. The PPG, EBC, ACM, and RETRY_PROXY tasks use deterministic forbidden-term and required-term checks.
- For population-level estimation, scale the item set following the sample-size guidance in §9.5 of the paper.

## Citation

If you use the taxonomy, the retry-probe construct, or the experiment pack, please cite as:

```
Suresh, V. (2026). Observed Recoverable Behavioral Failure Modes in LLM Workflows:
A Multi-Session Cross-Platform Case Study, Retry-Probe Pilot, and Multi-Model
Evaluation Protocol. Working paper, v1.9.
```

A `CITATION.cff` file is included for automated tooling.

## License

- Paper text and figures: CC-BY-4.0
- Code (experiment pack, analysis): MIT

## Status and contact

This is a working paper. The pilot is reported as exploratory. The multi-model protocol is offered as a planned replication; results from running the pack are not included in the paper.

Contributions and replications welcome. Please open an issue or pull request.
