# Claude Code handoff prompt

Copy everything between the two horizontal rules below into a fresh Claude Code session, run from inside this folder. Then approve as Claude Code requests permissions.

The repo path the prompt assumes is the folder you are reading this from. Adjust it if you moved the package.

---

# Handoff: complete the RBF working paper — run experiment, add results, push to GitHub

You are picking up a working paper on Recoverable Behavioral Failures (RBFs) in LLM workflows. Version 1.8 is complete (PDF + LaTeX). The remaining work was blocked by sandbox isolation (no API keys, no GitHub auth) in the parent Claude session. You are running on the user's laptop with API keys in environment variables and GitHub auth available, so you can finish it.

## Workspace

- Repo root: this folder (`Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/`).
- Paper PDFs and LaTeX live under `paper/`. v1.8 is the canonical version (28 pages, TOC, full sixteen-mode treatment in §5). Both `paper_v1.8.pdf` (reportlab build) and `paper_v1.8_latex_compiled.pdf` (LaTeX compile of `paper_v1.8.tex`) are present.
- Mode content for §5 lives in `paper/mode_content.py` as a single source of truth shared between the reportlab generator (`generate_paper_v1_8.py`) and the LaTeX generator (`generate_paper_v1_8_tex.py`). If you change a mode treatment, edit `mode_content.py` and re-run both generators.
- Experiment pack with runner + tasks under `experiment_pack/`.
- Analysis script (cross-model comparison with Wilson CIs and grouped bar chart) under `analysis/`.
- Push instructions in `PUSH_COMMANDS.md`. Sample one-shot orchestration script at `run_all.sh`.

## What "done" looks like

1. The pilot experiment has run against whichever frontier models the user has API access to on `experiment_pack/tasks/evaluation_tasks.jsonl`. At least one provider is required. The protocol supports any subset of Anthropic, OpenAI, and Google.
   - **Anthropic-only path:** test current Sonnet plus current Opus (and Haiku if available). This produces an intra-vendor Sonnet-vs-Opus pilot, which is a valid scientific result.
   - **Cross-vendor path:** include OpenAI and/or Google if keys are available. This produces a cross-vendor pilot.
2. `experiment_pack/results/raw_outputs.jsonl` and `experiment_pack/results/scored_results.csv` exist with real model outputs and deterministic-check scores.
3. `experiment_pack/results/comparison.csv` and `experiment_pack/results/comparison.png` exist, produced by `analysis/compare_models.py`.
4. `paper/paper_v1.9.pdf` and `paper/paper_v1.9.tex` exist, with a new short section inserted between current §7 and current §8. The section title and framing depend on what was tested:
   - If only Anthropic models were tested: title is **"Intra-Vendor Pilot Results: Sonnet and Opus on the Experiment Pack."** Frame the comparison as within-vendor; explicitly note that cross-vendor extension is deferred to future work.
   - If two or more vendors were tested: title is **"Multi-Model Pilot Results."**
   In either case, report the real numbers from `comparison.csv`, embed `comparison.png`, update the contributions list and abstract accordingly, and include the "Caveats" paragraph about small n per cell and wide CIs.
5. The full folder is pushed to `https://github.com/vjgits/Research-Papers` as `Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/`. Visibility: ask the user (default to private if uncertain).

## Hard constraints (do not violate)

- **No fabricated results.** Only report numbers that actually came from running the experiment. If a provider call fails, report the failure honestly and exclude it from the comparison.
- **No personal data.** Do not introduce names, employer references, job-search context, side-project names (PRDgenius / AItube / Rewind), salary numbers, real `/Users/<personname>/` paths, real API keys, or any identifying information into the paper, README, or any committed file.
- **Neutral framing of vendors.** Do not write "Model X is generally worse" anywhere. Use language like "On these ten items, model X resolved Y of 10 first-pass; this is a pilot result, not a population estimate."
- **Honest about pilot scope.** The pack has 10 items across 5 categories. Reportable results are pilot results, not population rates. Wilson CIs will be very wide.
- **No process commentary in the paper.** No mention of Claude Code, this prompt, or what you changed. The paper is a research artifact, not a changelog.

## Step-by-step

### Step 1 — Sanity-check environment

