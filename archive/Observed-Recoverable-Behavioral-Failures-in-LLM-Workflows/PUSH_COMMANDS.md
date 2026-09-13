# How to publish this folder to GitHub

The folder you have on disk under `outputs/github_package/Research-Papers/Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/` is ready to push. From your laptop:

## Option A — Create the repo via the web UI (simplest)

1. Go to https://github.com/new
2. Owner: `vjgits`
3. Repository name: `Research-Papers`
4. Visibility: Public or Private (your choice)
5. **Do not** initialize with a README, .gitignore, or LICENSE — you already have them
6. Click "Create repository"

Then from your terminal:

```bash
cd "/Users/VJ/Library/Application Support/Claude/local-agent-mode-sessions/454ccef4-4c43-4923-be47-fa9a9bf4df27/93aa6ab5-e970-4b6d-ae06-802c26410bfa/local_88558492-732b-4d06-9898-9581964f21fe/outputs/github_package/Research-Papers"

git init
git add .
git commit -m "Initial commit: Observed Recoverable Behavioral Failures in LLM Workflows v1.7"
git branch -M main
git remote add origin https://github.com/vjgits/Research-Papers.git
git push -u origin main
```

The first push will prompt for GitHub credentials. If you have 2FA, use a personal access token (PAT) instead of your password — generate at https://github.com/settings/tokens with `repo` scope.

## Option B — Use the GitHub CLI (if you have `gh` installed)

```bash
cd "/Users/VJ/Library/Application Support/Claude/local-agent-mode-sessions/454ccef4-4c43-4923-be47-fa9a9bf4df27/93aa6ab5-e970-4b6d-ae06-802c26410bfa/local_88558492-732b-4d06-9898-9581964f21fe/outputs/github_package/Research-Papers"

git init
git add .
git commit -m "Initial commit: Observed Recoverable Behavioral Failures in LLM Workflows v1.7"
git branch -M main
gh repo create vjgits/Research-Papers --public --source=. --remote=origin --push
```

(Substitute `--private` for `--public` if you prefer.)

## What lives where after the push

```
github.com/vjgits/Research-Papers
└── Observed-Recoverable-Behavioral-Failures-in-LLM-Workflows/
    ├── paper/paper_v1.7.pdf
    ├── paper/experiment_pack_v1.0.pdf
    ├── experiment_pack/                ← run_eval.py, score_results.py, tasks/, results/
    ├── analysis/compare_models.py
    ├── README.md
    ├── LICENSE
    ├── CITATION.cff
    └── .gitignore
```

## If you want to add future papers to the same repo

Create sibling folders inside `Research-Papers/`. Each paper gets its own folder with its own paper PDF, code, and README. The repo-level README can stay minimal or you can add an index that lists each paper.

## A note on the personal-data scrub

The original experiment pack (`evaluation_tasks.jsonl`, item `ppg_001`) contained `/Users/vijay/projects/ai-eval-runner` as part of a path-substitution test. That has been replaced in this package with `/Users/researcher/projects/ai-eval-runner`. The original pack file in your local `uploads/` folder still contains the old path. If you re-zip the pack, use the version in this package, not the upload.
