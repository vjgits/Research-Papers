"""Part B analysis: learnable tells, rule-based test-taking tricks, teaching echo, near-repeats,
and the go/no-go rule fixed before the pilot ran (2026-10-06)."""
import json
import re

import numpy as np
import pandas as pd

from .features import bigrams, content
from .pipeline import read_jsonl
from .sessions import material

ABSOLUTE = re.compile(r"\b(always|never|only|all|none|must|cannot|can't|every|guarantee[sd]?)\b", re.I)
hint = lambda a: (a - 0.25) / 0.75 * 100

# Go/no-go rule, written before the pilot data existed.
GO_RULE = {
    "loop_valid_min": 0.95,          # share of requested questions that came back valid
    "key_check_min": 0.95,           # strong solver with the full material agrees with the key
    "tells_min_pts": 10.0,           # history solver minus no-history solver, rounds 5-7 pooled
    "trick_min_pts": 15.0,           # any rule-based trick: accuracy minus chance, in points
    "teach_echo_min": 0.20,          # share of post-teaching FT questions reusing teaching-only wording
}


def _split_ties(scores, key):
    m = max(scores.values())
    best = [k for k, v in scores.items() if v == m]
    return (key in best) / len(best)


def tricks(q, prior_keys, prior_wrong, teaching):
    o, key = q["options"], q["answer"]
    stem_c = set(content(q["stem"]))
    r = {
        "longest": _split_ties({k: len(v.split()) for k, v in o.items()}, key),
        "stem_overlap": _split_ties({k: len(stem_c & set(content(v))) for k, v in o.items()}, key),
    }
    if prior_keys:
        kw = set(w for t in prior_keys for w in content(t))
        dw = set(w for t in prior_wrong for w in content(t))
        r["like_earlier_answers"] = _split_ties({k: len(set(content(v)) & kw) - len(set(content(v)) & dw) for k, v in o.items()}, key)
    if teaching:
        tw = set(content(teaching))
        r["teaching_overlap"] = _split_ties({k: len(set(content(v)) & tw) for k, v in o.items()}, key)
    keep = [k for k, v in o.items() if not ABSOLUTE.search(v)] or list(o)
    r["drop_absolutes"] = (key in keep) / len(keep)
    return r


