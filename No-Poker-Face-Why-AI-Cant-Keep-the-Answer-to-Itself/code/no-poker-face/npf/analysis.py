"""Analysis: per-condition leakage measures, the primary N-vs-W contrast, judge agreement,
and a power simulation that sizes the main study from calibration data."""
import json
import warnings

import numpy as np
import pandas as pd

from .config import CONDITIONS, PRIMARY_CONTRAST
from .pipeline import read_jsonl

warnings.filterwarnings("ignore")
import logging; logging.captureWarnings(True)
BOOL_CODES = ["deciding_fact_in_stem", "stem_key_overlap", "rule_echo", "explains_in_stem",
              "keyed_best_practice_register", "dominant_heuristic", "multiple_defensible"]


def load(outdir):
    items = pd.DataFrame(read_jsonl(outdir / "items.jsonl"))
    solves = pd.DataFrame(read_jsonl(outdir / "solves.jsonl"))
    codes = pd.DataFrame(read_jsonl(outdir / "codes.jsonl"))
    feats = pd.DataFrame(read_jsonl(outdir / "features.jsonl"))
    return items, solves, codes, feats


def collapse_codes(codes):
    """Two judges per item. 'both' = conservative (both say yes); 'either' = liberal."""
    c = codes[codes.parsed == True].copy()
    for k in BOOL_CODES:
        c[k] = c[k].astype("boolean")
    c["key_ok"] = c.key_correct.eq("yes")
    c["n_false_on_own"] = c.distractors.apply(
        lambda d: sum(v == "false_on_own" for v in d.values()) if isinstance(d, dict) else np.nan)
    g = c.groupby("id")
    out = pd.DataFrame({f"{k}_both": g[k].all() for k in BOOL_CODES + ["key_ok"]})
    for k in BOOL_CODES + ["key_ok"]:
        out[f"{k}_either"] = g[k].any()
    out["n_false_on_own"] = g.n_false_on_own.mean()
    out["n_judges"] = g.size()
    agree = {}
    for k in BOOL_CODES + ["key_ok"]:
        piv = c.pivot_table(index="id", columns="judge", values=k, aggfunc="first").dropna()
        if piv.shape[1] == 2 and len(piv):
            a, b = piv.iloc[:, 0].astype(bool), piv.iloc[:, 1].astype(bool)
            po = (a == b).mean()
            pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
            agree[k] = {"agreement": round(po, 3), "kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else None, "n": len(piv)}
    return out.reset_index(), agree


def item_table(outdir):
    items, solves, codes, feats = load(outdir)
    cc, agree = collapse_codes(codes) if len(codes) else (pd.DataFrame({"id": []}), {})
    df = items.merge(feats, on="id", how="left").merge(cc, on="id", how="left")
    s = solves[solves.parsed == True]
    acc = s.pivot_table(index="id", columns="mode", values="correct", aggfunc="mean")
    acc.columns = [f"acc_{c}" for c in acc.columns]
    df = df.merge(acc.reset_index(), on="id", how="left")
    df["slot_key"] = df.domain + ":" + df.slot
    return df, s.merge(items[["id", "writer", "domain", "cond", "slot", "weak_slot"]], on="id"), agree


def cluster_boot_diff(a_by_slot, b_by_slot, n=4000, seed=0):
    """Paired difference of slot means (b - a), bootstrap over blueprint slots."""
    j = pd.concat([a_by_slot.rename("a"), b_by_slot.rename("b")], axis=1).dropna()
    if len(j) < 3:
        return np.nan, (np.nan, np.nan), len(j)
    d = (j.b - j.a).values
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, (n, len(d))).mean(1)
    return float(d.mean()), tuple(float(x) for x in np.percentile(bs, [2.5, 97.5])), len(j)


