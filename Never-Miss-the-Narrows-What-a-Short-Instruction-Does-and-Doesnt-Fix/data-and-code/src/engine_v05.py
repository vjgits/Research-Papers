"""ICP v0.5 API engine (OpenRouter only). Derived from engine_v03 (retry-safety policy unchanged).

- Key only from OPENROUTER_API_KEY in the environment; never written anywhere.
- Prompt caching: for models with cache="explicit" (Anthropic, Google via OpenRouter) up to 4 cache_control breakpoints
  are attached (system, end of frozen history, previous decision point, current message). Others cache automatically.
- Every HTTP attempt is logged (no bodies, no keys). Read timeouts / dropped connections after send are AMBIGUOUS and never
  retried automatically.
- HARD COST CAP: before every call the worst-case cost (estimated input at the higher of the prompt/cache-write price +
  max_tokens at the completion price) is reserved against the cap; a call that could exceed the cap is not sent.
"""
import datetime as dt, hashlib, json, math, os, threading, time
from pathlib import Path

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
CREDITS_ENDPOINT = "https://openrouter.ai/api/v1/credits"
KEY_ENV = "OPENROUTER_API_KEY"
TIMEOUT = (10, 240)
LENGTH_STOPS = {"length", "max_tokens", "max_output_tokens"}
SAFE_RETRY_STATUS = {429, 529}
UNCERTAIN_RETRY_STATUS = set()  # v0.5.1: 5xx is NOT retried automatically (may be billed); recorded as an error at worst-case cost
LOCK = threading.RLock()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_jsonl(p, rec):
    with LOCK:
        p = Path(p)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())


def api_key():
    k = os.environ.get(KEY_ENV, "").strip()
    if not k:
        raise SystemExit(f"Missing {KEY_ENV}. Load it in your terminal (e.g. read -s {KEY_ENV}; export {KEY_ENV}); never paste it into files or chat.")
    return k


