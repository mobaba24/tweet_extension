"""Shared signup ledger for `bot` tasks. The partner bot (e.g. heefan) calls
add(code, user_id) when a user signs up via the referral deep link; the caption
bot calls has(code, user_id) to verify. File-backed — works when both bots share
this file (same VPS). If they're on different hosts, have the partner bot POST to
a small sync endpoint or replicate this file; until then admins can /grant."""
import json
import threading

import config

_FILE = config.ROOT / "bot_signups.json"   # { code: [user_id, ...] }
_LOCK = threading.Lock()


def add(code, user_id):
    with _LOCK:
        try:
            d = json.loads(_FILE.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        d.setdefault(code, [])
        if user_id not in d[code]:
            d[code].append(user_id)
        _FILE.write_text(json.dumps(d), encoding="utf-8")


def has(code, user_id):
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    return user_id in d.get(code, [])
