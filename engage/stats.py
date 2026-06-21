"""Tiny JSON-backed usage stats for admin /stats and /broadcast."""
import json
import threading

import config

_FILE = config.ROOT / "stats.json"
_LOCK = threading.Lock()


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"users": [], "captions": 0}


def record(user_id):
    with _LOCK:
        d = _load()
        if user_id and user_id not in d["users"]:
            d["users"].append(user_id)
        d["captions"] = d.get("captions", 0) + 1
        _FILE.write_text(json.dumps(d), encoding="utf-8")


def summary():
    d = _load()
    return {"users": len(d.get("users", [])), "captions": d.get("captions", 0), "user_ids": d.get("users", [])}
