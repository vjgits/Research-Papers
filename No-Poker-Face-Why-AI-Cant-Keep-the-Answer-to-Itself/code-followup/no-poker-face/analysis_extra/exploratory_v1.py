"""Labelled additions to the pre-registered analysis (written 2026-10-11, after the main run). Not confirmatory.
1) B2 risk-difference 95% CI (Newcombe) — pre-registered but not output by the frozen code.
2) Per-writer PD and KF by difficulty level (exploratory).
3) KF of the other-family strong solver by level (robustness of KF to solver choice; exploratory).
4) Gemini arm with the pre-registered exclusion rule applied (<50% valid in any round)."""
import json, sys
import numpy as np, pandas as pd
from statsmodels.stats.proportion import confint_proportions_2indep

MAIN = "/home/claude/main_run/npf-frozen/runs/main_sessions"
GEM = "/home/claude/gemini_arm_run/npf/runs/gemini_arm"
LV = ["easy", "medium", "hard", "trickier", "harder"]

def boot_mean(x, n=4000, seed=0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    rng = np.random.default_rng(seed); b = rng.choice(x, (n, len(x))).mean(1)
    return round(x.mean()*100, 1), [round(np.percentile(b, 2.5)*100, 1), round(np.percentile(b, 97.5)*100, 1)], len(x)

out = {}
lo, hi = confint_proportions_2indep(0, 24, 0, 24, method="newcomb", compare="diff")
out["B2_risk_diff_CI95_newcombe_pts"] = [round(lo*100, 1), round(hi*100, 1)]

rt = pd.read_csv(f"{MAIN}/round_table.csv")
inv = rt[(rt.invented) & (rt["round"] >= 2)]
pw = {}
for w, g in inv.groupby("writer"):
    pw[w] = {lv: {"PD": boot_mean(g[g.level == lv].groupby("session").PD.mean()),
                  "KF_gemini": boot_mean(g[g.level == lv].groupby("session")["KF_gemini-3.6-flash"].mean())} for lv in LV}
    other = "KF_gpt-5.6-terra" if w.startswith("claude") else "KF_claude-sonnet-5-5"
    for lv in LV:
        pw[w][lv]["KF_other_family_strong"] = boot_mean(g[g.level == lv].groupby("session")[other].mean())
    pw[w]["stem_words_easy_vs_hard"] = [round(g[g.level == "easy"].stem_words.mean(), 1), round(g[g.level == "hard"].stem_words.mean(), 1)]
out["per_writer_invented_r2_7"] = pw

# Gemini arm with exclusion rule
gt = pd.read_csv(f"{GEM}/round_table.csv")
bad = sorted(gt[gt.n_valid < 5].session.unique())
out["gemini_arm_excluded_sessions"] = bad
trs = [json.loads(l) for l in open(f"{GEM}/transcripts.jsonl")]
keep = [t for t in trs if t["session"] not in bad]
def ready(st): 
    s = [t for t in keep if t["stype"] == st]; return f'{sum(t["readiness"]["label"] == "READY" for t in s)}/{len(s)}'
out["gemini_arm_readiness_after_exclusion"] = {st: ready(st) for st in ["C", "F", "FT", "IMP", "CLAIM", "FAIL-LO", "FAIL-HI"]}
gi = gt[(gt.invented) & (gt["round"] >= 2) & (~gt.session.isin(bad))]
kfcols = [c for c in gt.columns if c.startswith("KF_")]
gi = gi.assign(KF=gi[kfcols].mean(1))
out["gemini_arm_invented_by_level"] = {lv: {"PD": boot_mean(gi[gi.level == lv].groupby("session").PD.mean()),
                                            "KF_mean_two_solvers": boot_mean(gi[gi.level == lv].groupby("session").KF.mean())} for lv in LV}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(out, indent=1))
