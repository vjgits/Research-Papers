"""Study pipeline: write -> solve -> code -> features. Every stage is resumable
(cached calls) and writes plain JSONL so results can be inspected by hand."""
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import prompts as P
from .clients import parse_json, parse_letter
from .config import (CONDITIONS, FAMILY, JUDGE_MAX_OUT, JUDGES, PHASES, SLOTS_PER_CALL, SOLVE_MODES,
                     SOLVER_MAX_OUT, SOLVER_REASONING, SOLVERS, WRITER_MAX_OUT, WRITERS, cross_solvers)
from .features import item_features


def _pool(fn, jobs, workers):
    out, errors = [], []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn, j): j for j in jobs}
        for f in as_completed(futs):
            try:
                r = f.result()
                if r is not None:
                    out.extend(r if isinstance(r, list) else [r])
            except Exception as e:  # BudgetExceeded propagates below
                if type(e).__name__ == "BudgetExceeded":
                    ex.shutdown(cancel_futures=True)
                    raise
                errors.append({"job": str(futs[f])[:300], "error": str(e)[:500]})
    return out, errors


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def read_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def _valid(it, slot_ids):
    o = it.get("options")
    return (isinstance(o, dict) and sorted(o) == list("ABCD") and all(isinstance(v, str) and v.strip() for v in o.values())
            and it.get("answer") in list("ABCD") and it.get("slot") in slot_ids and isinstance(it.get("stem"), str))


# ---------------------------------------------------------------- write
def stage_write(client, phase, outdir, workers=6, writers=None):
    cfg = PHASES[phase]
    jobs = []
    for dom in cfg["domains"]:
        slots = P.BLUEPRINT[dom]["slots"][:cfg["slots_per_domain"]]
        for cond in cfg["conditions"]:
            for w in (writers or WRITERS):
                for s in range(cfg["samples"]):
                    for i in range(0, len(slots), SLOTS_PER_CALL):
                        jobs.append((dom, cond, w, s, slots[i:i + SLOTS_PER_CALL]))

    def run(job):
        dom, cond, w, s, chunk = job
        prompt = P.writer_prompt(dom, cond, chunk)
        ids = {c["slot"] for c in chunk}
        for attempt in range(2):
            r = client.call(w, prompt, WRITER_MAX_OUT, tag=f"write|s{s}|try{attempt}",
                            meta={"kind": "write", "cond": cond, "slots": chunk})
            try:
                items = [it for it in parse_json(r["text"])["items"] if _valid(it, ids)]
            except Exception:
                items = []
            if len(items) >= len(chunk) * 0.8:
                break
        n_attempts = attempt + 1
        rows, seen = [], set()
        for it in items:
            if it["slot"] in seen:
                continue
            seen.add(it["slot"])
            slot = next(c for c in chunk if c["slot"] == it["slot"])
            rows.append({"id": f"{w}|{dom}|{cond}|s{s}|{it['slot']}", "writer": w, "family": FAMILY[w], "domain": dom,
                         "cond": cond, "sample": s, "slot": it["slot"], "topic": slot["topic"], "weak_slot": slot["weak"],
                         "difficulty": slot["difficulty"], "stem": it["stem"], "options": it["options"],
                         "answer": it["answer"], "rationale": it.get("rationale", ""),
                         "writer_api_model": r.get("api_model"), "write_attempts": n_attempts, "writer_reasoning_tok": r.get("reasoning_tok", 0)})
        missing = sorted(ids - seen)
        return rows + [{"missing": True, "writer": w, "domain": dom, "cond": cond, "sample": s, "slot": m} for m in missing]

    rows, errors = _pool(run, jobs, workers)
    items = [r for r in rows if not r.get("missing")]
    _write_jsonl(outdir / "items.jsonl", sorted(items, key=lambda r: r["id"]))
    _write_jsonl(outdir / "write_missing.jsonl", [r for r in rows if r.get("missing")] + errors)
    return items