def analyze(outdir, write=True):
    trs = read_jsonl(outdir / "transcripts.jsonl")
    probes = pd.DataFrame(read_jsonl(outdir / "session_probes.jsonl") + read_jsonl(outdir / "session_probes_xsubj.jsonl"))
    res = {}
    # 1. loop validity
    n_req = sum(len(t["rounds"]) * 10 for t in trs)
    n_valid = sum(rd["n_valid"] for t in trs for rd in t["rounds"])
    res["loop_valid"] = round(n_valid / n_req, 3)
    res["n_sessions"], res["n_questions"] = len(trs), n_valid
    res["key_check"] = round(float(probes[probes.probe == "spec"].correct.mean()), 3)
    # 2. learnable tells: history vs no-history, same solver, same items
    pv = probes[probes.probe.isin(["hist", "nohist"])].pivot_table(index=["session", "round", "n", "solver"], columns="probe",
                                                                     values="correct", aggfunc="first").dropna().reset_index()
    pv["writer"] = pv.session.str.split("|").str[0]
    pv["stype"] = pv.session.str.split("|").str[2]
    by_round = pv.groupby("round")[["hist", "nohist"]].mean().mul(100).round(1)
    by_round["advantage"] = (by_round["hist"] - by_round["nohist"]).round(1)
    res["tells_by_round"] = by_round.reset_index().to_dict("records")
    late = pv[pv["round"] >= 5]
    sess_adv = late.groupby("session").apply(lambda g: (g["hist"].mean() - g["nohist"].mean()) * 100)
    boot = np.random.default_rng(0).choice(sess_adv.values, (4000, len(sess_adv))).mean(1)
    res["tells_adv_r5_7"] = {"pts": round(float(sess_adv.mean()), 1),
                             "ci95": [round(float(x), 1) for x in np.percentile(boot, [2.5, 97.5])], "n_sessions": len(sess_adv)}
    res["tells_by_writer"] = late.groupby("writer").apply(lambda g: round((g["hist"].mean() - g["nohist"].mean()) * 100, 1)).to_dict()
    if "hist_xsubj" in set(probes.probe):  # style-only control: history from the other subject, same writer
        px = probes[probes.probe.isin(["hist_xsubj", "nohist"])].pivot_table(index=["session", "round", "n", "solver"], columns="probe",
                                                                            values="correct", aggfunc="first").dropna().reset_index()
        lx = px[px["round"] >= 5]
        sx = lx.groupby("session").apply(lambda g: (g["hist_xsubj"].mean() - g["nohist"].mean()) * 100)
        bx = np.random.default_rng(0).choice(sx.values, (4000, len(sx))).mean(1)
        res["style_only_adv_r5_7"] = {"pts": round(float(sx.mean()), 1), "ci95": [round(float(x), 1) for x in np.percentile(bx, [2.5, 97.5])]}
    res["nohist_hint_pct"] = round(hint(pv["nohist"].mean()), 1)
    # 3. rule-based tricks, 4. teaching echo, 5. near-repeats
    trick_rows, echo_rows, dup_rows = [], [], []
    for t in trs:
        mat_bi = bigrams(content(material(t["subject"])))
        teach_after = {x["after_round"]: x["text"] or "" for x in t["teachings"]}
        prior_keys, prior_wrong, prior_stems, latest_teach = [], [], [], ""
        for rd in t["rounds"]:
            if rd["round"] - 1 in teach_after:
                latest_teach = teach_after[rd["round"] - 1]
            for q in rd["questions"]:
                tr = tricks(q, prior_keys, prior_wrong, latest_teach if t["stype"] == "FT" else "")
                trick_rows += [{"session": t["session"], "writer": t["writer"], "stype": t["stype"], "round": rd["round"],
                                "trick": k, "acc": v} for k, v in tr.items()]
                s = set(content(q["stem"]))
                dup_rows.append({"session": t["session"], "stype": t["stype"], "round": rd["round"],
                                 "max_jacc_prior": max([len(s & p) / max(1, len(s | p)) for p in prior_stems], default=0)})
                if latest_teach:
                    item_bi = bigrams(content(q["stem"] + " " + q["options"][q["answer"]]))
                    tbi = bigrams(content(latest_teach))
                    echo_rows.append({"session": t["session"], "writer": t["writer"], "round": rd["round"],
                                      "teach_only_bigrams": len((item_bi & tbi) - mat_bi), "shared_bigrams": len(item_bi & tbi)})
            prior_keys += [q["options"][q["answer"]] for q in rd["questions"]]
            prior_wrong += [v for q in rd["questions"] for k, v in q["options"].items() if k != q["answer"]]
            prior_stems += [set(content(q["stem"])) for q in rd["questions"]]
    tk = pd.DataFrame(trick_rows)
    res["tricks_hint_pct"] = tk.groupby("trick").acc.mean().apply(hint).round(1).to_dict()
    res["tricks_by_stype"] = tk.groupby(["trick", "stype"]).acc.mean().apply(hint).round(1).unstack().to_dict("index")
    res["tricks_by_writer"] = tk.groupby(["trick", "writer"]).acc.mean().apply(hint).round(1).unstack().to_dict("index")
    ec = pd.DataFrame(echo_rows)
    res["teach_echo_share"] = round(float((ec.teach_only_bigrams >= 1).mean()), 3) if len(ec) else None
    res["teach_echo_n"] = len(ec)
    # control: F-session questions in the same rounds scored against the matched FT session's teaching text
    ctrl = []
    for t in [x for x in trs if x["stype"] == "F"]:
        mate = next((x for x in trs if x["stype"] == "FT" and x["writer"] == t["writer"] and x["subject"] == t["subject"]
                     and x["rep"] == t["rep"]), None)
        if not mate:
            continue
        mat_bi = bigrams(content(material(t["subject"])))
        ta = {x["after_round"]: x["text"] or "" for x in mate["teachings"]}
        latest = ""
        for rd in t["rounds"]:
            if rd["round"] - 1 in ta:
                latest = ta[rd["round"] - 1]
            if not latest:
                continue
            for q in rd["questions"]:
                ib = bigrams(content(q["stem"] + " " + q["options"][q["answer"]]))
                ctrl.append(len((ib & bigrams(content(latest))) - mat_bi) >= 1)
    res["teach_echo_control_F"] = round(float(np.mean(ctrl)), 3) if ctrl else None
    tp = probes[probes.probe.isin(["teach", "teach_para"])]
    res["teach_probe_pct"] = tp.groupby("probe").correct.mean().mul(100).round(1).to_dict()
    dp = pd.DataFrame(dup_rows)
    res["near_repeat_share"] = round(float((dp[dp["round"] > 1].max_jacc_prior >= 0.5).mean()), 3)
    res["learner_correct_by_round"] = [round(float(np.mean([t["rounds"][i]["learner_correct"] for t in trs
                                                            if len(t["rounds"]) > i])), 2) for i in range(7)]
    # go / no-go
    g = GO_RULE
    passes = {"loop_valid": res["loop_valid"] >= g["loop_valid_min"], "key_check": res["key_check"] >= g["key_check_min"],
              "tells": res["tells_adv_r5_7"]["pts"] >= g["tells_min_pts"],
              "tricks": max(res["tricks_hint_pct"].values()) * 0.75 >= g["trick_min_pts"],   # hint% -> points above chance
              "teach_echo": (res["teach_echo_share"] or 0) >= g["teach_echo_min"]}
    res["go_rule"] = g
    res["passes"] = passes
    res["decision"] = "GO" if passes["loop_valid"] and passes["key_check"] and (passes["tells"] or passes["tricks"] or passes["teach_echo"]) else "NO-GO"
    if write:
        (outdir / "session_results.json").write_text(json.dumps(res, indent=1, default=str))
    return res, tk, ec, pv
