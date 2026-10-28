#!/usr/bin/env python3
"""Recreate pricing_snapshot_v05.json from the public OpenRouter model catalog (no key needed).
The released package omits the original snapshot; run this once before any paid re-run.
Usage: python3 tools/make_pricing_snapshot.py"""
import json, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=60) as r:
    data = json.load(r)["data"]
keep = ("prompt", "completion", "input_cache_read", "input_cache_write", "internal_reasoning")
snap = {"fetched_utc": datetime.now(timezone.utc).isoformat(), "source": "https://openrouter.ai/api/v1/models",
        "models": {m["id"]: {**{k: (m.get("pricing") or {}).get(k) for k in keep}, "context_length": m.get("context_length"),
                            "hugging_face_id": m.get("hugging_face_id")} for m in data}}
(ROOT / "pricing_snapshot_v05.json").write_text(json.dumps(snap, indent=1))
print("wrote pricing_snapshot_v05.json with", len(snap["models"]), "models")
