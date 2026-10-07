"""Offline tests for the expanded Part B (v2). No network, no spend. Mock outputs are synthetic and never data.

    python tests/test_v2.py
"""
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from npf import sessions_v2 as S2                                     # noqa: E402
from npf.clients import Client, Ledger, BudgetExceeded                 # noqa: E402
from npf.config import PHASES, cross_solvers, SOLVERS                  # noqa: E402
from npf.sessions import SUBJECTS, material                            # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


# ---------------------------------------------------------------- design
def test_design():
    cfg = PHASES["main_sessions"]
    d = S2.design(cfg["subjects"], cfg["stypes"], cfg["reps"])
    check("main design has 168 sessions", len(d) == 168, len(d))
    check("4 subjects x 2 writers x 7 types x 3 reps", Counter((x["subject"], x["writer"], x["stype"]) for x in d) == Counter(
        {(s, w, t): 3 for s in cfg["subjects"] for w in ["claude-opus-5-5", "gpt-5.6-sol"] for t in cfg["stypes"]}))
    for t in cfg["stypes"]:
        c = Counter(x["order"] for x in d if x["stype"] == t)
        check(f"orders balanced in {t} (12/12)", c == Counter({"A": 12, "B": 12}), c)
    for t in cfg["stypes"]:
        for w in ["claude-opus-5-5", "gpt-5.6-sol"]:
            c = Counter(x["order"] for x in d if x["stype"] == t and x["writer"] == w)
            if c != Counter({"A": 6, "B": 6}):
                check(f"orders balanced in {t} x {w}", False, c)
    for t in cfg["stypes"]:
        for s in cfg["subjects"]:
            c = Counter(x["order"] for x in d if x["stype"] == t and x["subject"] == s)
            if c != Counter({"A": 3, "B": 3}):
                check(f"orders balanced in {t} x {s}", False, c)
    check("orders balanced within type x writer and type x subject", True)
    p = PHASES["pilot_sessions_v2"]
    dp = S2.design(p["subjects"], p["stypes"], p["reps"])
    check("pilot design has 16 sessions", len(dp) == 16, len(dp))
    for t in p["stypes"]:
        c = Counter(x["order"] for x in dp if x["stype"] == t)
        check(f"pilot orders balanced in {t} (2/2)", c == Counter({"A": 2, "B": 2}), c)
    A, B = S2.ORDERS["A"], S2.ORDERS["B"]
    check("round 1 is medium in both orders", A[0] == B[0] == "medium")
    check("order B rounds 2-7 = order A reversed", B[1:] == A[1:][::-1])
    check("all five levels used in each order", set(A) == set(B) == {"easy", "medium", "hard", "trickier", "harder"})
    check("'harder than the last set' never in round 1", A[0] != "harder" and B[0] != "harder")


def test_subjects():
    for s, v in SUBJECTS.items():
        ids = S2.rule_ids(s)
        lacks = v["learner_lacks"]
        check(f"{s}: learner gaps are real rule IDs", set(lacks) <= set(ids), set(lacks) - set(ids))
        share = len(lacks) / len(ids)
        check(f"{s}: learner lacks ~30% ({share:.0%})", 0.25 <= share <= 0.36)
        notes = S2.notes_without(s, lacks)
        check(f"{s}: gapped notes drop exactly the lacked rules",
              all(not re.search(rf"(?m)^-\s*{r}\.", notes) for r in lacks) and len(S2.rule_ids(s)) - len(lacks) ==
              len(re.findall(r"(?m)^-\s*[A-Z]\d+\.", notes)))
        gaps = [S2.panel_gaps(s, g) for _, g in S2.PANEL]
        check(f"{s}: 3 distinct panel gap profiles ~30%", len({tuple(g) for g in gaps}) == 3 and all(len(g) == round(0.3 * len(ids)) for g in gaps))
        check(f"{s}: panel gaps reproducible", gaps == [S2.panel_gaps(s, g) for _, g in S2.PANEL])
    txt = " ".join(material(s) for s in SUBJECTS).lower()
    check("no certification-exam wording in references", not any(w in txt for w in ("exam question", "sample question", "official exam")))