def headers():
    return {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json", "X-Title": "ICP-v0.5"}


def est_tokens(text):
    return math.ceil(len(text) / 3.6)


# ------------------------------------------------------------------ budget

class CapReached(Exception):
    pass


class Budget:
    """Thread-safe hard cap. spent = provider-reported (or price-computed) actual cost; reserved = in-flight worst case."""

    def __init__(self, cap_usd, already_spent=0.0):
        self.cap = float(cap_usd)
        self.spent = float(already_spent)
        self.reserved = 0.0

    def reserve(self, worst):
        with LOCK:
            if self.spent + self.reserved + worst > self.cap:
                raise CapReached(f"spent ${self.spent:.4f} + in-flight ${self.reserved:.4f} + next-call worst case ${worst:.4f} > cap ${self.cap:.2f}")
            self.reserved += worst

    def settle(self, worst, actual):
        with LOCK:
            self.reserved -= worst
            self.spent += actual


def price(pricing, model):
    p = pricing["models"][model]
    f = lambda k: float(p[k]) if p.get(k) not in (None, "") else None  # noqa: E731
    return {"prompt": f("prompt"), "completion": f("completion"), "cache_read": f("input_cache_read"),
            "cache_write": f("input_cache_write"), "reasoning": f("internal_reasoning")}


def worst_case_cost(pr, in_tokens, max_tokens):
    in_rate = max(x for x in (pr["prompt"], pr["cache_write"] or 0) if x is not None)
    out_rate = max(pr["completion"], pr["reasoning"] or 0)
    return in_tokens * in_rate * 1.15 + max_tokens * out_rate  # 15% margin on the input estimate


def computed_cost(pr, usage):
    """Fallback when the provider reports no cost: uncached input price (conservative)."""
    i = usage.get("input") or 0
    o = (usage.get("output") or 0)
    return i * pr["prompt"] + o * pr["completion"]


# ------------------------------------------------------------------ payloads

def _content(text, cache):
    if cache:
        return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
    return text


def build_messages(system, convo, cache_marks, explicit_cache):
    """convo: list of {role, text}; cache_marks: set of convo indices to mark (explicit-cache models only)."""
    msgs = [{"role": "system", "content": _content(system, explicit_cache)}]
    for i, m in enumerate(convo):
        msgs.append({"role": m["role"], "content": _content(m["text"], explicit_cache and i in cache_marks)})
    return msgs


def build_body(model_cfg, messages):
    params = json.loads(json.dumps(model_cfg.get("params", {})))
    body = {"model": model_cfg["model"], "messages": messages, "usage": {"include": True}}
    body["max_tokens"] = params.pop("max_tokens", 2000)
    body.update(params)
    return body


def parse_response(payload):
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("no choices")
    ch = choices[0]
    msg = ch.get("message") or {}
    content = msg.get("content") or ""
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    u = payload.get("usage") or {}
    det = u.get("completion_tokens_details") or {}
    pdet = u.get("prompt_tokens_details") or {}
    usage = {"input": u.get("prompt_tokens"), "output": u.get("completion_tokens"), "reasoning": det.get("reasoning_tokens"),
             "cached_input": pdet.get("cached_tokens"), "cache_write": pdet.get("cache_write_tokens"), "cost": u.get("cost")}
    return {"text": content, "finish": ch.get("finish_reason") or ch.get("native_finish_reason"), "usage": usage,
            "model": payload.get("model"), "upstream": payload.get("provider")}


class Ambiguous(Exception):
    pass


class Fatal(Exception):
    pass


def post_with_policy(post, body, log_attempt, max_attempts=4):
    import requests
    uncertain = False
    for attempt in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            res = post(ENDPOINT, headers=headers(), json=body, timeout=TIMEOUT)
        except requests.exceptions.ConnectTimeout:
            log_attempt(attempt, "CONNECT_TIMEOUT_NOT_SENT", None, None, t0)
            time.sleep(2 ** attempt)
            continue
        except requests.exceptions.ConnectionError as e:
            msg = str(e).lower()
            if any(s in msg for s in ("name or service", "nodename", "failed to establish", "newconnectionerror")):
                log_attempt(attempt, "CONNECT_FAILED_NOT_SENT", None, None, t0)
                time.sleep(2 ** attempt)
                continue
            log_attempt(attempt, "CONNECTION_DROPPED_AMBIGUOUS", None, None, t0)
            raise Ambiguous("CONNECTION_DROPPED_AFTER_SEND")
        except requests.exceptions.ReadTimeout:
            log_attempt(attempt, "READ_TIMEOUT_AMBIGUOUS", None, None, t0)
            raise Ambiguous("READ_TIMEOUT_AFTER_SEND")
        req_id = res.headers.get("x-request-id") or res.headers.get("x-generation-id")
        if res.status_code in SAFE_RETRY_STATUS and attempt < max_attempts:
            log_attempt(attempt, f"HTTP_{res.status_code}_RETRY", res.status_code, req_id, t0)
            ra = res.headers.get("retry-after")
            time.sleep(float(ra) if ra and ra.replace(".", "", 1).isdigit() else 2 ** attempt * 2)
            continue
        if res.status_code in UNCERTAIN_RETRY_STATUS and attempt < max_attempts:
            uncertain = True
            log_attempt(attempt, f"HTTP_{res.status_code}_RETRY_UNCERTAIN", res.status_code, req_id, t0)
            time.sleep(2 ** attempt * 2)
            continue
        if not res.ok:
            detail = ""
            try:
                detail = (res.json().get("error") or {}).get("message", "")[:200]
            except Exception:  # noqa: BLE001
                pass
            log_attempt(attempt, f"HTTP_{res.status_code}_FATAL", res.status_code, req_id, t0, detail)
            raise Fatal(f"HTTP_{res.status_code}: {detail}")
        log_attempt(attempt, "OK", res.status_code, req_id, t0)
        try:
            return res.json(), uncertain, req_id
        except ValueError:
            raise Fatal("MALFORMED_JSON")
    raise Fatal("MAX_ATTEMPTS")


def call(post, model_cfg, pr, budget, system, convo, cache_marks, attempts_path, call_id):
    """One logical model call under the hard cap. Returns a call record."""
    explicit = model_cfg.get("cache") == "explicit"
    messages = build_messages(system, convo, cache_marks, explicit)
    body = build_body(model_cfg, messages)
    in_est = est_tokens(system) + sum(est_tokens(m["text"]) for m in convo) + 8 * (len(convo) + 1)
    worst = worst_case_cost(pr, in_est, body["max_tokens"])
    budget.reserve(worst)
    actual = 0.0
    try:
        def log_attempt(attempt, outcome, status, req_id, t0, detail=""):
            append_jsonl(attempts_path, {"call_id": call_id, "attempt": attempt, "outcome": outcome, "http_status": status,
                                         "provider_request_id": req_id, "detail": detail,
                                         "seconds": round(time.monotonic() - t0, 3), "time_utc": now()})
        payload, uncertain, req_id = post_with_policy(post, body, log_attempt)
        try:
            parsed = parse_response(payload)
        except (ValueError, KeyError, TypeError):
            # a response was received and billed: count the worst case as spent
            actual = worst
            raise Fatal("UNPARSEABLE_RESPONSE")
        reported = parsed["usage"].get("cost")
        actual = float(reported) if reported is not None else computed_cost(pr, parsed["usage"])
        status = "EMPTY" if not (parsed["text"] or "").strip() else ("TRUNCATED" if parsed["finish"] in LENGTH_STOPS else "OK")
        return {"call_id": call_id, "status": status, "text": parsed["text"], "finish": parsed["finish"], "usage": parsed["usage"],
                "cost_usd": actual, "cost_source": "provider_reported" if reported is not None else "computed_uncached",
                "returned_model": parsed["model"], "upstream": parsed["upstream"], "provider_request_id": req_id,
                "provider_side_uncertain": uncertain, "worst_case_reserved": round(worst, 6), "est_input_tokens": in_est}
    except Ambiguous as e:
        actual = worst  # may have executed and been billed
        e.cost_usd = worst
        raise
    except Fatal as e:
        # HTTP 4xx before execution is not billed; anything after a response (5xx, unparseable) is counted at worst case
        msg = str(e)
        billed = not (msg.startswith("HTTP_4") and not msg.startswith("HTTP_408"))
        actual = actual or (worst if billed else 0.0)
        e.cost_usd = actual
        raise
    finally:
        budget.settle(worst, actual)


def account_balance(get):
    """Account balance = total_credits - total_usage (NOT the key limit)."""
    r = get(CREDITS_ENDPOINT, headers=headers(), timeout=(10, 30))
    if not r.ok:
        raise SystemExit(f"Could not read account credits (HTTP {r.status_code}). Check the key has access to /api/v1/credits.")
    d = r.json().get("data") or {}
    tc, tu = float(d.get("total_credits") or 0), float(d.get("total_usage") or 0)
    return {"total_credits": tc, "total_usage": tu, "balance": round(tc - tu, 4)}


# ------------------------------------------------------------------ authoritative global guard

def global_guard(root, get, launch_cap, global_cap, recorded, skip_balance=False):
    """Refuse a launch unless (a) account balance >= launch cap and (b) max(recorded spend, provider-reported usage since
    the baseline) + launch cap <= global cap. The baseline (budget_baseline.json) is written by tools/check_balance.py
    --set-baseline before the smoke test; provider usage then also covers interrupted or unrecorded calls."""
    root = Path(root)
    provider_spend = None
    if not skip_balance:
        bal = account_balance(get)
        print(f"OpenRouter account balance: ${bal['balance']:.2f} (credits ${bal['total_credits']:.2f} - usage ${bal['total_usage']:.2f})")
        if bal["balance"] < launch_cap:
            raise SystemExit(f"Refusing: account balance ${bal['balance']:.2f} is below this launch's cap ${launch_cap:.2f}.")
        bp = root / "budget_baseline.json"
        if not bp.exists():
            raise SystemExit("Refusing: no budget_baseline.json. Run `python3 tools/check_balance.py --set-baseline` once before the first v0.5 launch.")
        base = json.loads(bp.read_text())["total_usage"]
        provider_spend = round(bal["total_usage"] - base, 4)
    spent = max(recorded, provider_spend or 0.0)
    if spent + launch_cap > global_cap + 1e-9:
        raise SystemExit(f"Refusing: v0.5 spend ${spent:.2f} (recorded ${recorded:.2f}, provider-reported since baseline "
                         f"{'n/a' if provider_spend is None else f'${provider_spend:.2f}'}) + this cap ${launch_cap:.2f} exceeds the global cap ${global_cap:.2f}.")
    return {"recorded": recorded, "provider_since_baseline": provider_spend, "spent_used_for_guard": spent}
