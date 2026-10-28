#!/usr/bin/env python3
"""ICP v0.5 runner: frozen history + live generation at decision points only, three arms, hard cost caps.

Phases (each writes to its own output directory; phases are never pooled):
  smoke   data/manifest_smoke.csv  -> outputs/smoke/
  pilot   data/manifest_pilot.csv  -> outputs/pilot/
  main    data/manifest_main.csv   -> outputs/main/
  replay  PRIVATE Utah case study  -> private_replay/outputs/   (cases: private_replay/data/replay_cases_v05.jsonl)

Every launch REQUIRES --max-cost-usd (hard cap for this launch). Before any call the runner checks
  (1) the OpenRouter ACCOUNT BALANCE (total credits - total usage, not the key limit) >= the launch cap, and
  (2) recorded v0.5 spend across all phases + this cap <= --global-cap (see --global-cap).
Usage:
  python3 run_v05.py --phase smoke --max-cost-usd 0.75
  python3 run_v05.py --phase pilot --max-cost-usd 2.50
  python3 run_v05.py --phase main  --max-cost-usd 35 --confirm-main
  python3 run_v05.py --phase replay --max-cost-usd 5 --slots A,B,C,D,E,F,G
  python3 run_v05.py --phase pilot --dry-run          (no calls; shows the queue)
"""
import argparse, csv, json, re, sys, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import arms_v05 as A  # noqa: E402
import engine_v05 as E  # noqa: E402

RUNNER_VERSION = "0.5.2"
STOP = threading.Event()
STATE_RE = re.compile(r"<state>\s*(\{.*?\})\s*</state>", re.S)
STATE_TAIL = re.compile(r"<state>.*\Z|```(?:json)?\s*\{[^`]*\"(?:registry|ledger)\"[^`]*\}\s*```", re.S)
S_EXTRA_TOKENS = 600  # S-arm replies may append the state; budgeted outside the reply cap
STATE_BUILDER_TOKENS = 3000  # v0.5.2: state-builder calls get at least 3000 tokens (smoke: DeepSeek state call truncated)
PHASE_DIRS = {"smoke": ROOT / "outputs/smoke", "pilot": ROOT / "outputs/pilot", "main": ROOT / "outputs/main",
              "replay": ROOT / "private_replay/outputs"}


def recorded_spend_all():
    total = 0.0
    files = list((ROOT / "outputs").glob("**/responses.jsonl")) + list((ROOT / "outputs").glob("**/errors.jsonl")) \
        + list((ROOT / "outputs").glob("**/judgments.jsonl")) + list((ROOT / "private_replay/outputs").glob("**/*.jsonl"))
    for f in files:
        if f.name not in ("responses.jsonl", "errors.jsonl", "judgments.jsonl"):
            continue
        for r in E.load_jsonl(f):
            if r.get("provenance", "LIVE_PROVIDER_API") == "LIVE_PROVIDER_API":
                total += float(r.get("cost_usd") or 0)
    return round(total, 4)


