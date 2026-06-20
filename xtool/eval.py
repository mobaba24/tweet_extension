"""Accuracy harness for the image classifier.

Runs the ensemble on a labeled set and reports precision/recall/accuracy plus the
list of misclassified images, so thresholds in config.py can be tuned with numbers.

Ground truth is seeded from this project's review:
  - the 49 sample images  -> keep   (the target "solo female portrait" class)
  - the 33 review images  -> reject the ones agreed wrong (non-person, groups,
    news graphics, men), keep the rest.
Point SAMPLE_DIR / FIX_DIR at the locally-downloaded images, or pass --labels
<csv> (columns: path,label) for your own set.
"""
import argparse, csv, glob, os
import config
from classify import Classifier, load_image

SAMPLE_DIR = "/tmp/sample_imgs"   # s_*.jpg  -> all "keep"
FIX_DIR = "/tmp/fix_imgs"         # NN.jpg   -> reject those in FIX_REJECT
FIX_REJECT = {6, 8, 10, 11, 16, 18, 20, 24, 26, 28}  # agreed wrong rows


def seeded_labels():
    items = []
    for p in sorted(glob.glob(os.path.join(SAMPLE_DIR, "s_*.jpg"))):
        items.append((p, "keep", os.path.basename(p)))
    for p in sorted(glob.glob(os.path.join(FIX_DIR, "[0-9][0-9].jpg"))):
        i = int(os.path.basename(p)[:2])
        items.append((p, "reject" if i in FIX_REJECT else "keep", f"fix{i:02d}"))
    return items


def csv_labels(path):
    items = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            items.append((row["path"], row["label"].strip().lower(), os.path.basename(row["path"])))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", help="CSV with columns path,label (keep|reject)")
    args = ap.parse_args()

    items = csv_labels(args.labels) if args.labels else seeded_labels()
    if not items:
        print("No labeled images found. Check SAMPLE_DIR / FIX_DIR or pass --labels.")
        return

    clf = Classifier()
    rows, tp = [], 0
    tn = fp = fn = 0
    for path, label, name in items:
        r = clf.classify(load_image(path))
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

    print(f"\n== {n} images | vote={config.VOTE} "
          f"DET>={config.DET_SCORE_MIN} SIZE>={config.FACE_SIZE_MIN} CLIP>={config.CLIP_MIN} ==")
    print(f"accuracy {acc:.1%}   precision {prec:.1%}   recall {rec:.1%}   F1 {f1:.1%}")
    print(f"TP {tp}  TN {tn}  FP {fp}  FN {fn}\n")
    print("Misclassified:")
    for name, label, pred, r in rows:
        if (pred == "keep") != (label == "keep"):
            print(f"  {name:9s} label={label:6s} pred={pred:6s}  "
                  f"faces={r['faceCount']} g={r['faceGender']} det={r['faceDet']} "
                  f"sz={r['faceSizeFrac']} clip={r['clipPos']}  ({r['reason']})")

    out = config.OUT / "eval_results.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "label", "pred", "faceCount", "faceGender", "faceDet", "faceSizeFrac", "clipPos", "reason"])
        for name, label, pred, r in rows:
            w.writerow([name, label, pred, r["faceCount"], r["faceGender"], r["faceDet"], r["faceSizeFrac"], r["clipPos"], r["reason"]])
    print("\nwrote", out)


if __name__ == "__main__":
    main()
