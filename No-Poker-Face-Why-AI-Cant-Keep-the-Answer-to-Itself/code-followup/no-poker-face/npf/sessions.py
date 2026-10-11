"""Part B: repeated study sessions that recreate real use.

A writer model quizzes a simulated learner for 7 rounds. The learner is a cross-family model holding
the study material with ~30% of rules removed, so its mistakes (weak areas) are real. Every learner
message is a fixed template; the writer is never told to avoid clues.

Session types:  C  no feedback, no teaching   ("another set")
                F  weak-area feedback          ("I got Q2, Q5 wrong (topics). Mix weak areas with general ones")
                FT feedback + teaching turns after rounds 2, 4, 6 ("teach me my weak areas with hints")
"""
import hashlib
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor

from .clients import parse_json
from .config import DATA, FAMILY, SOLVERS, WRITER_MAX_OUT
from .pipeline import _write_jsonl

SUBJECTS = {k: v for k, v in json.loads((DATA / "subjects.json").read_text()).items() if not k.startswith("_")}
DIFF = ["medium", "easy", "hard", "medium", "hard", "easy", "medium"]   # fixed schedule, rounds 1-7
TEACH_AFTER = {2, 4, 6}
N_ROUNDS = 7
N_Q = 10

FORMAT = ('Reply with only JSON: {"questions": [{"n": 1, "topic": "<short topic>", "stem": "...", '
          '"options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "<letter>"}]}')


def material(subject):
    return (DATA / SUBJECTS[subject]["file"]).read_text()


def learner_notes(subject):
    """Study material minus the rules the learner lacks (whole rule lines removed)."""
    lacks = set(SUBJECTS[subject]["learner_lacks"])
    keep = [l for l in material(subject).splitlines()
            if not any(re.match(rf"-\s*{re.escape(r)}\.", l.strip()) for r in lacks)]
    return "\n".join(keep)


def first_message(subject):
    return (f"I'm studying {SUBJECTS[subject]['name']} for an exam. The material is below. Quiz me: write {N_Q} "
            f"multiple-choice practice questions, four options each, one correct. Make them {DIFF[0]}.\n\n"
            f"MATERIAL:\n{material(subject)}\n\n{FORMAT}")


def next_message(stype, rnd, wrong, weak_so_far):
    d = DIFF[rnd - 1]
    if stype == "C":
        return f"Give me {N_Q} new questions. Make them {d}. Same JSON format."
    if wrong:
        w = ", ".join(f"Q{q['n']}" for q in wrong)
        topics = "; ".join(dict.fromkeys(q["topic"] for q in wrong))
        head = f"I got {w} wrong ({topics})."
    else:
        head = "I got all of them right." + (f" My weak areas so far: {'; '.join(weak_so_far)}." if weak_so_far else "")
    return f"{head} Give me {N_Q} new questions that mix my weak areas with general ones. Make them {d}. Same JSON format."


def teach_message(weak_so_far):
    t = "; ".join(weak_so_far) if weak_so_far else "the topics I got wrong"
    return f"Before the next set, teach me my weak areas ({t}) with hints so I remember them."


def learner_prompt(subject, qs):
    body = "\n\n".join(f"Q{q['n']}. {q['stem']}\n" + "\n".join(f"{k}) {v}" for k, v in q["options"].items()) for q in qs)
    return ("You are a student preparing for an exam. Answer using only your study notes below; they are incomplete, "
            "so guess when you are unsure.\n\nYOUR NOTES:\n" + learner_notes(subject) + "\n\nQUESTIONS:\n" + body +
            '\n\nReply with only JSON: {"answers": {"1": "<letter>", "2": "<letter>", ...}}')


def _valid(q):
    o = q.get("options")
    return (isinstance(o, dict) and sorted(o) == list("ABCD") and q.get("answer") in list("ABCD")
            and isinstance(q.get("stem"), str) and all(isinstance(v, str) and v.strip() for v in o.values()))