def gee_contrast(sl, c0, c1):
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    d = sl[sl.cond.isin([c0, c1])].copy()
    d["treat"] = (d.cond == c1).astype(int)
    d["y"] = d.correct.astype(int)
    d["grp"] = d.domain + ":" + d.slot
    if d.treat.nunique() < 2 or len(d) < 30:
        return None
    try:
        m = smf.gee("y ~ treat + C(solver) + C(domain)", "grp", d, family=sm.families.Binomial(),
                    cov_struct=sm.cov_struct.Exchangeable()).fit()
        b, se = m.params["treat"], m.bse["treat"]
        return {"log_odds": round(b, 3), "odds_ratio": round(float(np.exp(b)), 3),
                "ci95": [round(float(np.exp(b - 1.96 * se)), 3), round(float(np.exp(b + 1.96 * se)), 3)],
                "p": float(m.pvalues["treat"]), "n_obs": len(d), "n_clusters": d.grp.nunique()}
    except Exception as e:
        return {"error": str(e)[:200]}


def summarize(outdir):
    df, sl, agree = item_table(outdir)
    res = {"n_items": len(df), "judge_agreement": agree, "by_condition": {}, "contrasts": {}}
    order = [c for c in CONDITIONS if c in set(df.cond)]
    cols = {"acc_options_only": "options-only acc", "acc_mismatched": "mismatched-stem acc", "acc_full": "full acc",
            "acc_with_spec": "with-reference acc (key check)", "key_longest": "keyed longest",
            "near_duplicate_options": "near-duplicate options", "stem_key_only_overlap_n": "stem→key-only overlap (words)",
            "notes_bigram_overlap": "notes bigram overlap", "deciding_fact_in_stem_both": "deciding fact in stem (both judges)",
            "deciding_fact_in_stem_either": "deciding fact in stem (either)", "rule_echo_either": "rule echo (either)",
            "explains_in_stem_either": "explains in stem (either)", "dominant_heuristic_both": "dominant heuristic (both)",
            "keyed_best_practice_register_both": "best-practice register (both)", "n_false_on_own": "distractors false on own (of 3)",
            "key_ok_both": "key correct (both judges)", "multiple_defensible_either": "multiple defensible (either)"}
    tab = []
    for dom in ["all"] + sorted(df.domain.unique()):
        d = df if dom == "all" else df[df.domain == dom]
        for c in order:
            x = d[d.cond == c]
            row = {"domain": dom, "cond": c, "n": len(x)}
            for k, lab in cols.items():
                if k in x:
                    row[lab] = round(float(pd.to_numeric(x[k], errors="coerce").mean()), 3) if len(x) else None
            tab.append(row)
    res["by_condition"] = tab
    # stem information = full - mismatched (fictional domain: solver knowledge cannot help)
    # primary + secondary contrasts against N
    sl_oo = sl[sl["mode"] == "options_only"]
    for c in [k for k in order if k != "N"]:
        base = "NG" if c == "WG" else "N"
        entry = {}
        for dom in ["all"] + sorted(df.domain.unique()):
            q = sl_oo if dom == "all" else sl_oo[sl_oo.domain == dom]
            a = q[q.cond == base].assign(k=lambda z: z.domain + ":" + z.slot).groupby("k").correct.mean()
            b = q[q.cond == c].assign(k=lambda z: z.domain + ":" + z.slot).groupby("k").correct.mean()
            diff, ci, n = cluster_boot_diff(a, b)
            entry[dom] = {"diff_options_only": None if np.isnan(diff) else round(diff, 3),
                          "ci95": [None if np.isnan(v) else round(v, 3) for v in ci], "n_slots": n}
            # stem-cue composite (either judge), item level, paired by slot
            dd = df if dom == "all" else df[df.domain == dom]
            cue = dd.assign(cue=lambda z: (z.deciding_fact_in_stem_either.fillna(False) | z.rule_echo_either.fillna(False)
                                           | (z.stem_key_only_overlap_n.fillna(0) > 0)).astype(float))
            a2 = cue[cue.cond == base].groupby("slot_key").cue.mean()
            b2 = cue[cue.cond == c].groupby("slot_key").cue.mean()
            d2, ci2, _ = cluster_boot_diff(a2, b2)
            entry[dom]["diff_stem_cue_rate"] = None if np.isnan(d2) else round(d2, 3)
            entry[dom]["stem_cue_ci95"] = [None if np.isnan(v) else round(v, 3) for v in ci2]
        entry["gee_options_only"] = gee_contrast(sl_oo, base, c)
        res["contrasts"][f"{c} vs {base}"] = entry
    # weak-slot interaction for the primary contrast
    c0, c1 = PRIMARY_CONTRAST
    w = {}
    for flag in [True, False]:
        q = sl_oo[(sl_oo.weak_slot == flag)]
        a = q[q.cond == c0].groupby(q.domain + ":" + q.slot).correct.mean()
        b = q[q.cond == c1].groupby(q.domain + ":" + q.slot).correct.mean()
        diff, ci, n = cluster_boot_diff(a, b)
        w["weak_slots" if flag else "other_slots"] = {"diff": None if np.isnan(diff) else round(diff, 3),
                                                     "ci95": [None if np.isnan(v) else round(v, 3) for v in ci], "n": n}
    res["primary_by_slot_type"] = w
    # H2: notes overlap R vs W
    a = df[df.cond == "W"].groupby("slot_key").notes_bigram_overlap.mean()
    b = df[df.cond == "R"].groupby("slot_key").notes_bigram_overlap.mean()
    diff, ci, n = cluster_boot_diff(a, b)
    res["H2_notes_overlap_R_minus_W"] = {"diff": None if np.isnan(diff) else round(diff, 3),
                                         "ci95": [None if np.isnan(v) else round(v, 3) for v in ci], "n": n}
    res["solver_parse_rate"] = round(float(sl.parsed.mean()), 3) if len(sl) else None
    return df, sl, res


