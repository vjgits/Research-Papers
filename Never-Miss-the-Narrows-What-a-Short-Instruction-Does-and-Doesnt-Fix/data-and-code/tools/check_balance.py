#!/usr/bin/env python3
"""Print the OpenRouter ACCOUNT balance (total credits - total usage) and, separately, the key's own limit.
The key is read from OPENROUTER_API_KEY in your terminal; it is never printed or saved.

  python3 tools/check_balance.py
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import engine_v05 as E  # noqa: E402
import requests  # noqa: E402

bal = E.account_balance(requests.get)
print(f"ACCOUNT balance: ${bal['balance']:.2f}  (total credits ${bal['total_credits']:.2f} - total usage ${bal['total_usage']:.2f})")
r = requests.get("https://openrouter.ai/api/v1/key", headers=E.headers(), timeout=(10, 30))
if r.ok:
    d = r.json().get("data") or {}
    print(f"key limit (informational only): limit={d.get('limit')} limit_remaining={d.get('limit_remaining')} usage={d.get('usage')}")
if "--set-baseline" in sys.argv:
    bp = Path(__file__).resolve().parents[1] / "budget_baseline.json"
    if bp.exists():
        print(f"Baseline already set: {bp.read_text().strip()} (delete the file only if you intend to restart the budget)")
    else:
        bp.write_text(json.dumps({"total_usage": bal["total_usage"], "set_utc": E.now()}))
        print(f"Baseline set: total_usage=${bal['total_usage']:.4f}. v0.5 spend is now measured from this point.")
print("Run phases only if the ACCOUNT balance covers the launch cap.")