def parse_json_obj(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def run_rollout(row, case, cfg, pr, budget, out, post, live):
    arm, slot, run_id = row["arm"], row["model_slot"], row["run_id"]
    att = out / "attempts.jsonl"
    nonce = uuid.uuid4().hex
    E.append_jsonl(out / "starts.jsonl", {"run_id": run_id, "nonce": nonce, "time_utc": E.now()})
    system = A.system_for(arm)
    frozen = [{"role": m["role"], "text": m["text"]} for m in case["frozen"]]
    base = {"run_id": run_id, "case_id": case["case_id"], "tier": case["tier"], "condition": case["condition"], "arm": arm,
            "model_slot": slot, "requested_model": cfg["model"], "trial": int(row.get("trial", 1)), "nonce": nonce,
            "generation_params": cfg.get("params"), "system_sha256": E.sha_text(system),
            "frozen_sha256": E.sha_text(json.dumps(frozen, ensure_ascii=False)), "runner_version": RUNNER_VERSION,
            "runner_sha256": E.sha_file(__file__), "engine_sha256": E.sha_file(ROOT / "src/engine_v05.py"),
            "arms_sha256": E.sha_file(ROOT / "src/arms_v05.py"),
            "provenance": "LIVE_PROVIDER_API" if live else "MOCK_TEST_NOT_DATA"}
    calls, dps, state_log = [], [], []
    failed_cost = 0.0
    if arm == "S":
        cfg = json.loads(json.dumps(cfg))
        cfg["params"]["max_tokens"] = cfg["params"].get("max_tokens", 2000) + S_EXTRA_TOKENS
    state = None
    t0 = time.monotonic()
    status = "OK"
    independent = case.get("dp_mode") == "independent"
    snapshots = {}
    try:
        if arm == "S":
            prev = 0
            for cp in case["checkpoints"]:
                seg = frozen[prev:cp]
                transcript = "\n\n".join(f"{m['role'].upper()}: {m['text']}" for m in seg)
                user = (f"CURRENT STATE:\n{json.dumps(state, ensure_ascii=False) if state else '{}'}\n\n"
                        f"NEXT CONVERSATION SEGMENT (messages {prev + 1}-{cp}):\n{transcript}\n\nReturn the complete updated state JSON only.")
                bcfg = json.loads(json.dumps(cfg))
                bcfg["params"]["max_tokens"] = max(bcfg["params"].get("max_tokens", 2000), STATE_BUILDER_TOKENS)
                rec = E.call(post, bcfg, pr, budget, A.STATE_BUILDER_SYSTEM, [{"role": "user", "text": user}], set(), att, f"{run_id}#state@{cp}")
                calls.append(rec)
                new = parse_json_obj(rec["text"]) if rec["status"] in ("OK", "TRUNCATED") else None
                state_log.append({"checkpoint": cp, "status": rec["status"], "parsed": new is not None})
                if new is not None:
                    state = new
                snapshots[cp] = state
                prev = cp
        history = list(frozen)
        prev_dp_user_idx = None
        prev_cut = None
        for dp in case["dps"]:
            if STOP.is_set():
                status = "INCOMPLETE_STOPPED"
                break
            if independent:
                # real history up to this DP's cut; only this reply is generated; nothing carried forward
                cut = dp["history_upto"]
                snap = snapshots.get(max([c for c in snapshots if c <= cut], default=-1)) if arm == "S" else None
                shown = (A.state_block(snap) + dp["text"]) if arm == "S" else dp["text"]
                convo = frozen[:cut] + [{"role": "user", "text": shown}]
                marks = {cut - 1, len(convo) - 1} | ({prev_cut - 1} if prev_cut else set())
                prev_cut = cut
            else:
                shown = (A.state_block(state) + dp["text"]) if arm == "S" else dp["text"]
                convo = history + [{"role": "user", "text": shown}]
                marks = {len(frozen) - 1, len(convo) - 1}
                if prev_dp_user_idx is not None:
                    marks.add(prev_dp_user_idx)
            rec = E.call(post, cfg, pr, budget, system, convo, marks, att, f"{run_id}#{dp['dp']}")
            calls.append(rec)
            raw = rec["text"] or ""
            visible = STATE_TAIL.sub("", STATE_RE.sub("", raw)).strip() if arm == "S" else raw.strip()
            leaked_state = arm == "S" and ("<state>" in raw and not STATE_RE.search(raw))
            upd = None
            if arm == "S" and not independent:
                m = STATE_RE.search(raw)
                if m:
                    try:
                        upd = json.loads(m.group(1))
                        state = upd
                    except ValueError:
                        upd = None
            dps.append({"dp": dp["dp"], "role": dp["role"], "status": rec["status"], "finish": rec["finish"], "reply": visible,
                        "reply_raw": raw if arm == "S" else None, "state_updated": upd is not None, "state_parse_failed": bool(arm == "S" and leaked_state),
                        "usage": rec["usage"], "cost_usd": rec["cost_usd"], "returned_model": rec["returned_model"],
                        "upstream": rec["upstream"], "words": len(visible.split())})
            if not independent:
                history = history + [{"role": "user", "text": dp["text"]}, {"role": "assistant", "text": visible}]
                prev_dp_user_idx = len(history) - 2
            if rec["status"] not in ("OK", "TRUNCATED"):
                status = "DP_" + rec["status"]
                break
    except E.CapReached as e:
        STOP.set()
        status = "INCOMPLETE_CAP"
        print(f"[{slot}] COST CAP: {e}", flush=True)
    except E.Ambiguous as e:
        status = "AMBIGUOUS:" + str(e)
        failed_cost = getattr(e, "cost_usd", 0.0)
    except E.Fatal as e:
        status = "ERROR:" + str(e)
        failed_cost = getattr(e, "cost_usd", 0.0)
    cost = round(sum(c["cost_usd"] or 0 for c in calls) + failed_cost, 8)
    rec = {**base, "status": status if len(dps) == len(case["dps"]) or status != "OK" else "INCOMPLETE", "dps": dps,
           "n_dps_done": len(dps), "n_dps_planned": len(case["dps"]), "state_calls": state_log,
           "final_state": state if arm == "S" else None, "calls": [{k: v for k, v in c.items() if k != "text"} for c in calls],
           "cost_usd": cost, "failed_call_cost_usd": round(failed_cost, 8), "retry_of_error": bool(row.get("_retry")), "elapsed_seconds": round(time.monotonic() - t0, 2), "time_utc": E.now()}
    target = "responses.jsonl" if rec["status"] == "OK" else "errors.jsonl"
    E.append_jsonl(out / target, rec)
    return rec["status"], cost


def main(argv=None, post=None, get=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=list(PHASE_DIRS))
    ap.add_argument("--max-cost-usd", type=float, help="hard cap for THIS launch (required unless --dry-run)")
    ap.add_argument("--global-cap", type=float, default=50.0)
    ap.add_argument("--models", default=str(ROOT / "models_v05.json"))
    ap.add_argument("--manifest", default="")
    ap.add_argument("--cases", default="")
    ap.add_argument("--slots", default="")
    ap.add_argument("--arms", default="")
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--confirm-main", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--retry-errors", action="store_true", help="re-run runs recorded in errors.jsonl (not AMBIGUOUS)")
    ap.add_argument("--rerun-ambiguous", action="store_true")
    ap.add_argument("--skip-balance-check", action="store_true", help="tests only")
    a = ap.parse_args(argv)
    live = post is None
    if live:
        import requests
        post, get = requests.post, requests.get
    out = Path(a.output_dir) if a.output_dir else PHASE_DIRS[a.phase]
    out.mkdir(parents=True, exist_ok=True)
    models = json.loads(Path(a.models).read_text())["slots"]
    pricing = json.loads((ROOT / "pricing_snapshot_v05.json").read_text())
    cases_path = Path(a.cases) if a.cases else (ROOT / ("private_replay/data/replay_cases_v05.jsonl" if a.phase == "replay" else "data/cases_v05.jsonl"))
    cases = {c["case_id"]: c for c in E.load_jsonl(cases_path)}
    if a.phase == "replay":
        slots = a.slots.split(",") if a.slots else [s for s, m in models.items() if m.get("main", True)]
        rows = [{"run_id": f"v05replay-{cid}-{arm}-{s}-t1", "case_id": cid, "arm": arm, "model_slot": s, "trial": 1}
                for cid in cases for arm in A.ARMS for s in slots]
    else:
        mf = Path(a.manifest) if a.manifest else ROOT / f"data/manifest_{a.phase}.csv"
        rows = list(csv.DictReader(open(mf)))
    if a.slots:
        rows = [r for r in rows if r["model_slot"] in a.slots.split(",")]
    if a.arms:
        rows = [r for r in rows if r["arm"] in a.arms.split(",")]
    if a.phase == "main" and not (a.confirm_main or a.dry_run):
        raise SystemExit("Main run requires --confirm-main (after the PI approves the costed plan).")
    done = {r["run_id"] for r in E.load_jsonl(out / "responses.jsonl")}
    errs = {}
    for r in E.load_jsonl(out / "errors.jsonl"):
        errs[r["run_id"]] = r
    term = {r.get("nonce") for r in E.load_jsonl(out / "responses.jsonl") + E.load_jsonl(out / "errors.jsonl")}
    for st in E.load_jsonl(out / "starts.jsonl"):
        if st["nonce"] not in term and st["run_id"] not in done:
            E.append_jsonl(out / "errors.jsonl", {"run_id": st["run_id"], "nonce": st["nonce"], "status": "AMBIGUOUS:INTERRUPTED_AFTER_START",
                                                  "cost_usd": 0, "time_utc": E.now()})
            errs[st["run_id"]] = {"status": "AMBIGUOUS:INTERRUPTED_AFTER_START"}
    queue = []
    for r in rows:
        if r["run_id"] in done:
            continue
        e = errs.get(r["run_id"])
        if e:
            amb = str(e.get("status", "")).startswith("AMBIGUOUS")
            if amb and not a.rerun_ambiguous:
                continue
            if not amb and not a.retry_errors:
                continue
            r = dict(r, _retry=True)
        queue.append(r)
    by_slot = {}
    for r in queue:
        by_slot.setdefault(r["model_slot"], []).append(r)
    summary = {"phase": a.phase, "queued": len(queue), "by_slot": {s: len(v) for s, v in sorted(by_slot.items())},
               "output_dir": str(out)}
    if a.dry_run:
        print(json.dumps(summary, indent=1))
        return summary
    if a.max_cost_usd is None:
        raise SystemExit("--max-cost-usd is required for every live launch.")
    spent_all = recorded_spend_all()
    guard = E.global_guard(ROOT, get, a.max_cost_usd, a.global_cap, spent_all, skip_balance=a.skip_balance_check)
    if live:
        E.append_jsonl(ROOT / "budget_ledger.jsonl", {"time_utc": E.now(), "phase": a.phase, "launch_cap_usd": a.max_cost_usd,
                                                      **guard, "global_cap_usd": a.global_cap, "queued": len(queue)})
    budget = E.Budget(a.max_cost_usd)
    STOP.clear()

    def worker(slot):
        cfg = json.loads(json.dumps(models[slot]))
        if a.phase == "replay":  # private transcript: request zero-data-retention endpoints only
            cfg["params"].setdefault("provider", {})["zdr"] = True
        pr = E.price(pricing, cfg["model"])
        n = 0
        for r in by_slot[slot]:
            if STOP.is_set():
                break
            st, cost = run_rollout(r, cases[r["case_id"]], cfg, pr, budget, out, post, live)
            n += 1
            print(f"[{slot} {n}/{len(by_slot[slot])}] {r['run_id']}: {st} ${cost:.4f}  launch spend ${budget.spent:.3f}/{a.max_cost_usd}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, len(by_slot))) as ex:
        list(ex.map(worker, sorted(by_slot)))
    summary.update({"launch_spend_usd": round(budget.spent, 4), "responses_total": len(E.load_jsonl(out / "responses.jsonl")),
                    "errors_total": len(E.load_jsonl(out / "errors.jsonl")), "stopped_by_cap": STOP.is_set()})
    print(json.dumps(summary, indent=1))
    return summary


if __name__ == "__main__":
    main()