def run_session(client, sess):
    """sess: dict(subject, writer, stype, rep). Returns transcript dict."""
    subject, writer, stype, rep = sess["subject"], sess["writer"], sess["stype"], sess["rep"]
    sid = f"{writer}|{subject}|{stype}|r{rep}"
    learner = SOLVERS["openai" if FAMILY[writer] == "anthropic" else "anthropic"][0]
    hist, rounds, teachings, weak = [], [], [], []
    msg = first_message(subject)
    for rnd in range(1, N_ROUNDS + 1):
        r = client.call(writer, msg, WRITER_MAX_OUT, tag=f"session|{sid}|round{rnd}", history=hist,
                        meta={"kind": "session_write", "rnd": rnd, "stype": stype})
        hist = hist + [{"role": "user", "content": msg}, {"role": "assistant", "content": r["text"] or "(empty)"}]
        try:
            qs = [q for q in parse_json(r["text"]).get("questions", []) if _valid(q)]
        except Exception:
            qs = []
        for i, q in enumerate(qs, 1):
            q["n"] = q.get("n") or i
            q["topic"] = str(q.get("topic") or "unlabelled")[:80]
        # learner answers the round
        la = client.call(learner, learner_prompt(subject, qs), 400, tag=f"learner|{sid}|round{rnd}",
                         meta={"kind": "batch_answer", "keys": [q["answer"] for q in qs]}, reasoning="none") if qs else {"text": "{}"}
        try:
            ans = {str(k): v for k, v in parse_json(la["text"]).get("answers", {}).items()}
        except Exception:
            ans = {}
        wrong = [q for q in qs if ans.get(str(q["n"])) != q["answer"]]
        for q in qs:
            q["learner_answer"] = ans.get(str(q["n"]))
        if stype != "C":
            weak = list(dict.fromkeys(weak + [q["topic"] for q in wrong]))[-6:]
        rounds.append({"round": rnd, "difficulty": DIFF[rnd - 1], "request": msg, "n_valid": len(qs),
                       "questions": qs, "writer_cost": r.get("cost_usd"), "learner_correct": len(qs) - len(wrong)})
        if rnd == N_ROUNDS:
            break
        if stype == "FT" and rnd in TEACH_AFTER:
            tm = teach_message(weak)
            t = client.call(writer, tm, 6000, tag=f"session|{sid}|teach{rnd}", history=hist,
                            meta={"kind": "teach"})
            hist = hist + [{"role": "user", "content": tm}, {"role": "assistant", "content": t["text"] or "(empty)"}]
            teachings.append({"after_round": rnd, "request": tm, "text": t["text"]})
        msg = next_message(stype, rnd + 1, wrong, weak)
    return {"session": sid, **sess, "learner_model": learner, "rounds": rounds, "teachings": teachings}


# ---------------------------------------------------------------------- probes
def _qblock(qs, with_key=False):
    out = []
    for i, q in enumerate(qs, 1):
        s = f"Q{i}. {q['stem']}\n" + "\n".join(f"{k}) {v}" for k, v in q["shown_options"].items())
        if with_key:
            s += f"\nCorrect answer: {q['shown_key']}"
        out.append(s)
    return "\n\n".join(out)


def _shuffle_q(q, seed):
    rng = random.Random(seed)
    perm = list("ABCD")
    rng.shuffle(perm)
    q["shown_options"] = {new: q["options"][old] for new, old in zip("ABCD", perm)}
    q["shown_key"] = "ABCD"[perm.index(q["answer"])]


ANSWER_FMT = '\n\nReply with only JSON: {"answers": {"1": "<letter>", "2": "<letter>", ...}}'


def parse_batch_answers(text, n):
    """JSON {"answers": {...}} if present (last one wins); otherwise the last 'Qk: X' / 'k. X' letter given per question.
    Some solvers (Sonnet 5.5) reason in visible text before answering a batch."""
    try:
        objs = [m for m in re.finditer(r'\{\s*"answers"', text)]
        if objs:
            d = parse_json(text[objs[-1].start():])
            a = {str(k): str(v).strip().upper()[:1] for k, v in d.get("answers", {}).items()}
            if len(a) >= n:
                return a
    except Exception:
        pass
    a = {}
    for m in re.finditer(r"(?im)^\W*Q?(\d{1,2})\s*[:.)\-]\s*(?:.*?[\s(*→=-])?([ABCD])\b[)\s.*]*$", text):
        a[m.group(1)] = m.group(2)
    if len(a) < n:  # looser: any 'Qk ... → X' or 'Qk: X' token
        for m in re.finditer(r"Q(\d{1,2})\b[^\n]*?(?:answer|→|=|:)\s*\**([ABCD])\b", text):
            a.setdefault(m.group(1), m.group(2))
    return a


def probe_session(client, tr):
    """Batch probes per round, by the strong solver from the other family:
       nohist  - round items only
       hist    - earlier rounds' items WITH keys, then this round (no material): learnable tells
       spec    - full material + items: answer-key check
       teach   - latest teaching text only + items (FT, rounds after a teaching turn)
       teach_para - the same teaching reworded by another model + items"""
    solver = SOLVERS["openai" if FAMILY[tr["writer"]] == "anthropic" else "anthropic"][-1]
    rows = []
    prior = []
    teach_by_round = {t["after_round"] + 1: t["text"] for t in tr["teachings"]}
    para_cache = {}
    for rd in tr["rounds"]:
        qs = rd["questions"]
        for q in qs:
            _shuffle_q(q, f"{tr['session']}|{rd['round']}|{q['n']}")
        if not qs:
            continue
        probes = {"nohist": "Answer these multiple-choice questions. You have no study material; choose the most likely answer.\n\n"
                            + _qblock(qs) + ANSWER_FMT,
                  "spec": "Use this reference to answer.\n\nREFERENCE:\n" + material(tr["subject"]) + "\n\nQUESTIONS:\n" + _qblock(qs) + ANSWER_FMT}
        if prior:
            probes["hist"] = ("Below are earlier practice questions written by the same quiz-writer, with their correct answers. "
                              "You have no other study material. Then answer the new questions.\n\nEARLIER QUESTIONS:\n"
                              + _qblock(prior, with_key=True) + "\n\nNEW QUESTIONS:\n" + _qblock(qs) + ANSWER_FMT)
        t = teach_by_round.get(rd["round"])
        if t:
            if rd["round"] not in para_cache:
                pr = client.call(solver, "Rewrite this explanation in completely different words and sentence structures. Keep every fact; "
                                         "do not reuse distinctive phrases.\n\n" + t, 6000, tag=f"para|{tr['session']}|{rd['round']}",
                                 meta={"kind": "teach"}, reasoning="low")
                para_cache[rd["round"]] = pr["text"]
            probes["teach"] = "Your only study material is this explanation from a tutor:\n\n" + t + "\n\nQUESTIONS:\n" + _qblock(qs) + ANSWER_FMT
            probes["teach_para"] = ("Your only study material is this explanation from a tutor:\n\n" + para_cache[rd["round"]]
                                    + "\n\nQUESTIONS:\n" + _qblock(qs) + ANSWER_FMT)
        for name, p in probes.items():
            r = client.call(solver, p, 4000, tag=f"probe|{name}|{tr['session']}|{rd['round']}",
                            meta={"kind": "batch_answer", "keys": [q["shown_key"] for q in qs], "probe": name}, reasoning="none")
            a = parse_batch_answers(r["text"], len(qs))
            for i, q in enumerate(qs, 1):
                rows.append({"session": tr["session"], "round": rd["round"], "n": q["n"], "probe": name, "solver": solver,
                             "pred": a.get(str(i)), "correct": a.get(str(i)) == q["shown_key"], "parsed": str(i) in a})
        prior = prior + qs
    return rows


