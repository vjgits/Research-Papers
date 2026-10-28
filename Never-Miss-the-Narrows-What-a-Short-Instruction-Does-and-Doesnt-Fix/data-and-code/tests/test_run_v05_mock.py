#!/usr/bin/env python3
"""Mock tests for run_v05 (no network, no key). Every record they create is marked MOCK_TEST_NOT_DATA."""
import json, os, shutil, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import run_v05 as R  # noqa: E402
import engine_v05 as E  # noqa: E402

FAKE_KEY = "sk-or-MOCK-should-never-appear-in-outputs"
os.environ["OPENROUTER_API_KEY"] = FAKE_KEY
RESULTS = []


class Resp:
    def __init__(self, status, payload, headers=None):
        self.status_code, self._p, self.headers = status, payload, headers or {}
        self.ok = 200 <= status < 300

    def json(self):
        return self._p


class MockPost:
    def __init__(self, mode="ok"):
        self.mode, self.bodies = mode, []

    def __call__(self, url, headers=None, json=None, timeout=None):
        import requests
        self.bodies.append(json)
        if self.mode == "timeout":
            raise requests.exceptions.ReadTimeout("mock")
        if self.mode == "http502":
            return Resp(502, {"error": {"message": "bad gateway"}})
        last = json["messages"][-1]["content"]
        last = last if isinstance(last, str) else last[0]["text"]
        if "Return the complete updated state JSON only" in last:
            text = '{"registry":[{"name":"MOCK STAR","tier":"S"}],"ledger":[],"preferences":{},"open_decisions":[]}'
        else:
            sysc = json["messages"][0]["content"]
            systext = sysc[0]["text"] if isinstance(sysc, list) else sysc
            text = "Mock reply. <state>{\"registry\":[{\"name\":\"UPDATED\"}]}</state>" if "EXPLICIT PLANNING STATE" in systext else "Mock reply."
        if self.mode == "leak" and "EXPLICIT PLANNING STATE" in systext if "Return the complete updated state" not in last else False:
            text = "Here is the plan.\n<state>{\"registry\":[{\"name\":\"Grand Prismatic Overlook\""  # truncated, unclosed
        if self.mode == "empty":
            text = ""
        finish = "length" if self.mode in ("truncate", "leak") else "stop"
        return Resp(200, {"model": json["model"], "provider": "mock", "choices": [{"message": {"content": text}, "finish_reason": finish}],
                          "usage": {"prompt_tokens": 1000, "completion_tokens": 100, "cost": 0.001}})


def get_balance(amount):
    def g(url, headers=None, timeout=None):
        return Resp(200, {"data": {"total_credits": amount + 10, "total_usage": 10}})
    return g


