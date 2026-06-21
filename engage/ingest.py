"""Load an extension export (tweets.json / .csv) into normalised dicts.
Self-contained so the bots can deploy without xtool."""
import csv
import json


def _norm(d):
    images = d.get("images")
    if isinstance(images, str):
        images = [u.strip() for u in images.split("|") if u.strip()]
    elif not isinstance(images, list):
        images = []
    return {
        "username": d.get("username", ""),
        "handle": d.get("handle", ""),
        "date": d.get("date", ""),
        "text": d.get("text", ""),
        "likes": d.get("likes", 0),
        "comments": d.get("comments", 0),
        "images": images,
        "id": d.get("id") or f'{d.get("handle") or d.get("username")}|{d.get("date")}',
    }


def load_export(path):
    p = str(path)
    if p.lower().endswith(".json"):
        return [_norm(d) for d in json.loads(open(p, encoding="utf-8").read())]
    with open(p, encoding="utf-8-sig", newline="") as f:   # csv (BOM-tolerant)
        return [_norm(d) for d in csv.DictReader(f)]
