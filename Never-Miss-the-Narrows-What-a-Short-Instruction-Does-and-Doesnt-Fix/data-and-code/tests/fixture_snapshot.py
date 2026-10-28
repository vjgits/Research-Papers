"""Mock tests only: write a placeholder pricing snapshot (made-up uniform prices, NOT real prices) if none exists,
and remove it afterwards. The public package ships no real price snapshot."""
import json
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "pricing_snapshot_v05.json"


@contextmanager
def placeholder_snapshot():
    if SNAP.exists():
        yield
        return
    import re
    ids = set()
    for p in list(ROOT.glob("*.json")) + list(ROOT.rglob("*.py")):
        ids |= set(re.findall(r'"([a-z0-9-]+/[A-Za-z0-9._:-]+)"', p.read_text(errors="ignore")))
    models = {i: {"prompt": "0.000001", "completion": "0.000004", "input_cache_read": "0.0000001", "input_cache_write": "0.000001",
                  "internal_reasoning": None, "context_length": 1000000, "hugging_face_id": None} for i in ids if "/" in i and " " not in i}
    SNAP.write_text(json.dumps({"fetched_utc": "placeholder", "source": "mock-test placeholder (not real prices)", "models": models}))
    try:
        yield
    finally:
        SNAP.unlink()