def t(name, ok, detail=""):
    RESULTS.append({"test": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def tmp_manifest(rows, d):
    p = Path(d) / "m.csv"
    with open(p, "w") as f:
        f.write("run_id,case_id,arm,model_slot,trial\n")
        for r in rows:
            f.write(",".join(str(r[k]) for k in ("run_id", "case_id", "arm", "model_slot", "trial")) + "\n")
    return str(p)


def main():
    d = tempfile.mkdtemp()
    real_outputs = ROOT / "outputs"
    try:
        # 1. full rollouts, three arms, explicit + auto cache models, LH case
        rows = [{"run_id": f"mock-LH1-{arm}-{s}", "case_id": "LH1", "arm": arm, "model_slot": s, "trial": 1} for arm in ("B", "P", "S") for s in ("A", "E")]
        mp = MockPost()
        out = Path(d) / "o1"
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows, d), "--output-dir", str(out), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=mp, get=get_balance(100))
        resp = E.load_jsonl(out / "responses.jsonl")
        t("all 6 rollouts recorded OK", len(resp) == 6 and all(r["status"] == "OK" for r in resp), str([r["status"] for r in resp]))
        t("records marked MOCK_TEST_NOT_DATA", all(r["provenance"] == "MOCK_TEST_NOT_DATA" for r in resp))
        t("six DPs per LH rollout", all(r["n_dps_done"] == 6 for r in resp))
        exp = [b for b in mp.bodies if b["model"].startswith("anthropic/")]
        auto = [b for b in mp.bodies if b["model"].startswith("deepseek/")]
        nmarks = lambda b: sum(1 for m in b["messages"] if isinstance(m["content"], list) and m["content"][0].get("cache_control"))  # noqa: E731
        t("explicit-cache model: 1-4 cache breakpoints per call", all(1 <= nmarks(b) <= 4 for b in exp), str(sorted({nmarks(b) for b in exp})))
        t("auto-cache model: no cache_control blocks", all(nmarks(b) == 0 for b in auto))
        is_s_dp = lambda b: "EXPLICIT PLANNING STATE" in json.dumps(b["messages"][0])  # noqa: E731
        cfg_mt = {m["model"]: m["params"]["max_tokens"] for m in json.loads((ROOT / "models_v05.json").read_text())["slots"].values()}
        t("max_tokens = model's configured limit (+600 on S-arm replies; v0.5.2) and reasoning effort low",
          all(b["max_tokens"] == cfg_mt.get(b["model"], 2000) + (600 if is_s_dp(b) else 0) and b["reasoning"] == {"effort": "low"}
              for b in mp.bodies if "Return the complete updated state" not in json.dumps(b["messages"][-1])))
        t("data_collection deny sent", all(b.get("provider", {}).get("data_collection") == "deny" for b in mp.bodies))
        s_runs = [r for r in resp if r["arm"] == "S"]
        t("S arm: state built at checkpoints", all(len(r["state_calls"]) >= 2 and all(x["parsed"] for x in r["state_calls"]) for r in s_runs))
        s_dp_bodies = [b for b in mp.bodies if "EXPLICIT PLANNING STATE" in json.dumps(b["messages"][0]) and "PLANNING STATE]" in json.dumps(b["messages"][-1])]
        t("S arm: [PLANNING STATE] block shown with each DP", len(s_dp_bodies) == 12, str(len(s_dp_bodies)))
        t("S arm: <state> stripped from visible replies", all("<state>" not in dp["reply"] for r in s_runs for dp in r["dps"]))
        t("S arm: state updated from reply", all(r["final_state"] == {"registry": [{"name": "UPDATED"}]} for r in s_runs))
        hist_has_block = any("[PLANNING STATE]" in (m["content"] if isinstance(m["content"], str) else m["content"][0]["text"])
                             for b in mp.bodies for m in b["messages"][1:-1])
        t("S arm: old state blocks not carried in history", not hist_has_block)
        b_bodies = [b for b in mp.bodies if "PLANNING PROTOCOL" not in json.dumps(b["messages"][0])]
        t("B arm system prompt has no protocol", len(b_bodies) > 0)
        lh_dp = [b for b in mp.bodies if "Return the complete updated state" not in json.dumps(b["messages"][-1])]
        t("DP calls carry the full frozen history (>=108 msgs + system)", min(len(b["messages"]) for b in lh_dp) >= 110, str(min(len(b["messages"]) for b in lh_dp)))
        # 2. resume: nothing re-run
        mp2 = MockPost()
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows, d), "--output-dir", str(out), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=mp2, get=get_balance(100))
        t("resume skips completed runs", len(mp2.bodies) == 0)
        # 3. hard cap
        out3 = Path(d) / "o3"
        mp3 = MockPost()
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows, d), "--output-dir", str(out3), "--max-cost-usd", "0.02",
                "--skip-balance-check", "--global-cap", "1000"], post=mp3, get=get_balance(100))
        recs = E.load_jsonl(out3 / "responses.jsonl") + E.load_jsonl(out3 / "errors.jsonl")
        spent = sum(r.get("cost_usd") or 0 for r in recs)
        t("hard cap: launch spend never exceeds cap", spent <= 0.02 + 1e-9, f"spent={spent:.4f}")
        t("hard cap: stopped runs recorded INCOMPLETE_CAP", any(r["status"] == "INCOMPLETE_CAP" for r in recs))
        # 4. ambiguous read timeout: no automatic retry
        out4 = Path(d) / "o4"
        mp4 = MockPost("timeout")
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out4), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=mp4, get=get_balance(100))
        er = E.load_jsonl(out4 / "errors.jsonl")
        t("read timeout -> AMBIGUOUS, single attempt", len(mp4.bodies) == 1 and er and er[0]["status"].startswith("AMBIGUOUS"))
        mp4b = MockPost()
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out4), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=mp4b, get=get_balance(100))
        t("AMBIGUOUS not re-run without --rerun-ambiguous", len(mp4b.bodies) == 0)
        # 5. truncation recorded, rollout continues
        out5 = Path(d) / "o5"
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out5), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=MockPost("truncate"), get=get_balance(100))
        r5 = E.load_jsonl(out5 / "responses.jsonl")
        t("truncated DPs flagged and rollout continues", r5 and all(dp["status"] == "TRUNCATED" for dp in r5[0]["dps"]) and r5[0]["n_dps_done"] == 6)
        # 5b. 5xx not retried; failed call recorded at worst-case cost
        out5b = Path(d) / "o5b"
        mp5b = MockPost("http502")
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out5b), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=mp5b, get=get_balance(100))
        e5b = E.load_jsonl(out5b / "errors.jsonl")
        t("HTTP 502: single attempt, ERROR, worst-case cost recorded", len(mp5b.bodies) == 1 and e5b and e5b[0]["status"].startswith("ERROR")
          and e5b[0]["cost_usd"] > 0, f"attempts={len(mp5b.bodies)} cost={e5b[0]['cost_usd'] if e5b else None}")
        e4 = E.load_jsonl(out4 / "errors.jsonl")
        t("AMBIGUOUS timeout recorded at worst-case cost", e4 and e4[0]["cost_usd"] > 0)
        # 5c. malformed state block never leaks into the visible reply
        out5c = Path(d) / "o5c"
        srow = [r for r in rows if r["arm"] == "S" and r["model_slot"] == "E"][:1]
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(srow, d), "--output-dir", str(out5c), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=MockPost("leak"), get=get_balance(100))
        r5c = E.load_jsonl(out5c / "responses.jsonl")
        t("S arm: truncated/unclosed <state> stripped and flagged", r5c and all("Overlook" not in dp["reply"] and dp["state_parse_failed"] for dp in r5c[0]["dps"]))
        # 5d. empty reply -> EMPTY, rollout stops (not carried forward)
        out5d = Path(d) / "o5d"
        R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out5d), "--max-cost-usd", "5",
                "--skip-balance-check", "--global-cap", "1000"], post=MockPost("empty"), get=get_balance(100))
        e5d = E.load_jsonl(out5d / "errors.jsonl")
        t("empty reply -> DP_EMPTY and rollout stops", e5d and e5d[0]["status"] == "DP_EMPTY" and e5d[0]["n_dps_done"] == 1)
        # 5e. provider-usage baseline guard
        bp = ROOT / "budget_baseline.json"
        had = bp.exists()
        if not had:
            bp.write_text(json.dumps({"total_usage": 0.0}))
        try:
            def g2(url, headers=None, timeout=None):
                return Resp(200, {"data": {"total_credits": 100, "total_usage": 49.6}})
            R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(Path(d) / "o5e"), "--max-cost-usd", "1"],
                   post=MockPost(), get=g2)
            t("provider usage since baseline counts toward the global guard", False)
        except SystemExit as e:
            t("provider usage since baseline counts toward the global guard", "global cap" in str(e), str(e)[:90])
        finally:
            if not had:
                bp.unlink()
        t("mock launches never write the real budget ledger", not (ROOT / "budget_ledger.jsonl").exists() or
          all(json.loads(l).get("phase") != "pilot" or "spent_used_for_guard" in l for l in open(ROOT / "budget_ledger.jsonl")))
        # 6. balance check refuses
        out6 = Path(d) / "o6"
        try:
            R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(out6), "--max-cost-usd", "5",
                    "--global-cap", "1000"], post=MockPost(), get=get_balance(1.0))
            t("balance below cap refuses launch", False)
        except SystemExit as e:
            t("balance below cap refuses launch", "balance" in str(e), str(e)[:80])
        # 7. missing cap refuses
        try:
            R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(Path(d) / "o7"), "--skip-balance-check"],
                   post=MockPost(), get=get_balance(100))
            t("missing --max-cost-usd refuses", False)
        except SystemExit as e:
            t("missing --max-cost-usd refuses", "required" in str(e))
        # 8. main requires confirmation
        try:
            R.main(["--phase", "main", "--output-dir", str(Path(d) / "o8"), "--max-cost-usd", "1", "--skip-balance-check"], post=MockPost(), get=get_balance(100))
            t("main run requires --confirm-main", False)
        except SystemExit as e:
            t("main run requires --confirm-main", "confirm-main" in str(e))
        # 9. global cap
        os.makedirs(real_outputs / "_mocktmp", exist_ok=True)
        E.append_jsonl(real_outputs / "_mocktmp/responses.jsonl", {"cost_usd": 49.5, "provenance": "LIVE_PROVIDER_API"})
        try:
            R.main(["--phase", "pilot", "--manifest", tmp_manifest(rows[:1], d), "--output-dir", str(Path(d) / "o9"), "--max-cost-usd", "1",
                    "--skip-balance-check"], post=MockPost(), get=get_balance(100))
            t("global cap refuses when recorded spend + cap > 50", False)
        except SystemExit as e:
            t("global cap refuses when recorded spend + cap > 50", "global cap" in str(e))
        finally:
            shutil.rmtree(real_outputs / "_mocktmp", ignore_errors=True)
        # 10. key never written
        blob = "".join(p.read_text() for p in Path(d).rglob("*.jsonl"))
        t("API key never written to any output", FAKE_KEY not in blob)
        # 11. replay phase reads the private cases file when present
        rp = ROOT / "private_replay/data/replay_cases_v05.jsonl"
        if rp.exists():
            mp11 = MockPost()
            R.main(["--phase", "replay", "--slots", "B", "--arms", "B", "--output-dir", str(Path(d) / "o11"), "--max-cost-usd", "5",
                    "--skip-balance-check", "--global-cap", "1000"], post=mp11, get=get_balance(100))
            rr = E.load_jsonl(Path(d) / "o11/responses.jsonl")
            t("replay: one run per arm x model with 3 independent DPs", len(rr) == 1 and rr[0]["n_dps_done"] == 3)
            lens = [len(b["messages"]) for b in mp11.bodies]
            t("replay: each DP sees only real history up to its cut (no carry-forward)", lens == [235 + 1, 239 + 1, 251 + 1], str(lens))
            mp12 = MockPost()
            R.main(["--phase", "replay", "--slots", "A", "--arms", "S", "--output-dir", str(Path(d) / "o12"), "--max-cost-usd", "5",
                    "--skip-balance-check", "--global-cap", "1000"], post=mp12, get=get_balance(100))
            st = [b for b in mp12.bodies if "Return the complete updated state" in json.dumps(b["messages"][-1])]
            t("replay S arm: state built once over 5 checkpoints", len(st) == 5, str(len(st)))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    fails = [r for r in RESULTS if not r["ok"]]
    (ROOT / "docs/validation_runner_v05.json").write_text(json.dumps({"n": len(RESULTS), "n_fail": len(fails), "results": RESULTS}, indent=1))
    print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} mock tests passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parent))
    from fixture_snapshot import placeholder_snapshot
    with placeholder_snapshot():
        main()