def test_messages():
    m = S2.next_message("C", 2, "easy", [], [])
    check("C message has no feedback", "wrong" not in m and "right" not in m and "Make them easy." in m)
    wrong = [{"n": 2, "topic": "Ferries"}, {"n": 5, "topic": "Pins"}]
    m = S2.next_message("F", 3, "harder", wrong, ["Ferries"])
    check("F message reports wrong Qs and topics", m.startswith("I got Q2, Q5 wrong (Ferries; Pins).") and "harder than the last set" in m)
    claims = [S2.next_message("CLAIM", r, "medium", wrong, []) for r in range(2, 8)]
    check("CLAIM: no claim in rounds 2-3", all(not any(c in m for c in S2.CLAIMS.values()) for m in claims[:2]))
    check("CLAIM: escalating claims in rounds 4-7", all(S2.CLAIMS[r] in claims[r - 2] for r in range(4, 8)))
    check("CLAIM vs FAIL-HI messages differ only by the claim",
          all(S2.next_message("CLAIM", r, "hard", wrong, []).replace(" " + S2.CLAIMS[r], "") == S2.next_message("FAIL-HI", r, "hard", wrong, [])
              for r in range(4, 8)))
    qs = [{"n": i, "topic": f"t{i}"} for i in range(1, 11)]
    for st, k in (("FAIL-LO", 1), ("FAIL-HI", 7), ("CLAIM", 7)):
        rw, scr = S2.reported_wrong(st, "sid", 3, qs, [])
        check(f"{st}: scripted {k} of 10 wrong regardless of real answers", len(rw) == k and scr)
    rw, scr = S2.reported_wrong("F", "sid", 3, qs, qs[:2])
    check("F: reports the real wrong answers", rw == qs[:2] and not scr)
    check("first message carries the material and the note field", "MATERIAL:" in S2.first_message("tarnball", "medium") and '"note"' in S2.FORMAT)
    check("readiness label parser", [S2.readiness_label(x) for x in ("READY - yes", "NOT READY.", "**Unsure** maybe", "Yes you are")] ==
          ["READY", "NOT READY", "UNSURE", "UNPARSED"])


def test_solvers():
    for w in ("claude-opus-5-5", "gpt-5.6-sol"):
        sv = cross_solvers(w)
        fam = "anthropic" if w.startswith("claude") else "openai"
        check(f"{w}: no same-family solver", not any(s.startswith("claude" if fam == "anthropic" else "gpt") for s in sv), sv)
        check(f"{w}: Gemini solvers included", set(SOLVERS["google"]) <= set(sv))
        pm = S2.panel_models(w)
        check(f"{w}: panel = 2 Gemini + 1 other-family cheap", pm[:2] == ["gemini-3.1-flash-lite"] * 2 and pm[2] == SOLVERS["openai" if fam == "anthropic" else "anthropic"][0], pm)


def test_google_client():
    c = Client(ROOT / "runs" / "_test_cache", Ledger(ROOT / "runs" / "_test_cache" / "l.jsonl", 1.0))
    seen = {}

    def fake_post(url, h, body):
        seen.update(url=url, body=body, h=h)
        return {"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": "B"}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 1, "thoughtsTokenCount": 20}, "modelVersion": "gemini-3.6-flash"}
    import os
    os.environ.setdefault("GEMINI_API_KEY", "test")
    c._post = fake_post
    r = c._google("gemini-3.6-flash", [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}, {"role": "user", "content": "q2"}], 32, "none")
    check("gemini: roles mapped (assistant -> model)", [x["role"] for x in seen["body"]["contents"]] == ["user", "model", "user"])
    check("gemini: minimal thinking requested for solvers", seen["body"]["generationConfig"].get("thinkingConfig") == {"thinkingLevel": "minimal"})
    check("gemini: thought parts excluded from text", r["text"] == "B")
    check("gemini: thoughts billed as output", r["out_tok"] == 21 and abs(r["cost_usd"] - (100 * 0.75 + 21 * 3.75) / 1e6) < 1e-12)
    shutil.rmtree(ROOT / "runs" / "_test_cache", ignore_errors=True)


# ---------------------------------------------------------------- end-to-end mock
def run(args):
    return subprocess.run([sys.executable, "run.py"] + args, cwd=ROOT, capture_output=True, text=True, timeout=3000)