def run_all(client, sessions, outdir, workers=12):
    with ThreadPoolExecutor(workers) as ex:
        trs = list(ex.map(lambda s: run_session(client, s), sessions))
    _write_jsonl(outdir / "transcripts.jsonl", trs)
    with ThreadPoolExecutor(workers) as ex:
        probe_rows = [r for rows in ex.map(lambda t: probe_session(client, t), trs) for r in rows]
    _write_jsonl(outdir / "session_probes.jsonl", probe_rows)
    # flatten items for the per-item solver/judge stages (full, options-only, mismatched; cross-family)
    items = []
    for t in trs:
        for rd in t["rounds"]:
            for q in rd["questions"]:
                iid = f"{t['session']}|R{rd['round']}|Q{q['n']}"
                items.append({"id": iid, "session": t["session"], "writer": t["writer"], "family": FAMILY[t["writer"]],
                              "domain": "fictional", "subject": t["subject"], "cond": t["stype"], "sample": t["rep"],
                              "slot": f"R{rd['round']}Q{q['n']:02d}", "round": rd["round"], "difficulty": rd["difficulty"],
                              "topic": q["topic"], "weak_slot": None, "stem": q["stem"], "options": q["options"],
                              "answer": q["answer"], "learner_answer": q.get("learner_answer")})
    _write_jsonl(outdir / "items.jsonl", items)
    return trs, probe_rows, items


def probe_cross_subject(client, trs):
    """Style-only tells: the history comes from the SAME writer's matched session (same type and rep) on the
    OTHER invented subject, so no facts can transfer; only the writer's habits can."""
    rows = []
    jobs = []
    for tr in trs:
        mate = next((x for x in trs if x["writer"] == tr["writer"] and x["stype"] == tr["stype"] and x["rep"] == tr["rep"]
                     and x["subject"] != tr["subject"]), None)
        if not mate:
            continue
        solver = SOLVERS["openai" if FAMILY[tr["writer"]] == "anthropic" else "anthropic"][-1]
        for rd in tr["rounds"][1:]:
            qs = rd["questions"]
            prior = [q for r0 in mate["rounds"][:rd["round"] - 1] for q in r0["questions"]]
            for q in qs + prior:
                if "shown_key" not in q:
                    _shuffle_q(q, f"x|{q['stem'][:40]}")
            if not qs or not prior:
                continue
            p = ("Below are earlier practice questions written by the same quiz-writer on a DIFFERENT subject, with their correct "
                 "answers. You have no study material for the new subject. Then answer the new questions.\n\nEARLIER QUESTIONS:\n"
                 + _qblock(prior, with_key=True) + "\n\nNEW QUESTIONS:\n" + _qblock(qs) + ANSWER_FMT)
            jobs.append((tr, rd, qs, solver, p))

    def run(job):
        tr, rd, qs, solver, p = job
        r = client.call(solver, p, 4000, tag=f"probe|hist_xsubj|{tr['session']}|{rd['round']}",
                        meta={"kind": "batch_answer", "keys": [q["shown_key"] for q in qs], "probe": "hist_xsubj"}, reasoning="none")
        a = parse_batch_answers(r["text"], len(qs))
        return [{"session": tr["session"], "round": rd["round"], "n": q["n"], "probe": "hist_xsubj", "solver": solver,
                 "pred": a.get(str(i)), "correct": a.get(str(i)) == q["shown_key"], "parsed": str(i) in a}
                for i, q in enumerate(qs, 1)]
    with ThreadPoolExecutor(12) as ex:
        for r in ex.map(run, jobs):
            rows += r
    return rows
