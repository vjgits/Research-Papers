"""Figure 1: panel accuracy (PD) and knowledge-free accuracy (KF) by requested difficulty, invented subjects, rounds 2-7."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
E = json.load(open(sys.argv[1])); M = json.load(open(sys.argv[2])); out = sys.argv[3]
LV = ["easy", "medium", "hard", "trickier", "harder"]; XL = ["easy", "medium", "hard", "trickier", "harder\nthan last"]
S = [("Claude Opus 5.5", "#2a78d6", "o", "-", E["per_writer_invented_r2_7"]["claude-opus-5-5"], "PD", "KF_gemini"),
     ("GPT-5.6 Sol", "#eb6834", "s", "-", E["per_writer_invented_r2_7"]["gpt-5.6-sol"], "PD", "KF_gemini"),
     ("Gemini 3.1 Pro (exploratory arm)", "#1baf7a", "^", "--", E["gemini_arm_invented_by_level"], "PD", "KF_mean_two_solvers")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b",
                     "xtick.color": "#52514e", "ytick.color": "#52514e"})
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True, facecolor="#fcfcfb")
for ax, idx, title in [(axs[0], 5, "Learner panel accuracy (higher = easier)"), (axs[1], 6, "No-material accuracy (leakage; chance = 25%)")]:
    ax.set_facecolor("#fcfcfb")
    for name, col, mk, ls, d, pdk, kfk in S:
        key = pdk if idx == 5 else kfk
        y = [d[l][key][0] for l in LV]; lo = [d[l][key][1][0] for l in LV]; hi = [d[l][key][1][1] for l in LV]
        x = range(len(LV))
        ax.fill_between(x, lo, hi, color=col, alpha=0.10, lw=0)
        ax.plot(x, y, ls, color=col, lw=2, marker=mk, ms=6, mec="#fcfcfb", mew=1.5, label=name)
    if idx == 6:
        ax.axhline(25, color="#52514e", lw=1, ls=":"); ax.text(4.1, 26, "chance", color="#52514e", fontsize=8, ha="right")
    ax.set_xticks(range(len(LV))); ax.set_xticklabels(XL, fontsize=8)
    ax.set_title(title, fontsize=9.5, loc="left", color="#0b0b0b")
    ax.grid(axis="y", color="#e6e5e1", lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axs[0].set_ylabel("% correct (session mean, 95% CI)"); axs[0].set_ylim(20, 90)
axs[0].legend(loc="lower left", fontsize=7.5, frameon=False)
fig.text(0.01, -0.02, "Requested difficulty level (rounds 2-7, invented subjects). Panel: two Gemini 3.1 Flash-Lite learners (Claude/GPT writers) or two Claude Haiku learners (Gemini writer).",
         fontsize=7, color="#52514e")
fig.tight_layout(); fig.savefig(out, dpi=220, bbox_inches="tight", facecolor="#fcfcfb")
