"""Admin-managed earn-credit tasks (channels + bots). JSON-backed.

task = {id, type: "channel"|"bot", target, url, title, bonus}
  - channel: target is @username or chat id (the caption bot must be admin there
    to verify membership); url is the join link.
  - bot: target is a short code the partner bot reports on signup; url is the
    deep link the user taps.
"""
import json
import threading

import config

_FILE = config.ROOT / "tasks.json"
_LOCK = threading.Lock()


def _load():
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seq": 0, "items": []}


def _save(d):
    _FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def list_tasks():
    return _load()["items"]


def add(type_, target, url, title):
    with _LOCK:
        d = _load()
        d["seq"] += 1
        tid = str(d["seq"])
        d["items"].append({
            "id": tid, "type": type_, "target": target, "url": url,
            "title": title, "bonus": config.TASK_BONUS,
        })
        _save(d)
        return tid


def remove(tid):
    with _LOCK:
        d = _load()
        before = len(d["items"])
        d["items"] = [t for t in d["items"] if t["id"] != tid]
        _save(d)
        return len(d["items"]) < before
