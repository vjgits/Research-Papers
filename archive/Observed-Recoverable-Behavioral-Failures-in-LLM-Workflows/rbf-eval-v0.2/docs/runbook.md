# RBF-Eval Runbook

## 1. Prepare environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Run model calls

Use `rbf_eval.runner` or your own model wrapper to generate raw outputs in JSONL.

Expected raw-output fields:

- `id`
- `model`
- `condition`
- `prompt`
- `output`
- `timestamp`
- `metadata`

## 3. Score outputs

Run deterministic checks first, then human annotation for items marked `human_judged`.

## 4. Summarize metrics

Report first-pass success, null-retry success, verification-retry success, recoverability gap, directed recoverability lift, and per-mode pass/failure rates.