def simulate_power(sl, effects=(0.05, 0.08, 0.10), samples=(1, 3, 5, 8), slots=(40,), n_sim=600, seed=1,
                   mode="options_only", domain=None, writers=2):
    """Size the main study from calibration: estimate baseline options-only accuracy and the
    between-slot spread (logit scale) in N, then simulate the paired N-vs-W slot-mean test."""
    rng = np.random.default_rng(seed)
    q = sl[(sl["mode"] == mode) & (sl.cond == "N")]
    if domain:
        q = q[q.domain == domain]
    p0 = float(q.correct.mean()) if len(q) else 0.6
    slot_means = q.groupby(q.domain + ":" + q.slot).correct.mean().clip(0.02, 0.98)
    lg = np.log(slot_means / (1 - slot_means))
    sd_slot = float(lg.std()) if len(lg) > 2 else 1.0
    n_solves_per_item = int(q.groupby("id").size().mean()) if len(q) else 2
    out = []
    logit = lambda p: np.log(p / (1 - p))
    inv = lambda x: 1 / (1 + np.exp(-x))
    for S in slots:
        for k in samples:
            for e in effects:
                hits = 0
                for _ in range(n_sim):
                    u = rng.normal(logit(p0), sd_slot, S)
                    shift = logit(min(.99, p0 + e)) - logit(p0)
                    m = writers * k * n_solves_per_item
                    a = rng.binomial(m, inv(u)) / m
                    b = rng.binomial(m, inv(u + shift + rng.normal(0, 0.3, S))) / m
                    d = b - a
                    t = d.mean() / (d.std(ddof=1) / np.sqrt(S) + 1e-12)
                    hits += t > 2.02
                out.append({"slots": S, "samples_per_cell": k, "effect_pts": int(e * 100), "power": round(hits / n_sim, 2)})
    return {"mode": mode, "domain": domain or "all", "baseline_options_only_N": round(p0, 3), "sd_slot_logit": round(sd_slot, 3),
            "solves_per_item": n_solves_per_item, "grid": out}


