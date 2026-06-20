"""Accuracy harness for the image classifier.

Runs the ensemble on a labeled set and reports precision/recall/accuracy plus the
misclassified images, so the thresholds in config.py can be tuned with numbers.

Feature extraction (the slow model inference) is cached to out/features.json, so
after the first run you can edit config.py thresholds and re-run in ~1s — only the
fast decide() logic re-runs.

Ground truth seeded from this project's review (see SAMPLE_REJECT / FIX_REJECT).
Pass --labels <csv> (columns path,label) to use your own set. Pass --refresh to
recompute the feature cache.
"""
import argparse, csv, glob, json, os
import config
from classify import decide

SAMPLE_DIR = "/tmp/sample_imgs"   # s_N.jpg
FIX_DIR = "/tmp/fix_imgs"         # NN.jpg
SAMPLE_REJECT = {23, 29, 35, 48}                       # groups / collages, not solo portraits
FIX_REJECT = {6, 7, 8, 10, 11, 15, 16, 18, 20, 24, 26, 28}  # non-person / group / news / men


def seeded_labels():
    items = []
    for p in sorted(glob.glob(os.path.join(SAMPLE_DIR, "s_*.jpg"))):
        i = int(os.path.basename(p)[2:-4])
        items.append((p, "reject" if i in SAMPLE_REJECT else "keep", os.path.basename(p)[:-4]))
    for p in sorted(glob.glob(os.path.join(FIX_DIR, "[0-9][0-9].jpg"))):
        i = int(os.path.basename(p)[:2])
        items.append((p, "reject" if i in FIX_REJECT else "keep", f"fix{i:02d}"))
    return items


def csv_labels(path):
    with open(path, newline="") as f:
        return [(r["path"], r["label"].strip().lower(), os.path.basename(r["path"])) for r in csv.DictReader(f)]


def get_features(items, refresh):
    cache_path = config.OUT / "features.json"
    cache = {} if refresh or not cache_path.exists() else json.loads(cache_path.read_text())
    missing = [it for it in items if it[2] not in cache]
    if missing:
        from classify import Classifier, load_image
        clf = Classifier()
        for path, _, name in missing:
            cache[name] = clf.features(load_image(path))
        config.OUT.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache))
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels")
    ap.add_argument("--refresh", action="store_true", help="recompute the feature cache")
    args = ap.parse_args()

    items = csv_labels(args.labels) if args.labels else seeded_labels()
    feats = get_features(items, args.refresh)

    rows, tp = [], 0
    tn = fp = fn = 0
    for path, label, name in items:
        r = decide(feats[name])
        pred = "keep" if r["match"] else "reject"
        if label == "keep" and pred == "keep": tp += 1
        elif label == "reject" and pred == "reject": tn += 1
        elif label == "reject" and pred == "keep": fp += 1
        elif label == "keep" and pred == "reject": fn += 1
        rows.append((name, label, pred, r))

    n = len(items)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    acc = (tp + tn) / n
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    print(f"\n== {n} images | DET>={config.DET_SCORE_MIN} SIZE>={config.FACE_SIZE_MIN} "
          f"rescue>={config.NOFACE_RESCUE_CLIP} trustSize>={config.GENDER_TRUST_SIZE} ==")
    print(f"accuracy {acc:.1%}   precision {prec:.1%}   recall {rec:.1%}   F1 {f1:.1%}")
    print(f"TP {tp}  TN {tn}  FP {fp}  FN {fn}")

    def show(title, pred_kw):
        sub = [r for r in rows if (r[2] == "keep") != (r[1] == "keep") and r[2] == pred_kw]
        if sub:
            print(f"\n{title}:")
            for name, label, pred, r in sub:
                print(f"  {name:8s} label={label:6s} pred={pred:6s}  "
                      f"faces={r['faceCount']} g={r['faceGender']} sz={r['faceSizeFrac']} "
                      f"clip={r['clipPos']} grp={r['clipGroup']}  ({r['reason']})")
    show("FALSE POSITIVES (kept but should reject)", "keep")
    show("FALSE NEGATIVES (rejected but should keep)", "reject")

    boosted = [r for r in rows if r[3]["reason"] in ("rescue-noface", "small-but-clip") or
               (r[3]["match"] and r[3]["faceGender"] == "male")]
    if boosted:
        print("\nRecall-booster matches (audit these):")
        for name, label, pred, r in boosted:
            print(f"  {name:8s} {r['reason']:14s} g={r['faceGender']} sz={r['faceSizeFrac']} "
                  f"clip={r['clipPos']}  -> {'OK' if label=='keep' else 'WRONG(FP)'}")


if __name__ == "__main__":
    main()