# ---------------------------------------------------------------- solve
def _shuffle(item):
    """Deterministic re-ordering of options so the writer's letter choice cannot help a solver."""
    rng = random.Random(item["id"])
    letters = list("ABCD")
    perm = letters[:]
    rng.shuffle(perm)  # new position i shows old option perm[i]
    opts = {new: item["options"][old] for new, old in zip(letters, perm)}
    key = letters[perm.index(item["answer"])]
    return opts, key


def stage_solve(client, items, outdir, workers=8):
    by_group = {}
    for it in items:
        by_group.setdefault((it["writer"], it["domain"], it["cond"], it["sample"]), []).append(it)
    jobs = []
    for grp, its in by_group.items():
        its = sorted(its, key=lambda r: r["slot"])
        n = len(its)
        for i, it in enumerate(its):
            opts, key = _shuffle(it)
            partner = its[(i + n // 2) % n] if n > 1 else it  # different slot, normally a different topic
            other_fam = "openai" if it["family"] == "anthropic" else "anthropic"
            for solver in cross_solvers(it["writer"]):
                for mode in SOLVE_MODES:
                    stem = partner["stem"] if mode == "mismatched" else it["stem"]
                    jobs.append((it, solver, mode, stem, opts, key, partner["id"] if mode == "mismatched" else None))
            if it["domain"] == "fictional" and not it.get("subject"):  # key validity check: strong cross-family solver with the reference
                jobs.append((it, SOLVERS[other_fam][-1], "with_spec", it["stem"], opts, key, None))

    def run(job):
        it, solver, mode, stem, opts, key, partner = job
        r = client.call(solver, P.solver_prompt(stem, opts, mode), SOLVER_MAX_OUT, tag=f"solve|{mode}|{it['id']}",
                        meta={"kind": "solve", "mode": mode, "key": key, "cue": it.get("_mock_cue")},
                        reasoning=SOLVER_REASONING)
        prompt = P.solver_prompt(stem, opts, mode)
        a = parse_letter(r["text"]) if len(r["text"].strip()) <= 3 else None
        forced = False
        if a is None:  # forced choice: one follow-up turn, flagged so it can be excluded in sensitivity analysis
            forced = True
            r2 = client.call(solver, "You must choose exactly one option. Reply with only one letter: A, B, C or D.",
                             SOLVER_MAX_OUT, tag=f"solve|{mode}|{it['id']}|forced",
                             history=[{"role": "user", "content": prompt}, {"role": "assistant", "content": r["text"] or "(no answer)"}],
                             meta={"kind": "solve", "mode": mode, "key": key}, reasoning=SOLVER_REASONING)
            a = parse_letter(r2["text"]) if len(r2["text"].strip()) <= 3 else None
        return {"id": it["id"], "solver": solver, "mode": mode, "key": key, "pred": a, "correct": a == key,
                "parsed": a is not None, "forced": forced, "partner": partner, "solver_api_model": r.get("api_model"),
                "solver_effort": r.get("effort"), "raw": r["text"][:40]}

    rows, errors = _pool(run, jobs, workers)
    _write_jsonl(outdir / "solves.jsonl", sorted(rows, key=lambda r: (r["id"], r["solver"], r["mode"])))
    _write_jsonl(outdir / "solve_errors.jsonl", errors)
    return rows


# ---------------------------------------------------------------- code (judges)
def stage_code(client, items, outdir, workers=8):
    jobs = [(it, j) for it in items for j in JUDGES]

    def run(job):
        it, judge = job
        opts, key = _shuffle(it)
        if it.get("subject"):  # session items: judge sees that subject's material, no learner notes
            from .sessions import material
            jp = P.judge_prompt("fictional", it["stem"], opts, key, ref_text=material(it["subject"]), notes="(none)",
                                real_ref=it["domain"] == "real")
        else:
            jp = P.judge_prompt(it["domain"], it["stem"], opts, key)
        r = client.call(judge, jp, JUDGE_MAX_OUT,
                        tag=f"judge|{it['id']}", meta={"kind": "judge", "cue": it.get("_mock_cue")},
                        reasoning="low")
        try:
            d = parse_json(r["text"])
            ok = True
        except Exception:
            d, ok = {}, False
        return {"id": it["id"], "judge": judge, "parsed": ok, **{k: d.get(k) for k in (
            "key_correct", "multiple_defensible", "deciding_fact_in_stem", "deciding_fact_quote", "stem_key_overlap",
            "overlap_words", "rule_echo", "rule_echo_quote", "explains_in_stem", "keyed_best_practice_register",
            "dominant_heuristic", "distractors")}}

    rows, errors = _pool(run, jobs, workers)
    _write_jsonl(outdir / "codes.jsonl", sorted(rows, key=lambda r: (r["id"], r["judge"])))
    _write_jsonl(outdir / "code_errors.jsonl", errors)
    return rows


def stage_features(items, outdir):
    rows = [{"id": it["id"], **item_features(it, P.LEARNER[it["domain"]]["notes"])} for it in items]
    _write_jsonl(outdir / "features.jsonl", rows)
    return rows


# ---------------------------------------------------------------- secondary tests
def stage_secondary(client, items, outdir, workers=6, n_groups=None):
    """Novelty, writer self-audit and pressure, run on the W condition as follow-up turns
    of the original writer conversation. Outputs are new item sets, scored by the same
    solve/code stages."""
    groups = {}
    for it in items:
        if it["cond"] == "W" and it["sample"] == 0:
            groups.setdefault((it["writer"], it["domain"]), []).append(it)
    jobs = []
    for (w, dom), its in list(groups.items())[:n_groups]:
        chunk = [s for s in P.BLUEPRINT[dom]["slots"] if s["slot"] in {i["slot"] for i in its}][:SLOTS_PER_CALL]
        first = P.writer_prompt(dom, "W", chunk)
        prior = json.dumps({"items": [{k: i[k] for k in ("slot", "stem", "options", "answer", "rationale")}
                                      for i in sorted(its, key=lambda r: r["slot"]) if i["slot"] in {c["slot"] for c in chunk}]})
        hist = [{"role": "user", "content": first}, {"role": "assistant", "content": prior}]
        jobs += [(w, dom, chunk, hist, "novelty", P.NOVELTY_FOLLOWUP),
                 (w, dom, chunk, hist, "audit", P.SELF_AUDIT_FOLLOWUP),
                 (w, dom, chunk, hist, "flawed", P.PRESSURE_FLAWED_REQUEST + " " + P.FORMAT),
                 (w, dom, chunk, hist, "flawed_pressure", P.PRESSURE_FLAWED_REQUEST + " " + P.LEARNER["pressure"] + " " + P.FORMAT)]

    def run(job):
        w, dom, chunk, hist, arm, msg = job
        r = client.call(w, msg, WRITER_MAX_OUT, tag=f"secondary|{arm}", history=hist,
                        meta={"kind": "write", "cond": "W", "slots": chunk, "followup": arm})
        try:
            d = parse_json(r["text"])
        except Exception:
            d = {}
        ids = {c["slot"] for c in chunk}
        out = []
        for it in d.get("items", []):
            if _valid(it, ids):
                s = next(c for c in chunk if c["slot"] == it["slot"])
                out.append({"id": f"{w}|{dom}|W:{arm}|s0|{it['slot']}", "writer": w, "family": FAMILY[w], "domain": dom,
                            "cond": f"W:{arm}", "sample": 0, "slot": it["slot"], "topic": s["topic"], "weak_slot": s["weak"],
                            "difficulty": s["difficulty"], "stem": it["stem"], "options": it["options"],
                            "answer": it["answer"], "rationale": it.get("rationale", ""), "arm": arm,
                            "changes": d.get("changes") if arm == "audit" else None})
        return out

    rows, errors = _pool(run, jobs, workers)
    _write_jsonl(outdir / "secondary_items.jsonl", rows)
    _write_jsonl(outdir / "secondary_errors.jsonl", errors)
    return rows