def write_report(outdir, res, power, mock):
    lines = []
    if mock:
        lines += ["# MOCK RUN — synthetic outputs, not data", "",
                  "Every number below comes from the offline mock client. It tests the code path only.", ""]
    else:
        lines += ["# Results", ""]
    lines += [f"Items: {res['n_items']}  ·  solver parse rate: {res['solver_parse_rate']}", "", "## By condition", ""]
    tab = pd.DataFrame(res["by_condition"])
    lines += [tab.to_markdown(index=False), "", "## Contrasts (options-only accuracy, paired by slot; cluster bootstrap)", ""]
    for k, v in res["contrasts"].items():
        a = v["all"]
        g = v.get("gee_options_only") or {}
        lines.append(f"- **{k}**: Δ options-only = {a['diff_options_only']} {a['ci95']} over {a['n_slots']} slots; "
                     f"Δ stem-cue rate = {a['diff_stem_cue_rate']} {a['stem_cue_ci95']}; GEE OR = {g.get('odds_ratio')} "
                     f"{g.get('ci95')} p = {g.get('p')}")
    lines += ["", f"Primary contrast by slot type: {json.dumps(res['primary_by_slot_type'])}",
              f"H2 notes overlap (R − W): {json.dumps(res['H2_notes_overlap_R_minus_W'])}", "",
              "## Judge agreement", "", json.dumps(res["judge_agreement"], indent=1), "",
              "## Power simulation for the main study", "",
              f"Baseline options-only accuracy (N): {power['baseline_options_only_N']}; slot SD (logit): {power['sd_slot_logit']}", "",
              pd.DataFrame(power["grid"]).pivot_table(index=["slots", "samples_per_cell"], columns="effect_pts",
                                                       values="power").to_markdown()]
    try:
        _, sl_, _ = item_table(outdir)
        ht, hc = hint_table(sl_)
        lines += ["", "## Hint % by company, solver and condition (invented domain)", "",
                  "Hint % = (accuracy − 0.25) / 0.75 × 100. 0 = guessing; 100 = always answerable without the knowledge.", "",
                  ht.to_markdown(index=False), "", hc.to_markdown()]
    except Exception as e:
        lines += ["", f"(hint table unavailable: {e})"]
    (outdir / "report.md").write_text("\n".join(lines))
    (outdir / "results.json").write_text(json.dumps({"mock": mock, "results": res, "power": power}, indent=1, default=str))


def explore_contrasts(outdir, measures=("acc_options_only", "acc_full", "acc_mismatched", "stem_info", "key_longest",
                                        "notes_bigram_overlap", "deciding_fact_in_stem_both"), pairs=None):
    """Calibration-stage exploration: every contrast vs its baseline, per domain and per writer,
    paired by slot with a cluster bootstrap. Used to choose the pre-registered primary measure,
    so it is reported as exploratory."""
    df, sl, _ = item_table(outdir)
    df["stem_info"] = df.acc_full - df.acc_mismatched
    pairs = pairs or [(c, "NG" if c == "WG" else "N") for c in CONDITIONS if c != "N" and c in set(df.cond)]
    rows = []
    for c, base in pairs:
        for dom in sorted(df.domain.unique()):
            for wr in ["all"] + sorted(df.writer.unique()):
                d = df[(df.domain == dom) & ((df.writer == wr) if wr != "all" else True)]
                for m in measures:
                    a = d[d.cond == base].groupby("slot_key")[m].mean().astype(float)
                    b = d[d.cond == c].groupby("slot_key")[m].mean().astype(float)
                    diff, ci, n = cluster_boot_diff(a, b)
                    rows.append({"contrast": f"{c}-{base}", "domain": dom, "writer": wr, "measure": m,
                                 "base": round(float(a.mean()), 3), "cond": round(float(b.mean()), 3),
                                 "diff": round(diff, 3), "lo": round(ci[0], 3), "hi": round(ci[1], 3), "n_slots": n})
    return pd.DataFrame(rows)


def hint_table(sl, domain="fictional"):
    """Hint % = (accuracy - 0.25) / 0.75 x 100: 0 = no better than guessing, 100 = always answerable
    without the tested knowledge. Reported per writer company, solver and condition, with a slot-clustered CI."""
    d = sl[(sl.domain == domain) & sl["mode"].isin(["full", "options_only"])]
    rng = np.random.default_rng(0)
    rows = []
    for keys, g in d.groupby(["mode", "writer", "solver"]):
        m = g.groupby("slot").correct.mean().values
        b = rng.choice(m, (2000, len(m))).mean(1)
        h = lambda a: round((a - 0.25) / 0.75 * 100, 1)
        rows.append(dict(zip(["mode", "writer", "solver"], keys), hint=h(m.mean()), lo=h(np.percentile(b, 2.5)),
                         hi=h(np.percentile(b, 97.5)), n_answers=len(g)))
    by_cond = (d.groupby(["mode", "writer", "cond"]).correct.mean().sub(0.25).div(0.75).mul(100).round(0)
               .unstack("cond"))
    return pd.DataFrame(rows), by_cond
