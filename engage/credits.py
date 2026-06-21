"""Per-user daily credits. FREE_PER_DAY free captions/day (resets at UTC midnight)
plus earned `bonus` credits from completed tasks. JSON-backed."""
import datetime
import json
import threading

import config

_FILE = config.ROOT / "credits.json"
_LOCK = threading.Lock()


def _today():
    return datetime.datetime.utcnow().date().isoformat()


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d):
    _FILE.write_text(json.dumps(d), encoding="utf-8")


def _rec(d, uid):
    u = d.get(str(uid))
    if not u:
        u = {"day": _today(), "used": 0, "bonus": 0, "done": []}
        d[str(uid)] = u
    if u.get("day") != _today():
        u["day"] = _today()
        u["used"] = 0
    return u


def available(uid):
    with _LOCK:
        d = _load()
        u = _rec(d, uid)
        _save(d)
        return max(0, config.FREE_PER_DAY - u["used"]) + u.get("bonus", 0)


def consume(uid):
    """Spend one credit (free first, then bonus). Returns True if it could."""
    with _LOCK:
        d = _load()
        u = _rec(d, uid)
        ok = True
        if config.FREE_PER_DAY - u["used"] > 0:
            u["used"] += 1
        elif u.get("bonus", 0) > 0:
            u["bonus"] -= 1
        else:
            ok = False
        _save(d)
        return ok


def grant(uid, task_id, amount=None):
    """Grant a task's bonus once per user. Returns True if newly granted."""
    amount = config.TASK_BONUS if amount is None else amount
    with _LOCK:
        d = _load()
        u = _rec(d, uid)
        if task_id in u["done"]:
            _save(d)
            return False
        u["done"].append(task_id)
        u["bonus"] = u.get("bonus", 0) + amount
        _save(d)
        return True


def done_tasks(uid):
    with _LOCK:
        d = _load()
        u = _rec(d, uid)
        _save(d)
        return set(u.get("done", []))
