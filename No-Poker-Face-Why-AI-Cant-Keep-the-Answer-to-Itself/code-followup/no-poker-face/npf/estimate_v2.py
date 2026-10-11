"""Cost estimate for Part B v2, built from the pilot's MEASURED per-call costs (runs/pilot_sessions/ledger.jsonl, 7,054
real calls on 2026-10-06) times the exact call counts of the new design. Gemini (not in the pilot) is priced from the
pilot's measured token counts for the same call type at Gemini rates, plus an assumption for thinking tokens.

Expected case: pilot means, Gemini thinking 0 (measured). High case: writer output +50%, Gemini thinking 150 tokens per call, every forced-choice
follow-up at Sonnet's pilot rate, every note non-empty. Prices: npf/config.py (read 2026-10-05/06).
"""
import json
from collections import defaultdict

import numpy as np

from .config import PRICES, RUNS, SOLVERS, other_family
from .sessions_v2 import XSUBJ_MATE, design


def _pilot():
    L = [json.loads(l) for l in (RUNS / "pilot_sessions" / "ledger.jsonl").read_text().splitlines()]
    by = defaultdict(list)
    writer_round = defaultdict(list)          # (writer, stype class, round) -> cost
    for r in L:
        t = r["tag"].split("|")
        if t[0] == "session":
            w, st, part = t[1], t[3], t[-1]
            if part.startswith("round"):
                writer_round[(w, "FT" if st == "FT" else "other", int(part[5:]))].append(r)
            else:
                by[("teach", r["model"])].append(r)
            continue
        kind = t[0] if t[0] not in ("probe", "solve") else f"{t[0]}:{t[1]}"
        if t[0] == "solve" and t[-1] == "forced":
            kind += "|forced"
        by[(kind, r["model"])].append(r)
    return L, by, writer_round


def _m(rows, f):
    return float(np.mean([f(r) for r in rows])) if rows else 0.0


def per_call_tables():
    L, by, wr = _pilot()
    cost = {k: _m(v, lambda r: r["cost_usd"]) for k, v in by.items()}
    tin = {k: _m(v, lambda r: r["in_tok"]) for k, v in by.items()}
    tout = {k: _m(v, lambda r: r["out_tok"]) for k, v in by.items()}
    wcost = {k: _m(v, lambda r: r["cost_usd"]) for k, v in wr.items()}
    wout = {k: _m(v, lambda r: r["out_tok"]) for k, v in wr.items()}
    return cost, tin, tout, wcost, wout, by


def _gem(model, tokens_in, vis_out, think):
    pi, po = PRICES[model]
    return (tokens_in * pi + (vis_out + think) * po) / 1e6


