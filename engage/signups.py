"""Shared signup ledger for `bot` tasks. A partner bot (e.g. dordor/heefan) writes
a user's Telegram id here when they COMPLETE signup; the caption bot verifies via
has(code, user_id). File path is config.SIGNUPS_FILE (point it at a shared volume
both bots can reach).

Tolerant of several ledger shapes (str/int safe), so the partner bot can use
whichever it already has:
  - heefan style:  {"<id>": <ts>, ...}   (ids as keys)   <-- current dordor format
  - {code: [ids]}                         (per-task lists)
  - flat list:     [ids]
Telegram ids are global, so the id alone is the key — `code` just labels the task."""
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
        data = json.loads(open(_path(), encoding="utf-8").read())
    except Exception:
        return False
    sid = str(user_id)
    if isinstance(data, dict):
        if sid in data or user_id in data:                 # heefan {"<id>": ts}
            return True
        members = data.get(code, [])                        # {code: [ids]}
        return user_id in members or sid in [str(m) for m in members]
    if isinstance(data, list):                              # flat [ids]
        return user_id in data or sid in [str(m) for m in data]
    return False