```bash
echo "Anthropic: ${ANTHROPIC_API_KEY:+set}${ANTHROPIC_API_KEY:-MISSING}"
echo "OpenAI:    ${OPENAI_API_KEY:+set}${OPENAI_API_KEY:-MISSING}"
echo "Gemini:    ${GEMINI_API_KEY:+set}${GEMINI_API_KEY:-MISSING}"
which python3 pip3 git gh
```

If a provider's key is missing, ask the user whether they intend to include it. If they don't have a key for it, exclude that provider from the run and **also exclude it from the v1.9 results section**. Do not claim results for models you did not test. At least one provider is required; one is sufficient for a valid pilot.

### Step 2 — Install deps

```bash
cd experiment_pack
pip3 install -r requirements.txt
```

### Step 3 — Update model identifiers in `run_eval.py` invocation

The default model strings in `experiment_pack/README.md` (`openai:gpt-5.5`, `anthropic:claude-sonnet-4-5`, `google:gemini-2.5-pro`) are placeholders. Ask the user which currently-enabled models they want to test, or use these defaults that are commonly available as of mid-2026 (verify availability in each console first):

- Anthropic: pick the user's preferred current Sonnet model and current Opus model.
- OpenAI: pick the user's preferred current frontier model.
- Google: pick the user's preferred current Gemini Pro model.

Confirm the chosen identifiers with the user before running.

### Step 4 — Run the experiment

```bash
cd experiment_pack
python3 run_eval.py \
    --models \
        anthropic:<sonnet-id> \
        anthropic:<opus-id> \
        openai:<gpt-id> \
        google:<gemini-id> \
    --tasks tasks/evaluation_tasks.jsonl \
    --out results/raw_outputs.jsonl
```

If any provider call fails, capture the error in `results/run_errors.log` and continue. Do not retry on transient errors more than twice per item; this is a pilot run.

### Step 5 — Score

```bash
python3 score_results.py \
    --raw results/raw_outputs.jsonl \
    --tasks tasks/evaluation_tasks.jsonl \
    --out results/scored_results.csv
```

Open `scored_results.csv` and confirm it has columns including `task_id`, `model`, `category`, `score`. If the scorer's column names differ from what `analysis/compare_models.py` expects, pass the alternate column names via the script's `--col-model` / `--col-category` / `--col-score` flags, or adapt the scorer.

### Step 6 — Cross-model comparison

```bash
cd ../analysis
python3 compare_models.py \
    --scored ../experiment_pack/results/scored_results.csv \
    --out    ../experiment_pack/results/comparison.csv \
    --plot   ../experiment_pack/results/comparison.png
```

Verify `comparison.csv` and `comparison.png` are produced. Open the plot. It should show one grouped bar per category, with one bar per model and Wilson 95% CIs as error bars.

### Step 7 — Produce v1.9 paper with real results

The v1.8 manuscript is the current canonical version. Fork it to v1.9 to add the multi-model results. Two options:

**Option A (preferred): edit the .tex directly.** Copy `paper/paper_v1.8.tex` to `paper/paper_v1.9.tex`, make the edits listed below, and recompile. The .tex source already imports nothing dynamic from `mode_content.py` — it has the mode treatments inlined — so editing the .tex is self-contained.

**Option B: edit `mode_content.py` if you want to change a mode treatment, then rerun `generate_paper_v1_8.py` and `generate_paper_v1_8_tex.py`.** Don't do this for v1.9 unless you're also changing taxonomy text.

The edits for v1.9, in order:

1. Bump version. Change `\date{Version 1.8 \quad May 2026}` to `\date{Version 1.9 \quad <today's date>}`. Update the `pdftitle` in `\hypersetup` to `(v1.9)`.

2. Update the abstract. Add this sentence to the end of the Abstract: *"We additionally report a multi-model pilot result on the ten-task experiment pack, with per-model and per-category pass rates and Wilson 95\% confidence intervals; these results are exploratory and not population estimates."*

