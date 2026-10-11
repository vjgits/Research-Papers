"""Pre-registered analysis for the follow-up study (Addendum 2). Written and frozen BEFORE any follow-up data exist.

KF (knowledge-free accuracy) of a round = mean, over the two cross-family strong solvers, of the share of the round's
questions answered correctly with no material ('nohist' probe). Both subjects are invented, so KF above 25% is leakage.
Exclusion (pre-registered, also applied here): a session with fewer than 5 valid questions in any round is dropped.

H1 (difficulty requests increase leakage), confirmatory writers, C sessions only:
    d_s = mean KF over the session's rounds requested as hard, trickier or harder  minus  KF of its easy round.
    One-sided one-sample t-test of mean(d_s) > 0.  Smallest effect of interest: +6 points.
H2 (distractor-matching instruction reduces leakage), confirmatory writers, C vs CFIX:
    session KF = mean KF over rounds 2-7. OLS  KF ~ FIX + subject + writer + order, HC3. One-sided test of FIX < 0.
Holm across H1 and H2 (one-sided): smaller p vs 0.025, larger vs 0.05.
Secondary (descriptive, 95% session bootstrap): H1 per writer and per solver; d_s in CFIX and CFIX minus C; KF and
panel accuracy (PD) by level and arm; key-is-longest share by arm; key check (solver with material) by arm, to see
whether the instruction breaks answer keys; Gemini arm (exploratory) estimates of everything above.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from .pipeline import read_jsonl
from .session_analysis_v2 import GEMINI_MEMBERS

HARD = ("hard", "trickier", "harder")
LEVELS = ["easy", "medium", "hard", "trickier", "harder"]


def _boot(x, n=4000, seed=0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) == 0:
        return None
    b = np.random.default_rng(seed).choice(x, (n, len(x))).mean(1)
    return {"mean": round(x.mean() * 100, 1), "ci95": [round(np.percentile(b, 2.5) * 100, 1), round(np.percentile(b, 97.5) * 100, 1)], "n": len(x)}


def _boot_diff(a, b, n=4000, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    bs = rng.choice(a, (n, len(a))).mean(1) - rng.choice(b, (n, len(b))).mean(1)
    return {"diff": round((a.mean() - b.mean()) * 100, 1), "ci95": [round(np.percentile(bs, 2.5) * 100, 1), round(np.percentile(bs, 97.5) * 100, 1)],
            "n": [len(a), len(b)]}


def tables(outdir):
    trs = read_jsonl(outdir / "transcripts.jsonl")
    pr = pd.DataFrame(read_jsonl(outdir / "session_probes.jsonl"))
    excluded = sorted(t["session"] for t in trs if min(rd["n_valid"] for rd in t["rounds"]) < 5)
    trs = [t for t in trs if t["session"] not in excluded]
    kf = pr[pr.probe == "nohist"].groupby(["session", "round"]).correct.mean()
    kf_s = pr[pr.probe == "nohist"].groupby(["session", "round", "solver"]).correct.mean().unstack("solver")
    rows = []
    for t in trs:
        for rd in t["rounds"]:
            n = max(1, rd["n_valid"]); key = (t["session"], rd["round"])
            r = {"session": t["session"], "writer": t["writer"], "group": t.get("group"), "subject": t["subject"], "arm": t["stype"],
                 "order": t["order"], "round": rd["round"], "level": rd["difficulty"], "n_valid": rd["n_valid"],
                 "KF": kf.get(key, np.nan), "PD": np.mean([rd["panel_correct"][i] / n for i in GEMINI_MEMBERS]),
                 "stem_words": np.mean([len(q["stem"].split()) for q in rd["questions"]]) if rd["questions"] else np.nan,
                 "key_longest": np.mean([max(q["options"], key=lambda k: len(q["options"][k])) == q["answer"] for q in rd["questions"]]) if rd["questions"] else np.nan}
            for s in kf_s.columns:
                r["KF_" + s] = kf_s.loc[key, s] if key in kf_s.index else np.nan
            rows.append(r)
    return pd.DataFrame(rows), pr, excluded


def d_scores(rt, col="KF"):
    def d(g):
        return g[g.level.isin(HARD)][col].mean() - g[g.level == "easy"][col].mean()
    return rt.groupby(["session", "writer", "group", "subject", "arm", "order"]).apply(d).rename("d").reset_index()


def analyze(outdir, mock=False):
    rt, pr, excluded = tables(outdir)
    res = {"MOCK_NOT_DATA": bool(mock), "excluded_sessions": excluded, "n_sessions": int(rt.session.nunique())}
    late = rt[rt["round"] >= 2]
    conf = late[late.group == "confirm"]
    ds = d_scores(conf)
    c = ds[ds.arm == "C"].d.dropna()
    t = stats.ttest_1samp(c, 0, alternative="greater")
    res["H1"] = {"mean_pts": round(c.mean() * 100, 1), "boot": _boot(c), "t": round(float(t.statistic), 3), "p_one_sided": float(t.pvalue), "n": len(c)}
    sess = conf.groupby(["session", "writer", "subject", "arm", "order"]).KF.mean().reset_index()
    sess["FIX"] = (sess.arm == "CFIX").astype(int)
    m = smf.ols("KF ~ FIX + C(subject) + C(writer) + C(order)", sess).fit(cov_type="HC3")
    coef, se = m.params["FIX"], m.bse["FIX"]
    p2 = float(stats.norm.cdf(coef / se))   # one-sided, FIX < 0
    res["H2"] = {"coef_pts": round(coef * 100, 1), "ci95": [round((coef - 1.96 * se) * 100, 1), round((coef + 1.96 * se) * 100, 1)],
                 "p_one_sided": p2, "n": int(len(sess)), "boot": _boot_diff(sess[sess.FIX == 1].KF, sess[sess.FIX == 0].KF)}
    ps = sorted([("H1", res["H1"]["p_one_sided"]), ("H2", p2)], key=lambda x: x[1])
    holm, go = {}, True
    for i, (k, p) in enumerate(ps):
        a = 0.025 if i == 0 else 0.05
        rej = go and p < a
        holm[k] = {"p": round(p, 4), "alpha": a, "reject": bool(rej)}
        go = go and rej
    res["holm"] = holm
    # ---- secondary (descriptive)
    res["H1_by_writer"] = {w: _boot(g[g.arm == "C"].d) for w, g in ds.groupby("writer")}
    res["H1_by_solver"] = {}
    for col in [c for c in conf.columns if c.startswith("KF_")]:
        dd = d_scores(conf, col)
        res["H1_by_solver"][col] = _boot(dd[dd.arm == "C"].d)
    res["d_CFIX"] = _boot(ds[ds.arm == "CFIX"].d)
    res["d_CFIX_minus_C"] = _boot_diff(ds[ds.arm == "CFIX"].d.dropna(), ds[ds.arm == "C"].d.dropna())
    res["by_level_arm"] = {arm: {lv: {"KF": _boot(g[g.level == lv].groupby("session").KF.mean()),
                                      "PD": _boot(g[g.level == lv].groupby("session").PD.mean()),
                                      "stem_words": round(float(g[g.level == lv].stem_words.mean()), 1),
                                      "key_longest": round(float(g[g.level == lv].key_longest.mean()) * 100, 1)}
                                 for lv in LEVELS} for arm, g in conf.groupby("arm")}
    spec = pr[pr.probe == "spec"].copy()
    spec["arm"] = spec.session.str.split("|").str[2]
    spec["writer"] = spec.session.str.split("|").str[0]
    res["key_check_by_arm"] = spec.groupby("arm").correct.mean().round(3).to_dict()
    gem = late[late.group == "gemini"]
    if len(gem):
        gd = d_scores(gem)
        gs = gem.groupby(["session", "arm"]).KF.mean().reset_index()
        res["gemini_exploratory"] = {"d_C": _boot(gd[gd.arm == "C"].d), "d_CFIX": _boot(gd[gd.arm == "CFIX"].d),
                                     "KF_CFIX_minus_C": _boot_diff(gs[gs.arm == "CFIX"].KF, gs[gs.arm == "C"].KF),
                                     "key_check_by_arm": spec[spec.writer == "gemini-3.1-pro-preview"].groupby("arm").correct.mean().round(3).to_dict()}
    res["valid_share"] = round(float(rt.n_valid.sum() / (10 * len(rt))), 4)
    (outdir / "followup_results.json").write_text(json.dumps(res, indent=1, default=str))
    rt.to_csv(outdir / "followup_round_table.csv", index=False)
    return res
