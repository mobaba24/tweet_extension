"""Shared signup ledger for `bot` tasks. A partner bot (e.g. dordor/heefan) writes
a user's Telegram id here when they COMPLETE signup; the caption bot verifies via
has(code, user_id). File path is config.SIGNUPS_FILE (point it at a shared volume
both bots can reach). Accepts either a flat list of ids, or {code: [ids]}.
Telegram ids are global, so a flat list is enough — `code` just labels the task."""
import json
import threading

import config

_LOCK = threading.Lock()


def _path():
    return config.SIGNUPS_FILE


def add(code, user_id):
    """Local helper / for same-process partner code. Writes {code: [ids]}."""
    with _LOCK:
        try:
            d = json.loads(open(_path(), encoding="utf-8").read())
            if not isinstance(d, dict):
                d = {}
        except Exception:
            d = {}
        d.setdefault(code, [])
        if user_id not in d[code]:
            d[code].append(user_id)
        open(_path(), "w", encoding="utf-8").write(json.dumps(d))


def has(code, user_id):
    try:
        d = json.loads(open(_path(), encoding="utf-8").read())
    except Exception:
        return False
    if isinstance(d, list):           # flat list of completed-signup ids
        return user_id in d
    return user_id in d.get(code, [])  # {code: [ids]}
