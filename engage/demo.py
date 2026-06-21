"""Phase-1 demo: load an export, draft a reply for each post, print {post -> reply}.
No posting, no browser. Verifies the reply engine + safety gate.

    python demo.py [path-to-tweets.json] [N]
"""
import os
import sys
import config
from ingest import load_export
from safety import is_engageable
from llm import ReplyEngine, detect_lang


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/tweets.json")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    tweets = load_export(path)
    print(f"Loaded {len(tweets)} posts from {path}; model={config.MODEL}\n")

    eng = ReplyEngine()
    shown = 0
    for t in tweets:
        text = t.get("text", "")
        ok, reason = is_engageable(text)
        if not ok:
            continue
        reply = eng.draft(text)
        handle = t.get("handle", "") or t.get("username", "")
        print("=" * 70)
        print(f"{handle:20s} [{detect_lang(text)}]")
        print("POST :", " ".join(text.split())[:200])
        print("REPLY:", reply if reply else "(model returned SKIP)")
        shown += 1
        if shown >= n:
            break
    print("\nDone.")


if __name__ == "__main__":
    main()