def test_mock_main_small():
    """All 7 types x 4 subjects x 2 writers x 1 rep (56 sessions) in mock mode."""
    PHASES["_mock_all"] = dict(PHASES["main_sessions"], reps=1)
    out = ROOT / "runs" / "_mock_all_mock"
    shutil.rmtree(out, ignore_errors=True)
    from npf.clients import Client, Ledger
    from npf.pipeline import stage_solve, stage_code
    from npf.session_analysis_v2 import analyze
    client = Client(out / "cache", Ledger(out / "ledger.jsonl", 1e9), mock=True)
    sess = S2.design(PHASES["_mock_all"]["subjects"], PHASES["_mock_all"]["stypes"], 1)
    trs, probes, items = S2.run_all(client, sess, out)
    stage_solve(client, items, out)
    res, rt, _ = analyze(out, mock=True)
    check("56 mock sessions, 7 rounds each", len(trs) == 56 and all(len(t["rounds"]) == 7 for t in trs))
    check("every session has a readiness reply", all(t["readiness"]["label"] != "UNPARSED" for t in trs))
    check("panel answered every question (3 members)", all(len(q["panel"]) == 3 and all(q["panel"]) for t in trs for rd in t["rounds"] for q in rd["questions"]))
    for st, k in (("FAIL-LO", 1), ("FAIL-HI", 7), ("CLAIM", 7)):
        ok = all(len(rd["reported_wrong"]) == k and rd["scripted"] for t in trs if t["stype"] == st for rd in t["rounds"])
        check(f"mock {st}: every round reports exactly {k} wrong", ok)
    imp = [rd["learner_full_material"] for t in trs if t["stype"] == "IMP" for rd in t["rounds"]]
    check("IMP: learner gets full material from round 4 only", imp == [False, False, False, True, True, True, True] * (len(imp) // 7))
    check("IMP never set for other types", not any(rd["learner_full_material"] for t in trs if t["stype"] != "IMP" for rd in t["rounds"]))
    req = {t["session"]: [rd["request"] for rd in t["rounds"]] for t in trs}
    check("CLAIM requests carry claims in rounds 4-7 only",
          all(all((S2.CLAIMS.get(r + 1, "@@") in m) == (r + 1 >= 4) for r, m in enumerate(v)) for s, v in req.items() if "|CLAIM|" in s))
    check("no claim text in non-CLAIM sessions", not any(c in m for s, v in req.items() if "|CLAIM|" not in s for m in v for c in S2.CLAIMS.values()))
    check("FT has 3 teaching turns, others none", all(len(t["teachings"]) == (3 if t["stype"] == "FT" else 0) for t in trs))
    lv = {t["session"]: [rd["difficulty"] for rd in t["rounds"]] for t in trs}
    check("each session follows its assigned order", all(lv[t["session"]] == S2.ORDERS[t["order"]] for t in trs))
    check("level text in every request", all(S2.LEVEL_TEXT[rd["difficulty"]] in rd["request"] for t in trs for rd in t["rounds"]))
    pr = {(p["solver"], p["probe"]) for p in probes}
    check("probes run by both cross-family strong solvers", {s for s, _ in pr} == {"gpt-5.6-terra", "claude-sonnet-5-5", "gemini-3.6-flash"})
    xs = [json.loads(l) for l in (out / "session_probes_xsubj.jsonl").read_text().splitlines()]
    check("style-only probe skips llmapi, covers tarnball", not any("|llmapi|" in r["session"] for r in xs) and any("|tarnball|" in r["session"] for r in xs))
    codes = [json.loads(l) for l in (out / "reply_codes.jsonl").read_text().splitlines()]
    check("reply codes: 2 judges x 8 units per session", len(codes) == 56 * 8 * 2, len(codes))
    check("analysis flags MOCK", res["MOCK_NOT_DATA"] is True)
    b1 = res["B1_failure_easing"]["invented_subjects"]["bootstrap"]
    check("planted failure-easing recovered (mock: FAIL-HI easier)", b1 and b1["diff"] > 0, b1)
    check("planted claim effect recovered (mock: CLAIM more READY)", res["B2_claimed_mastery"]["risk_diff_pts"] > 0, res.get("B2_claimed_mastery"))
    check("planted level effect recovered (hard < easy)", res["hard_minus_easy_PD"]["mean"] < 0, res["hard_minus_easy_PD"])
    check("teaching echo computed with F control", res["pilot_measures"].get("teach_echo_control_F") is not None, res.get("pilot_measures"))
    check("style-only control computed", res["pilot_measures"].get("style_only_adv_r5_7") is not None)
    check("Part A trigger evaluated", res["part_A_trigger"]["estimate"] is not None)
    check("IMP analyses computed", res["IMP_manipulation_learner_acc_r4_7"] is not None)
    solved = [json.loads(l) for l in (out / "solves.jsonl").read_text().splitlines()]
    check("each item solved by 4 cross-family solvers x 3 modes", Counter(Counter(r["id"] for r in solved).values()) == Counter({12: len(items)}))
    shutil.rmtree(out, ignore_errors=True)


def test_budget_cap():
    out = ROOT / "runs" / "pilot_sessions_v2_mock"
    shutil.rmtree(out, ignore_errors=True)
    r = run(["sessions", "--phase", "pilot_sessions_v2", "--mock", "--budget", "1.0"])
    led = [json.loads(l) for l in (out / "ledger.jsonl").read_text().splitlines()] if (out / "ledger.jsonl").exists() else []
    spent = sum(x["cost_usd"] for x in led)
    check("CLI: cap below one wave stops before any call", "STOPPED before wave 1" in r.stdout and spent == 0, r.stdout[-300:])
    # in-run cap with 12 parallel workers: in-flight reservations must keep total spend under the cap
    from npf.pipeline import read_jsonl  # noqa: F401
    out2 = ROOT / "runs" / "_cap_mock"
    shutil.rmtree(out2, ignore_errors=True)
    led = Ledger(out2 / "ledger.jsonl", 1.0)
    client = Client(out2 / "cache", led, mock=True)
    stopped = False
    try:
        S2.run_all(client, S2.design(["tarnball", "llmapi"], ["IMP", "CLAIM", "FAIL-LO", "FAIL-HI"], 1), out2, workers=12)
    except BudgetExceeded:
        stopped = True
    total = sum(json.loads(l)["cost_usd"] for l in (out2 / "ledger.jsonl").read_text().splitlines())
    check("in-run cap raises BudgetExceeded (12 workers)", stopped)
    check(f"in-run spend under the cap (${total:.3f} <= $1.00)", total <= 1.0)
    shutil.rmtree(out2, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    r = run(["sessions", "--phase", "pilot_sessions_v2"])
    check("real run refuses to start without --budget", r.returncode != 0 and "budget" in (r.stderr + r.stdout).lower())


def test_waves():
    """Main run in mock with a cap that fits two replicate waves: it must stop BEFORE wave 3, leaving 2 complete reps."""
    out = ROOT / "runs" / "main_sessions_mock"
    shutil.rmtree(out, ignore_errors=True)
    r = run(["sessions", "--phase", "main_sessions", "--mock", "--budget", "150", "--stages", "write"])
    trs = [json.loads(l) for l in (out / "transcripts.jsonl").read_text().splitlines()]
    check("wave stop message printed", "STOPPED before wave 3" in r.stdout, r.stdout[-400:] + r.stderr[-400:])
    check("2 complete replicate waves = 112 sessions", len(trs) == 112, len(trs))
    c = Counter((t["subject"], t["writer"], t["stype"]) for t in trs)
    check("every subject x writer x type cell has exactly 2 reps", set(c.values()) == {2} and len(c) == 56)
    led = sum(json.loads(l)["cost_usd"] for l in (out / "ledger.jsonl").read_text().splitlines())
    check(f"mock spend under the cap (${led:.2f} <= $150)", led <= 150)
    shutil.rmtree(out, ignore_errors=True)


def test_v1_regression():
    """Re-analysis of the real pilot (v1) must still give the logged numbers after the multi-solver change."""
    from npf.session_analysis import analyze
    res, *_ = analyze(ROOT / "runs" / "pilot_sessions", write=False)
    check("v1 pilot: key check 97.7%", res["key_check"] == 0.977, res["key_check"])
    check("v1 pilot: tells +29.4", res["tells_adv_r5_7"]["pts"] == 29.4, res["tells_adv_r5_7"])
    check("v1 pilot: style-only -4.2", res["style_only_adv_r5_7"]["pts"] == -4.2, res.get("style_only_adv_r5_7"))
    check("v1 pilot: near-repeats 21.4%", res["near_repeat_share"] == 0.214, res["near_repeat_share"])
    check("v1 pilot: decision GO", res["decision"] == "GO")


if __name__ == "__main__":
    for t in (test_design, test_subjects, test_messages, test_solvers, test_google_client, test_v1_regression,
              test_budget_cap, test_waves, test_mock_main_small):
        print(f"--- {t.__name__}")
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            check(t.__name__ + " raised", False, repr(e)[:300])
    print(f"\n{len(FAILS)} failure(s)" + (": " + ", ".join(FAILS) if FAILS else ""))
    sys.exit(1 if FAILS else 0)
