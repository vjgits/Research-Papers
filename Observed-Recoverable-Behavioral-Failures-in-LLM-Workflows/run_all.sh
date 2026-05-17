#!/usr/bin/env bash
# run_all.sh — one-shot orchestration of the RBF multi-model pilot.
#
# Runs: env check -> deps -> experiment -> scoring -> cross-model analysis.
# Does NOT do: paper v1.9 edit (manual via Claude Code), git push (manual).
#
# Usage:
#   export ANTHROPIC_API_KEY=...
#   export OPENAI_API_KEY=...
#   export GEMINI_API_KEY=...
#   export ANTHROPIC_SONNET_MODEL="<current-sonnet-id>"
#   export ANTHROPIC_OPUS_MODEL="<current-opus-id>"
#   export OPENAI_MODEL="<current-gpt-id>"
#   export GEMINI_MODEL="<current-gemini-id>"
#   ./run_all.sh
#
# Any model env var that is empty will cause that provider to be skipped with
# a noted exclusion. Set at least one of the three families.

set -u
set -o pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "==> Repo root: $REPO_ROOT"

# ---------- env check ----------
echo "==> Checking API keys..."
have_anthropic=0; have_openai=0; have_google=0
[ -n "${ANTHROPIC_API_KEY:-}" ] && have_anthropic=1
[ -n "${OPENAI_API_KEY:-}" ]    && have_openai=1
[ -n "${GEMINI_API_KEY:-}" ]    && have_google=1

if [ "$have_anthropic" -eq 0 ] && [ "$have_openai" -eq 0 ] && [ "$have_google" -eq 0 ]; then
    echo "ERROR: no API keys set. Export at least one of ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY."
    exit 1
fi

# ---------- model identifiers ----------
ANTH_SONNET="${ANTHROPIC_SONNET_MODEL:-}"
ANTH_OPUS="${ANTHROPIC_OPUS_MODEL:-}"
OAI="${OPENAI_MODEL:-}"
GEM="${GEMINI_MODEL:-}"

if [ "$have_anthropic" -eq 1 ] && [ -z "$ANTH_SONNET" ] && [ -z "$ANTH_OPUS" ]; then
    echo "ERROR: ANTHROPIC_API_KEY is set but neither ANTHROPIC_SONNET_MODEL nor ANTHROPIC_OPUS_MODEL is set."
    echo "       Export at least one. Example: export ANTHROPIC_SONNET_MODEL=claude-sonnet-4-5-...."
    exit 1
fi
if [ "$have_openai" -eq 1 ] && [ -z "$OAI" ]; then
    echo "ERROR: OPENAI_API_KEY set but OPENAI_MODEL not set. Example: export OPENAI_MODEL=gpt-...."
    exit 1
fi
if [ "$have_google" -eq 1 ] && [ -z "$GEM" ]; then
    echo "ERROR: GEMINI_API_KEY set but GEMINI_MODEL not set. Example: export GEMINI_MODEL=gemini-...."
    exit 1
fi

# Build --models argument
models_args=()
[ -n "$ANTH_SONNET" ] && models_args+=("anthropic:$ANTH_SONNET")
[ -n "$ANTH_OPUS" ]   && models_args+=("anthropic:$ANTH_OPUS")
[ -n "$OAI" ]         && models_args+=("openai:$OAI")
[ -n "$GEM" ]         && models_args+=("google:$GEM")

echo "==> Will test: ${models_args[*]}"

# ---------- install deps ----------
echo "==> Installing Python deps..."
pip3 install -q -r experiment_pack/requirements.txt
pip3 install -q matplotlib  # for the comparison plot

# ---------- run experiment ----------
mkdir -p experiment_pack/results
echo "==> Running multi-model experiment..."
python3 experiment_pack/run_eval.py \
    --models "${models_args[@]}" \
    --tasks  experiment_pack/tasks/evaluation_tasks.jsonl \
    --out    experiment_pack/results/raw_outputs.jsonl
echo "==> raw_outputs.jsonl produced"

# ---------- score ----------
echo "==> Scoring outputs..."
python3 experiment_pack/score_results.py \
    --raw    experiment_pack/results/raw_outputs.jsonl \
    --tasks  experiment_pack/tasks/evaluation_tasks.jsonl \
    --out    experiment_pack/results/scored_results.csv
echo "==> scored_results.csv produced"

# ---------- compare ----------
echo "==> Cross-model comparison..."
python3 analysis/compare_models.py \
    --scored experiment_pack/results/scored_results.csv \
    --out    experiment_pack/results/comparison.csv \
    --plot   experiment_pack/results/comparison.png
echo "==> comparison.csv and comparison.png produced"

# ---------- summary ----------
echo
echo "==== SUMMARY ===="
echo "Raw outputs:   experiment_pack/results/raw_outputs.jsonl"
echo "Scored:        experiment_pack/results/scored_results.csv"
echo "Comparison:    experiment_pack/results/comparison.csv"
echo "Plot:          experiment_pack/results/comparison.png"
echo
echo "Head of comparison.csv:"
head -n 12 experiment_pack/results/comparison.csv
echo
echo "Next: open paper/paper_v1.8.tex, save as paper_v1.9.tex,"
echo "      insert the Multi-Model Pilot Results section using comparison.csv,"
echo "      embed comparison.png, compile, and push to GitHub."
echo "See HANDOFF_PROMPT.md for the exact edit checklist."
