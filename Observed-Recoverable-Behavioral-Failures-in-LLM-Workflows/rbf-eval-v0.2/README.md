# RBF-Eval v0.2

RBF-Eval is a benchmark scaffold for measuring recoverable behavioral failures (RBFs) in LLM workflows: cases where a model fails on a first pass but succeeds after a retry or verification prompt that introduces no new substantive information.

This companion package includes:

- `paper/` - the current manuscript PDF
- `tasks/` - JSONL benchmark items
- `prompts/` - first-pass, null-retry, generic-retry, and verification-retry templates
- `rbf_eval/` - Python package scaffold for schemas, running, scoring, metrics, and summaries
- `docs/` - taxonomy, schema reference, annotation rubric, runbook, and contribution guide
- `results/` - example raw-output and scored-result files plus a results summary template
- `notebooks/` - analysis notebook placeholder

## Basic flow

1. Select a model and task file.
2. Run first-pass prompts.
3. Route failed items to null-retry, generic-retry, or verification-retry conditions.
4. Score deterministic checks and annotate human-judged items.
5. Report first-pass success, retry success, recoverability gap, and directed recoverability lift.

This package is a scaffold and pilot release, not a finished large-scale benchmark.