3. Insert the new "Multi-Model Pilot Results" section between current §7 (Pilot Experiment) and current §8 (Observational Notes Beyond the Pilot). Make it about one page. Include:
   - The list of models actually tested, by family (e.g., "Anthropic Sonnet `<id>`, Anthropic Opus `<id>`, OpenAI `<id>`, Google `<id>`").
   - The pack composition reminder: 10 items across 5 categories (QI, PPG, EBC, ACM, RETRY_PROXY), 2 items per category.
   - A `tabularx` table reproducing `comparison.csv` (columns: model, category, n_items, n_pass, pass_rate, Wilson 95% CI low/high).
   - The `comparison.png` figure with caption: *"Multi-model pilot pass rate by category, with Wilson 95\% confidence intervals."* The figure file path is `../experiment_pack/results/comparison.png`; copy it into `paper/figures/comparison.png` and reference from there so the .tex is self-contained.
   - A "Caveats" paragraph: small n per cell (2 items), wide CIs, single-pilot, single-user prompt design, no inter-rater check on outputs, no statistical claims of model superiority based on this sample size.

4. Update the contributions list (§1.1) to add a sixth item: *"A first multi-model pilot result on the experiment pack, providing existence-level evidence that the metrics surface measurable per-model differences on a small sample, and that the protocol is implementable across at least three frontier API surfaces."*

5. Compile: `cd paper && pdflatex -interaction=nonstopmode paper_v1.9.tex && pdflatex -interaction=nonstopmode paper_v1.9.tex` (twice for the TOC). Confirm `paper_v1.9.pdf` builds without errors and includes the new section in the TOC.

6. Update `README.md` at the repo root: change current-version line to `**Current version:** 1.9 (<today>) — supersedes v1.8`. Add a bullet to the v1.8 changes list describing the v1.9 change: *"Adds §8 Multi-Model Pilot Results based on a real run of the ten-task pack against Anthropic, OpenAI, and Google models."* Renumber subsequent sections in the README directory tree to reflect that §8 is now Multi-Model Pilot Results.

7. Update `CITATION.cff`: version → "1.9", date-released → today.

### Step 8 — Commit and push

```bash
cd <repo-root>
git init
git add .
git commit -m "v1.9: add multi-model pilot results from experiment pack run"
git branch -M main
```

If the user wants the repo public, ask. Otherwise default to private:

```bash
gh repo create vjgits/Research-Papers --private --source=. --remote=origin --push
```

If `gh` is not available, fall back to creating the repo via the web UI and pushing with `git remote add origin https://github.com/vjgits/Research-Papers.git && git push -u origin main`.

### Step 9 — Verify

Print these to the chat at the end:
- The five rows of `comparison.csv` head, so the user can sanity-check.
- The arXiv-checklist status: PDF compiles, no fabricated results, no personal data in committed files, .gitignore excludes results that should not be in git.
- The GitHub URL of the pushed repo.

## Files Claude Code may need to know about

Path | Purpose
--- | ---
`paper/paper_v1.8.pdf` | Current paper, reportlab build, 28 pp with TOC
`paper/paper_v1.8.tex` | LaTeX source to fork into v1.9 (this is the canonical source for arXiv submission)
`paper/paper_v1.8_latex_compiled.pdf` | LaTeX-compiled v1.8 PDF (for visual diff, 28 pp with TOC)
`paper/mode_content.py` | Source of truth for §5 mode treatments (shared by both generators)
`paper/generate_paper_v1_8.py` | Reportlab generator
`paper/generate_paper_v1_8_tex.py` | LaTeX-source generator
`experiment_pack/run_eval.py` | Multi-provider runner
`experiment_pack/score_results.py` | Deterministic scorer
`experiment_pack/tasks/evaluation_tasks.jsonl` | 10 pilot items
`analysis/compare_models.py` | Cross-model comparison with Wilson CIs and bar chart
`README.md` | Repo-level readme, update to v1.9
`CITATION.cff` | Update version + date
`.gitignore` | Already excludes `results/*.jsonl` `results/*.csv` `results/*.png` — keep that
`PUSH_COMMANDS.md` | Step-by-step git/gh push reference
`run_all.sh` | One-shot orchestration script that runs steps 2-6

## If something fails

- API rate limit: pause and continue, do not skip an entire model just because one item rate-limited.
- One provider unavailable: drop it from `--models`, note the exclusion in §7 caveats, and finish with the remaining providers.
- LaTeX compile error: read the .log, fix the offending lines, rerun. Common: missing package, mismatched `\begin{...}` / `\end{...}`, missing image file.
- Git push auth failure: use `gh auth login` or generate a PAT at github.com/settings/tokens with `repo` scope.

When finished, return to the user a single chat message containing: the comparison.csv head, the v1.9 PDF link, and the GitHub URL.

---
