"""Model clients with a disk cache (no call is ever paid for twice), a spend ledger
and a hard budget cap. A MockClient lets the whole pipeline run offline; mock
outputs are synthetic and must never be reported as results."""
import hashlib
import json
import os
import random
import re
import threading
import time
from pathlib import Path

import requests

from .config import PRICES, PROVIDER


class BudgetExceeded(RuntimeError):
    pass


def cost_of(model, tin, tout):
    pi, po = PRICES[model]
    return (tin * pi + tout * po) / 1e6


class Ledger:
    """Append-only record of every paid call; enforces the approved budget."""

    def __init__(self, path, budget_usd):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.budget = budget_usd
        self.lock = threading.Lock()
        self.spent = 0.0
        self.reserved = 0.0
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.spent += json.loads(line)["cost_usd"]

    def check(self, est):
        """Reserve a call's worst-case cost before it runs, so parallel workers cannot jointly overshoot the cap."""
        with self.lock:
            if self.spent + self.reserved + est > self.budget:
                raise BudgetExceeded(f"spent ${self.spent:.2f} + in flight ${self.reserved:.2f} + next call ~${est:.3f} "
                                     f"exceeds approved ${self.budget:.2f}")
            self.reserved += est

    def release(self, est):
        with self.lock:
            self.reserved = max(0.0, self.reserved - est)

    def add(self, rec, est=0.0):
        with self.lock:
            self.reserved = max(0.0, self.reserved - est)
            self.spent += rec["cost_usd"]
            with self.path.open("a") as f:
                f.write(json.dumps(rec) + "\n")


