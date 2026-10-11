"""Follow-up study (Addendum 2, drafted 2026-10-11): does asking for harder questions increase leakage, and does a
distractor-matching instruction reduce it?  Fresh data only: two NEW invented subjects never used before.

Design (confirmatory writers: claude-opus-5-5, gpt-5.6-sol):
  C     no-feedback session, exactly as the main run's C sessions (7 rounds x 10 questions, orders A/B)  18 reps/subject
  CFIX  the same, plus FIX_TEXT in every request                                                     10 reps/subject
Exploratory: gemini-3.1-pro-preview, C and CFIX, 4 reps/subject each (evaluated only by Anthropic/OpenAI models).

Per session: writer rounds + learner + 3-member panel (as main run), readiness turn, then two probes per round by each of
the two cross-family strong solvers: 'nohist' (no material: knowledge-free accuracy, KF) and 'spec' (with material: key
check). No history probes, item solves or judges: they are not needed for the registered hypotheses.

Waves = one replicate of every cell still needing it; before each wave its high-case cost must fit the remaining cap.
"""
import json
from concurrent.futures import ThreadPoolExecutor

from .pipeline import _write_jsonl, read_jsonl
from .sessions import ANSWER_FMT, _qblock, _shuffle_q, material, parse_batch_answers
from .sessions_v2 import order_for, probe_solvers, run_session

SUBJECTS_FU = ["ostrel", "velloran"]
CONFIRM_WRITERS = ["claude-opus-5-5", "gpt-5.6-sol"]
GEMINI_WRITER = "gemini-3.1-pro-preview"
REPS = {("confirm", "C"): 18, ("confirm", "CFIX"): 10, ("gemini", "C"): 4, ("gemini", "CFIX"): 4}
N_WAVES = max(REPS.values())


def design_wave(k):
    """Sessions of wave k (0-based rep index)."""
    out = []
    for sj in SUBJECTS_FU:
        for grp, writers in (("confirm", CONFIRM_WRITERS), ("gemini", [GEMINI_WRITER])):
            for w in writers:
                for st in ("C", "CFIX"):
                    if k < REPS[(grp, st)]:
                        out.append({"subject": sj, "writer": w, "stype": st, "rep": k, "order": order_for(sj, w, k), "group": grp})
    return out


def all_sessions():
    return [s for k in range(N_WAVES) for s in design_wave(k)]


def probe_lean(client, tr):
    rows = []
    for rd in tr["rounds"]:
        qs = rd["questions"]
        for q in qs:
            _shuffle_q(q, f"{tr['session']}|{rd['round']}|{q['n']}")
        if not qs:
            continue
        for solver in probe_solvers(tr["writer"]):
            probes = {"nohist": "Answer these multiple-choice questions. You have no study material; choose the most likely answer.\n\n"
                                + _qblock(qs) + ANSWER_FMT,
                      "spec": "Use this reference to answer.\n\nREFERENCE:\n" + material(tr["subject"]) + "\n\nQUESTIONS:\n"
                              + _qblock(qs) + ANSWER_FMT}
            for name, p in probes.items():
                r = client.call(solver, p, 4000, tag=f"probe2|{name}|{solver}|{tr['session']}|{rd['round']}",
                                meta={"kind": "batch_answer", "keys": [q["shown_key"] for q in qs], "probe": name,
                                      "stems": [q["stem"] for q in qs]}, reasoning="none")
                a = parse_batch_answers(r["text"], len(qs))
                rows += [{"session": tr["session"], "round": rd["round"], "n": q["n"], "probe": name, "solver": solver,
                          "pred": a.get(str(i)), "correct": a.get(str(i)) == q["shown_key"], "parsed": str(i) in a,
                          "key_is_longest": max(q["options"], key=lambda k: len(q["options"][k])) == q["answer"]}
                         for i, q in enumerate(qs, 1)]
    return rows


def run(client, ledger, outdir, wave_high, workers=12, log=print):
    trs_all, probes_all = [], []
    for k in range(N_WAVES):
        sess = design_wave(k)
        if ledger.spent + wave_high(sess) > ledger.budget:
            log(f"STOPPED before wave {k + 1}: spent ${ledger.spent:.2f} + wave high-case ${wave_high(sess):.2f} > cap ${ledger.budget:.2f}")
            break
        with ThreadPoolExecutor(workers) as ex:
            trs = list(ex.map(lambda s: run_session(client, s), sess))
        for t, s in zip(trs, sess):
            t["group"] = s["group"]
        with ThreadPoolExecutor(workers) as ex:
            pr = [r for rows in ex.map(lambda t: probe_lean(client, t), trs) for r in rows]
        trs_all += trs
        probes_all += pr
        _write_jsonl(outdir / "transcripts.jsonl", trs_all)
        _write_jsonl(outdir / "session_probes.jsonl", probes_all)
        log(f"[wave {k + 1}/{N_WAVES}] {len(sess)} sessions  spent ${ledger.spent:.2f}")
    return trs_all, probes_all
