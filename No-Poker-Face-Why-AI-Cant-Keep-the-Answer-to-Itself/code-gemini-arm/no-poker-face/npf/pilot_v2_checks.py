"""Scores the v2 pilot against the checks fixed in findings-paper1.md BEFORE the paid run (2026-10-07). Feasibility only."""
import json
import re

import numpy as np
import pandas as pd

from .pipeline import read_jsonl
from .sessions import SUBJECTS
from .sessions_v2 import CLAIMS, SCRIPTED_WRONG

EST_PER_SESSION = 1.043


def checks(outdir):
    trs = read_jsonl(outdir / "transcripts.jsonl")
    pr = pd.DataFrame(read_jsonl(outdir / "session_probes.jsonl"))
    codes = read_jsonl(outdir / "reply_codes.jsonl")
    led = [json.loads(l) for l in (outdir / "ledger.jsonl").read_text().splitlines()]
    study = [r for r in led if not r["tag"].startswith(("smoke", "manual"))]
    out = {}
    n_req = sum(len(t["rounds"]) * 10 for t in trs)
    out["valid_share"] = sum(rd["n_valid"] for t in trs for rd in t["rounds"]) / n_req
    inv = pr[pr.session.str.split("|").str[1].map(lambda s: SUBJECTS[s]["invented"]) & (pr.probe == "spec")]
    out["key_check_invented"] = float(inv.correct.mean())
    out["key_check_by_solver"] = inv.groupby("solver").correct.mean().round(3).to_dict()
    out["key_check_llmapi"] = float(pr[(pr.session.str.contains("|llmapi|", regex=False)) & (pr.probe == "spec")].correct.mean())
    pan = [a for t in trs for rd in t["rounds"] for q in rd["questions"] for a in q["panel"]]
    lea = [q["learner_answer"] for t in trs for rd in t["rounds"] for q in rd["questions"]]
    out["panel_parsed"] = float(np.mean([a in list("ABCD") for a in pan]))
    out["learner_parsed"] = float(np.mean([a in list("ABCD") for a in lea]))
    out["readiness_parsed"] = float(np.mean([t["readiness"]["label"] != "UNPARSED" for t in trs]))
    nonempty = [c for c in codes if not c["empty"]]
    out["reply_judge_parsed"] = float(np.mean([c["parsed"] for c in nonempty])) if nonempty else None
    ok_script = all(len(rd["reported_wrong"]) == min(SCRIPTED_WRONG[t["stype"]], rd["n_valid"])
                    for t in trs if t["stype"] in SCRIPTED_WRONG for rd in t["rounds"])
    ok_claims = all((CLAIMS.get(rd["round"], "@@") in rd["request"]) == (t["stype"] == "CLAIM" and rd["round"] >= 4)
                    for t in trs for rd in t["rounds"])
    out["scripted_feedback_exact"], out["claims_placed_exactly"] = ok_script, ok_claims
    imp = {}
    for t in trs:
        if t["stype"] == "IMP" and t["subject"] == "tarnball":
            acc = [rd["learner_correct"] / max(1, rd["n_valid"]) for rd in t["rounds"]]
            imp[t["writer"]] = round((np.mean(acc[3:]) - np.mean(acc[:3])) * 100, 1)
    out["IMP_check_pts_by_writer"] = imp
    out["IMP_check_pts"] = float(np.mean(list(imp.values()))) if imp else None
    out["spend_study_calls"] = round(sum(r["cost_usd"] for r in study), 2)
    out["spend_smoke"] = round(sum(r["cost_usd"] for r in led) - out["spend_study_calls"], 3)
    out["cost_per_session"] = round(out["spend_study_calls"] / len(trs), 3)
    out["cost_vs_estimate"] = round(out["cost_per_session"] / EST_PER_SESSION, 2)
    out["passes"] = {"valid>=95%": out["valid_share"] >= .95, "key_check_invented>=95%": out["key_check_invented"] >= .95,
                     "panel+learner parsed>=95%": min(out["panel_parsed"], out["learner_parsed"]) >= .95,
                     "readiness parsed>=90%": out["readiness_parsed"] >= .90,
                     "reply judge parsed>=95%": (out["reply_judge_parsed"] or 0) >= .95,
                     "scripted feedback exact": ok_script, "claims placed exactly": ok_claims,
                     "IMP check >= +10 pts": (out["IMP_check_pts"] or 0) >= 10,
                     "cost within +25%": out["cost_vs_estimate"] <= 1.25}
    out["proceed"] = all(out["passes"].values())
    (outdir / "pilot_v2_checks.json").write_text(json.dumps(out, indent=1, default=str))
    return out