def estimate(subjects, stypes, reps, high=False):
    cost, tin, tout, wcost, wout, by = per_call_tables()
    G_LITE, G_STRONG = SOLVERS["google"]
    think = 150 if high else 0          # measured 0 thinking tokens at "minimal" on 3.1-flash-lite and 3.6-flash (2026-10-06)
    wmul = 1.5 if high else 1.0
    lines = defaultdict(float)
    calls = defaultdict(int)
    sess = design(subjects, stypes, reps)
    for s in sess:
        w, st, sj = s["writer"], s["stype"], s["subject"]
        ofam = other_family(w)
        cheap, strong = SOLVERS[ofam][0], SOLVERS[ofam][-1]
        cls = "FT" if st == "FT" else "other"
        # writer: 7 rounds at the pilot's measured per-round cost for that writer, type class and round
        for rnd in range(1, 8):
            c = wcost[(w, cls, rnd)]
            pi, po = PRICES[w]
            note = 60 * po / 1e6                                   # optional note field, ~60 tokens
            lines["writer rounds"] += c + (wmul - 1) * wout[(w, cls, rnd)] * po / 1e6 + note * (2 if high else 1)
            calls["writer rounds"] += 1
        if st == "FT":
            lines["writer teaching (FT)"] += 3 * cost[("teach", w)] * wmul
            calls["writer teaching (FT)"] += 3
        # readiness turn: round-7 input cost again (history is cached as in the pilot) + a short reply
        r7 = wcost[(w, cls, 7)] - wout[(w, cls, 7)] * PRICES[w][1] / 1e6
        ready_out = (300 if w.startswith("claude") else 900) * (2 if high else 1)
        lines["readiness turn"] += r7 + ready_out * PRICES[w][1] / 1e6
        calls["readiness turn"] += 1
        # main learner + panel (2 Gemini lite + 1 other-family cheap), 7 rounds
        lines["learner"] += 7 * cost[("learner", cheap)]
        lines["panel: other-family cheap"] += 7 * cost[("learner", cheap)]
        lines["panel: 2 x Gemini lite"] += 14 * _gem(G_LITE, tin[("learner", cheap)], 60, think)
        calls["learner"] += 7; calls["panel: other-family cheap"] += 7; calls["panel: 2 x Gemini lite"] += 14
        # probes: nohist 7, spec 7, hist 6 (+ teach, teach_para 3 each in FT) by the other-family strong solver AND Gemini strong
        probes = {"nohist": 7, "spec": 7, "hist": 6} | ({"teach": 3, "teach_para": 3} if st == "FT" else {})
        if XSUBJ_MATE.get(sj) in subjects:
            probes["hist_xsubj"] = 6
        for p, n in probes.items():
            k = (f"probe:{p}", strong)
            lines["probes: other-family strong"] += n * cost[k]
            lines["probes: Gemini strong"] += n * _gem(G_STRONG, tin[k], 50, think)
            calls["probes: other-family strong"] += n; calls["probes: Gemini strong"] += n
        if st == "FT":
            lines["teaching rewording (FT)"] += 3 * cost[("para", strong)]
            calls["teaching rewording (FT)"] += 3
        # per-item solves: 70 items x 3 modes x (2 other-family + 2 Gemini), plus forced-choice follow-ups at pilot rates
        for mode in ("full", "options_only", "mismatched"):
            for m in SOLVERS[ofam]:
                k = (f"solve:{mode}", m)
                fk = (f"solve:{mode}|forced", m)
                frate = len(by.get(fk, [])) / max(1, len(by[k]))
                if high:
                    frate = max(frate, len(by.get((f"solve:{mode}|forced", "claude-sonnet-5-5"), [])) / len(by[(f"solve:{mode}", "claude-sonnet-5-5")]))
                lines["item solves: other-family"] += 70 * (cost[k] + frate * (cost.get(fk) or cost[k]))
                calls["item solves: other-family"] += round(70 * (1 + frate))
            k = (f"solve:{mode}", strong)
            sonnet_forced = len(by[(f"solve:{mode}|forced", "claude-sonnet-5-5")]) / len(by[(f"solve:{mode}", "claude-sonnet-5-5")])
            frate = sonnet_forced if high else 0.05
            for g in (G_LITE, G_STRONG):
                lines["item solves: Gemini"] += 70 * (1 + frate) * _gem(g, tin[k] * 1.1, 2, think)
                calls["item solves: Gemini"] += round(70 * (1 + frate))
        # item judges on a 30% sample, both judges
        for j in ("claude-sonnet-5-5", "gpt-5.6-terra"):
            lines["item judges (30%)"] += 21 * cost[("judge", j)]
            calls["item judges (30%)"] += 21
        # reply judges: 7 notes + readiness; expected half the notes non-empty, high all
        units = 8 if high else 4.5
        for j in ("claude-sonnet-5-5", "gpt-5.6-terra"):
            pi, po = PRICES[j]
            lines["reply judges"] += units * (700 * pi + (200 if j.startswith("claude") else 500) * po) / 1e6
            calls["reply judges"] += round(units)
    total = sum(lines.values())
    return {"n_sessions": len(sess), "lines": dict(lines), "calls": dict(calls), "total": total, "per_session": total / len(sess)}


# Measured actual/estimate ratios from the v2 pilot (16 sessions, 2026-10-07); applied by estimate(..., calibrated=True).
V2_PILOT_RATIO = {"writer rounds": 7.46 / 5.77, "writer teaching (FT)": 7.46 / 5.77, "probes: other-family strong": 2.29 / 1.72,
                  "reply judges": 0.55 / 0.78, "teaching rewording (FT)": 2.29 / 1.72}


def calibrated(subjects, stypes, reps, high=False, judge_share=0.3):
    e = estimate(subjects, stypes, reps, high=high)
    lines = {k: v * V2_PILOT_RATIO.get(k, 1.0) for k, v in e["lines"].items()}
    lines["item judges (30%)"] *= judge_share / 0.3
    return {**e, "lines": lines, "total": sum(lines.values()), "per_session": sum(lines.values()) / e["n_sessions"]}


def pilot_check():
    """Sanity check: the same method applied to the pilot design (C, F, FT; 2 subjects; no panel/Gemini) vs the real spend."""
    cost, tin, tout, wcost, wout, by = per_call_tables()
    L, _, _ = _pilot()
    return round(sum(r["cost_usd"] for r in L), 2)
