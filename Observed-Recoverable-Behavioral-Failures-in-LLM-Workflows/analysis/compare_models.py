#!/usr/bin/env python3
"""Cross-model comparison of recoverable-behavioral-failure proxy pass rates.

Consumes scored_results.csv produced by score_results.py and produces:
  - A per-(model, category) summary CSV with pass rate and Wilson 95% CI.
  - A grouped bar chart comparing models within each category.

Example:
    python compare_models.py \
        --scored ../experiment_pack/results/scored_results.csv \
        --out ../experiment_pack/results/comparison.csv \
        --plot ../experiment_pack/results/comparison.png

Inputs:
    The scored CSV must contain at least these columns:
        task_id, model, category, score (1 = pass, 0 = fail)
    If score_results.py emits a different schema, adapt --col-* flags below.
"""
import argparse
import csv
import math
import os
import sys
from collections import defaultdict


def wilson_ci(k, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + (z * z) / n
    centre = (p + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def load_scored(path, col_model, col_category, col_score):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            try:
                rows.append({
                    "model":    r[col_model],
                    "category": r[col_category],
                    "score":    int(r[col_score]),
                })
            except KeyError as e:
                sys.stderr.write(f"missing column in scored CSV: {e}\n")
                sys.exit(2)
    return rows


def aggregate(rows):
    """Group by (model, category) -> {n, k_pass}."""
    g = defaultdict(lambda: {"n": 0, "k": 0})
    for r in rows:
        key = (r["model"], r["category"])
        g[key]["n"] += 1
        g[key]["k"] += r["score"]
    return g


def write_summary(groups, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "model", "category", "n_items", "n_pass",
            "pass_rate", "wilson_lo", "wilson_hi",
        ])
        for (model, cat), v in sorted(groups.items()):
            n, k = v["n"], v["k"]
            rate = (k / n) if n else float("nan")
            lo, hi = wilson_ci(k, n)
            w.writerow([
                model, cat, n, k,
                f"{rate:.4f}", f"{lo:.4f}", f"{hi:.4f}",
            ])
    print(f"Wrote summary: {out_path}")


def make_plot(groups, plot_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        sys.stderr.write("matplotlib not installed; skipping plot. "
                         "Run: pip install matplotlib\n")
        return

    models = sorted({m for m, _ in groups.keys()})
    cats = sorted({c for _, c in groups.keys()})
    if not models or not cats:
        sys.stderr.write("no data to plot\n")
        return

    import numpy as np
    width = 0.8 / max(len(models), 1)
    x = np.arange(len(cats))

    fig, ax = plt.subplots(figsize=(max(8, 1.4 * len(cats)), 5))
    for i, m in enumerate(models):
        rates, errs_lo, errs_hi = [], [], []
        for c in cats:
            v = groups.get((m, c), {"n": 0, "k": 0})
            n, k = v["n"], v["k"]
            r = (k / n) if n else 0.0
            lo, hi = wilson_ci(k, n) if n else (0.0, 0.0)
            rates.append(r)
            errs_lo.append(max(0, r - lo))
            errs_hi.append(max(0, hi - r))
        ax.bar(x + i * width, rates, width, label=m,
               yerr=[errs_lo, errs_hi], capsize=3)

    ax.set_xticks(x + width * (len(models) - 1) / 2)
    ax.set_xticklabels(cats, rotation=20, ha="right")
    ax.set_ylabel("Pass rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("Per-(model, category) pass rate with Wilson 95% CI")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    print(f"Wrote plot: {plot_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scored", required=True, help="Path to scored_results.csv")
    ap.add_argument("--out", required=True, help="Path to output comparison.csv")
    ap.add_argument("--plot", default=None, help="Optional output plot path (.png)")
    ap.add_argument("--col-model", default="model")
    ap.add_argument("--col-category", default="category")
    ap.add_argument("--col-score", default="score")
    args = ap.parse_args()

    rows = load_scored(args.scored, args.col_model, args.col_category, args.col_score)
    if not rows:
        sys.stderr.write("no rows loaded; nothing to do\n")
        return 1

    groups = aggregate(rows)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    write_summary(groups, args.out)

    if args.plot:
        os.makedirs(os.path.dirname(os.path.abspath(args.plot)) or ".", exist_ok=True)
        make_plot(groups, args.plot)

    return 0


if __name__ == "__main__":
    sys.exit(main())