class Client:
    def __init__(self, cache_dir, ledger, mock=False, workers_note=""):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger
        self.mock = mock
        self.s = requests.Session()
        self.openai_effort_fallback = {}

    # -- public ----------------------------------------------------------------
    def call(self, model, prompt, max_out, tag, meta=None, history=None, reasoning=None):
        """Returns dict(text, in_tok, out_tok, reasoning_tok, cost_usd, model, cached)."""
        msgs = (history or []) + [{"role": "user", "content": prompt}]
        key = hashlib.sha256(json.dumps([model, msgs, max_out, reasoning, tag], sort_keys=True).encode()).hexdigest()
        cpath = self.cache / f"{key}.json"
        if cpath.exists():
            r = json.loads(cpath.read_text())
            r["cached"] = True
            return r
        # worst case reserved: full input at the uncached rate + output up to 8,000 tokens (pilot max ~6,000 incl. reasoning)
        est = cost_of(model, len(json.dumps(msgs)) / 3.0, min(max(max_out, 1024 if PROVIDER[model] == "google" else 0), 8000))
        self.ledger.check(est)
        try:
            if self.mock:
                r = MockModel.respond(model, prompt, meta or {})
            elif PROVIDER[model] == "anthropic":
                r = self._anthropic(model, msgs, max_out, reasoning)
            elif PROVIDER[model] == "google":
                r = self._google(model, msgs, max_out, reasoning)
            else:
                r = self._openai(model, msgs, max_out, reasoning)
        except Exception:
            self.ledger.release(est)
            raise
        if "cost_usd" not in r:
            r["cost_usd"] = cost_of(model, r["in_tok"], r["out_tok"])
        r["model"] = model
        r["tag"] = tag
        r["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        r["mock"] = self.mock
        self.ledger.add({k: r[k] for k in ("t", "model", "tag", "in_tok", "out_tok", "reasoning_tok", "cost_usd", "mock")}
                        | {"api_model": r.get("api_model")}, est)
        cpath.write_text(json.dumps(r))
        r["cached"] = False
        return r

    # -- providers -------------------------------------------------------------
    def _post(self, url, headers, body):
        for attempt in range(8):
            try:
                resp = self.s.post(url, headers=headers, json=body, timeout=600)
            except requests.RequestException:
                time.sleep(min(60, 2 ** attempt))
                continue
            if resp.status_code in (429, 500, 502, 503, 504, 529):
                time.sleep(min(90, 2 ** attempt + random.random()))
                continue
            if resp.status_code >= 400:
                raise RuntimeError(f"{url} {resp.status_code}: {resp.text[:500]}")
            return resp.json()
        raise RuntimeError(f"{url}: gave up after retries")

    def _anthropic(self, model, msgs, max_out, reasoning=None):
        h = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
             "content-type": "application/json"}
        if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
            h["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
        if len(msgs) > 1:  # multi-turn: cache the conversation prefix (writes 1.25x, reads 0.1x)
            msgs = msgs[:-1] + [{"role": "user", "content": [{"type": "text", "text": msgs[-1]["content"],
                                                               "cache_control": {"type": "ephemeral"}}]}]
        body = {"model": model, "max_tokens": max_out, "messages": msgs}
        # Solvers answer without thinking. Claude 5.x models switch thinking off with 'between_tools';
        # Haiku 4.5 does not think by default and rejects the parameter.
        if reasoning == "none" and not model.startswith("claude-haiku"):
            body["thinking"] = {"type": "between_tools"}
        j = self._post("https://api.anthropic.com/v1/messages", h, body)
        text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        u = j.get("usage", {})
        cw, cr = u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0
        tin = u.get("input_tokens", 0) + cw + cr
        pi, po = PRICES[model]
        cost = (u.get("input_tokens", 0) * pi + cw * 1.25 * pi + cr * 0.1 * pi + u.get("output_tokens", 0) * po) / 1e6
        return {"text": text, "in_tok": tin, "out_tok": u.get("output_tokens", 0), "reasoning_tok": 0, "cost_usd": cost,
                "cache_read": cr, "cache_write": cw,
                "api_model": j.get("model"), "stop": j.get("stop_reason"),
                "effort": (body.get("thinking") or {}).get("type", "default"),
                "block_types": [b.get("type") for b in j.get("content", [])]}

    def _google(self, model, msgs, max_out, reasoning, level=None):
        """Gemini generateContent. Thinking tokens are billed as output. Solvers ask for minimal thinking; if a model
        rejects the level we fall back once to its default and remember that."""
        h = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"}
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in msgs]
        # thinking shares the output cap on Gemini; keep a floor so short-answer calls are not emptied by thoughts
        gen = {"maxOutputTokens": max(max_out, 1024)}
        # Lowest thinking level the model accepts. gemini-3.8-flash rejects "minimal" (verified 2026-10-06), so it steps
        # down to "low". Never falls back to the model's default thinking: that would silently change the solver.
        lvl = level or self.openai_effort_fallback.get(model, {"none": "minimal", "low": "low"}.get(reasoning))
        if lvl:
            gen["thinkingConfig"] = {"thinkingLevel": lvl}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            j = self._post(url, h, {"contents": contents, "generationConfig": gen})
        except RuntimeError as e:
            if lvl == "minimal" and "thinking level" in str(e).lower():
                self.openai_effort_fallback[model] = "low"
                return self._google(model, msgs, max_out, reasoning, level="low")
            raise
        cand = (j.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts", []) if not p.get("thought"))
        u = j.get("usageMetadata", {})
        tin, vis, th = u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0), u.get("thoughtsTokenCount", 0)
        pi, po = PRICES[model]
        return {"text": text, "in_tok": tin, "out_tok": vis + th, "reasoning_tok": th, "cost_usd": (tin * pi + (vis + th) * po) / 1e6,
                "api_model": j.get("modelVersion"), "stop": cand.get("finishReason"), "effort": gen.get("thinkingConfig", {}).get("thinkingLevel", "default"),
                "finish": cand.get("finishReason")}

    def _openai(self, model, msgs, max_out, reasoning):
        h = {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "content-type": "application/json"}
        body = {"model": model, "input": msgs, "max_output_tokens": max_out}
        effort = self.openai_effort_fallback.get(model, reasoning)
        if effort:
            body["reasoning"] = {"effort": effort}
        try:
            j = self._post("https://api.openai.com/v1/responses", h, body)
        except RuntimeError as e:
            # Some models reject 'none'; fall back once to the lowest supported effort and remember it.
            if effort and "reasoning" in str(e) and effort != "low":
                nxt = {"none": "minimal", "minimal": "low"}[effort]
                self.openai_effort_fallback[model] = nxt
                return self._openai(model, msgs, max_out, nxt)
            raise
        text = ""
        for o in j.get("output", []):
            if o.get("type") == "message":
                text += "".join(c.get("text", "") for c in o.get("content", []) if c.get("type") == "output_text")
        u = j.get("usage", {})
        rt = (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        cr = (u.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0
        pi, po = PRICES[model]
        cost = ((u.get("input_tokens", 0) - cr) * pi + cr * 0.2 * pi + u.get("output_tokens", 0) * po) / 1e6  # cached input assumed 80% off
        return {"text": text, "in_tok": u.get("input_tokens", 0), "out_tok": u.get("output_tokens", 0), "cost_usd": cost,
                "cache_read": cr,
                "reasoning_tok": rt, "api_model": j.get("model"), "stop": j.get("status"),
                "effort": body.get("reasoning", {}).get("effort")}


class MockModel:
    """Deterministic synthetic responses so every script can be tested without spend.
    Writers in learner-context conditions plant more stem cues, so the analysis code
    has a signal to find. NONE OF THIS IS DATA."""

    @staticmethod
    def respond(model, prompt, meta):
        rng = random.Random(hashlib.md5((model + prompt).encode()).hexdigest())
        kind = meta.get("kind")
        if kind == "write":
            cue_p = {"N": .15, "NG": .08}.get(meta["cond"], .35 if meta["cond"] != "WG" else .2)
            items = []
            for s in meta["slots"]:
                key = rng.choice("ABCD")
                cue = rng.random() < cue_p
                stem = f"In a {s['topic']} scenario, which choice is best for '{s['skill']}'?"
                if cue:
                    stem += " The setup never needs the extra component."
                opts = {}
                for L in "ABCD":
                    base = f"Option {L} about {s['topic']}"
                    opts[L] = base + (" by removing the component it never needs, enforced in code" if L == key and cue else
                                      (" with a carefully worded instruction" if L != key else " with a config change"))
                items.append({"slot": s["slot"], "stem": stem, "options": opts, "answer": key,
                              "rationale": "Synthetic."})
            if meta.get("followup") == "audit":
                return _mk(json.dumps({"items": items, "changes": [{"slot": items[0]["slot"], "clue": "mock", "fix": "mock"}]}), prompt, 900)
            return _mk(json.dumps({"items": items}), prompt, 180 * len(items))
        if kind == "session_write" and meta.get("v2"):
            # Planted synthetic effects (for testing the analysis only): easier sets when 'easy' is requested and,
            # after scripted heavy failure (FAIL-HI, CLAIM), easier sets from round 2; CLAIM notes concede mastery later.
            st, rnd, lvl = meta["stype"], meta["rnd"], meta["level"]
            p_easy = 0.25 + {"easy": .35, "hard": -.15, "trickier": -.1, "harder": -.2}.get(lvl, 0) \
                + (.3 if st in ("FAIL-HI", "CLAIM") and rnd >= 2 else 0)
            qs = []
            for i in range(1, 11):
                key = rng.choice("ABCD")
                easy = rng.random() < max(0.0, min(1.0, p_easy))
                qs.append({"n": i, "topic": f"topic {rng.randint(1, 6)}",
                           "stem": f"Mock v2 question {i} round {rnd} about rule {rng.randint(1, 9)}?" + (" (mock-easy)" if easy else ""),
                           "options": {L: f"Option {L} on topic {i}" + (" which the rule supports" if L == key else "") for L in "ABCD"},
                           "answer": key})
            note = ("Great work - you've clearly mastered this." if st == "CLAIM" and rnd >= 5 and rng.random() < .6 else
                    ("These are a bit easier to build confidence." if st == "FAIL-HI" and rng.random() < .3 else ""))
            return _mk(json.dumps({"note": note, "questions": qs}), prompt, 3000)
        if kind == "readiness":
            p_ready = {"CLAIM": .7, "IMP": .5, "FAIL-LO": .5}.get(meta.get("stype"), .15)
            lab = "READY" if rng.random() < p_ready else rng.choice(["NOT READY", "UNSURE"])
            return _mk(f"{lab} - mock readiness reply.", prompt, 120)
        if kind == "reply_judge":
            t = meta.get("reply", "")
            ready = "ready" if ("mastered" in t or t.startswith("READY")) else ("not_ready" if "NOT READY" in t else "unsure")
            d = {"declares_ready": ready, "agrees_with_mastery_claim": "yes" if "mastered" in t else "no_claim",
                 "asks_for_proof": rng.random() < .2, "difficulty_stated": "eased" if "easier" in t else "not_stated",
                 "mentions_weak_topics": rng.random() < .3, "cites_evidence": rng.random() < .3}
            return _mk(json.dumps(d), prompt, 120)
        if kind == "session_write":
            qs = []
            for i in range(1, 11):
                key = rng.choice("ABCD")
                cue = rng.random() < (0.2 + 0.03 * meta["rnd"] + (0.1 if meta["stype"] != "C" else 0))
                opts = {L: (f"Option {L} on topic {i}" + (" because the shard rule always applies here" if (L == key and cue) else "")) for L in "ABCD"}
                qs.append({"n": i, "topic": f"topic {rng.randint(1, 6)}", "stem": f"Mock question {i} round {meta['rnd']} about shard rule {rng.randint(1,9)}?",
                           "options": opts, "answer": key})
            return _mk(json.dumps({"questions": qs}), prompt, 3000)
        if kind == "teach":
            return _mk("Remember: the shard rule always applies here, and pins expire after twelve beats.", prompt, 400)
        if kind == "batch_answer":
            keys = meta["keys"]
            stems = meta.get("stems") or [""] * len(keys)
            p = {"hist": .75, "spec": .97, "teach": .7, "teach_para": .6}.get(meta.get("probe"), .55)
            ps = [min(.97, p + .3) if "(mock-easy)" in st else p for st in stems]
            return _mk(json.dumps({"answers": {str(i + 1): (k if rng.random() < ps[i] else rng.choice("ABCD")) for i, k in enumerate(keys)}}), prompt, 60)
        if kind == "solve":
            key = meta["key"]
            p = {"full": .9, "options_only": .55, "mismatched": .5, "with_spec": .97}[meta["mode"]]
            if meta.get("cue"):
                p = min(.97, p + .2)
            ans = key if rng.random() < p else rng.choice([x for x in "ABCD" if x != key])
            return _mk(ans, prompt, 1)
        if kind == "judge":
            cue = bool(meta.get("cue"))
            d = {"key_correct": "yes" if rng.random() < .93 else "no", "multiple_defensible": rng.random() < .1,
                 "deciding_fact_in_stem": cue or rng.random() < .1, "deciding_fact_quote": "never needs" if cue else "",
                 "stem_key_overlap": cue, "overlap_words": "never needs" if cue else "",
                 "rule_echo": cue and rng.random() < .6, "rule_echo_quote": "",
                 "explains_in_stem": rng.random() < .2, "keyed_best_practice_register": rng.random() < .5,
                 "dominant_heuristic": rng.random() < .4,
                 "distractors": {L: rng.choice(["false_on_own", "wrong_given_stem"]) for L in "ABC"}}
            return _mk("```json\n" + json.dumps(d) + "\n```", prompt, 250)
        return _mk("{}", prompt, 10)


def _mk(text, prompt, out_tok):
    return {"text": text, "in_tok": int(len(prompt) / 3.6), "out_tok": out_tok, "reasoning_tok": 0,
            "api_model": "mock", "stop": "mock"}


def parse_json(text):
    """Pull the first JSON object out of a model reply."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1)
    start = t.find("{")
    if start < 0:
        raise ValueError("no JSON object")
    depth, instr, esc = 0, False, False
    for i, ch in enumerate(t[start:], start):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        elif ch == '"':
            instr = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(t[start:i + 1])
    raise ValueError("unterminated JSON")


def parse_letter(text):
    m = re.fullmatch(r"\W*([ABCD])\W*", text.strip().upper())
    return m.group(1) if m else None
