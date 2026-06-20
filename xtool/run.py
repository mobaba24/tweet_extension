"""End-to-end: get tweets -> infer account gender -> classify images
-> export tweets.json / tweets.csv (+ filtered) and a contact sheet.

Two ways to get tweets:

  # A) RECOMMENDED — ingest the extension's export (X blocks automated browsers,
  #    so let the extension scrape from your real logged-in session, then:
  python run.py --input ~/Downloads/tweets.json --filter like

  # B) Playwright scrape directly (only works if X doesn't block automation):
  python run.py --url "https://x.com/<handle>" --scrolls 10 --filter like

--filter:
    all   every post
    any   only posts that have a photo
    like  only posts with a SOLO FEMALE PORTRAIT photo (InsightFace + CLIP)
"""
import argparse, csv, json, urllib.request
from PIL import Image, ImageDraw, ImageFont
import config
from gender_names import guess_gender

FIELDS = ["username", "handle", "gender", "date", "likes", "comments", "retweets",
          "views", "imageCount", "imageUrl", "images", "faceCount", "faceGender",
          "faceDet", "clipPos", "decision", "text"]


def norm_tweet(d):
    """Normalise one record from an extension export (json dict or csv row)."""
    images = d.get("images")
    if isinstance(images, str):
        images = [u.strip() for u in images.split("|") if u.strip()]  # CSV: pipe-joined
    elif not isinstance(images, list):
        images = []
    if not images:
        u = d.get("imageUrl")
        if u and u != "none":
            images = [u]

    def num(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    return {
        "id": d.get("id") or f'{d.get("handle") or d.get("username")}|{d.get("date")}',
        "username": d.get("username", ""), "handle": d.get("handle", ""),
        "date": d.get("date", ""), "text": d.get("text", ""),
        "likes": num(d.get("likes")), "comments": num(d.get("comments")),
        "retweets": num(d.get("retweets")), "views": num(d.get("views")),
        "images": images,
    }


def load_export(path):
    p = str(path)
    if p.lower().endswith(".json"):
        data = json.loads(open(p, encoding="utf-8").read())
        return [norm_tweet(d) for d in data]
    with open(p, encoding="utf-8-sig", newline="") as f:   # csv (BOM-tolerant)
        return [norm_tweet(d) for d in csv.DictReader(f)]


def cache_image(url):
    config.IMG_CACHE.mkdir(parents=True, exist_ok=True)
    mid = url.split("/media/")[-1].split("?")[0]
    dest = config.IMG_CACHE / f"{mid}.jpg"
    if not dest.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        dest.write_bytes(urllib.request.urlopen(req, timeout=20).read())
    return dest


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM for Excel
        w = csv.writer(f)
        w.writerow(FIELDS)
        for r in rows:
            w.writerow([" | ".join(r[k]) if isinstance(r.get(k), list) else r.get(k, "") for k in FIELDS])


def contact_sheet(rows, path, cols=6, tile=200):
    imgs = [r for r in rows if (r.get("matchUrl") or r.get("imageUrl")) not in (None, "none")]
    if not imgs:
        return
    import math
    n = len(imgs); rn = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * tile, rn * (tile + 22)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    except Exception: font = ImageFont.load_default()
    for idx, r in enumerate(imgs):
        try:
            im = Image.open(cache_image(r.get("matchUrl") or r["imageUrl"])).convert("RGB"); im.thumbnail((tile, tile))
        except Exception:
            continue
        x = (idx % cols) * tile; y = (idx // cols) * (tile + 22)
        sheet.paste(im, (x + (tile - im.width) // 2, y + 22 + (tile - im.height) // 2))
        tag = r.get("decision", "")
        color = (90, 230, 90) if tag == "match" else (230, 90, 90)
        d.text((x + 3, y + 4), f"{r.get('handle','')[:14]} {tag}", fill=color, font=font)
    sheet.save(path, quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="extension export (tweets.json/.csv) — RECOMMENDED, no browser")
    ap.add_argument("--url", help="X page to scrape with Playwright (X may block automation)")
    ap.add_argument("--scrolls", type=int, default=config.SCROLLS)
    ap.add_argument("--filter", choices=["all", "any", "like"], default="like")
    args = ap.parse_args()
    config.OUT.mkdir(parents=True, exist_ok=True)

    if args.input:
        print(f"Loading export {args.input}…")
        tweets = load_export(args.input)
    elif args.url:
        from scrape import scrape  # lazy: only needed for Playwright path
        print(f"Scraping {args.url} ({args.scrolls} scrolls)…")
        tweets = scrape(args.url, args.scrolls)
    else:
        ap.error("pass --input <extension export> (recommended) or --url <x page>")
    print(f"  {len(tweets)} tweets")

    clf = None
    if args.filter == "like":
        print("Loading models (InsightFace + CLIP)…")
        from classify import Classifier, load_image
        clf = Classifier()

    kept = []
    for t in tweets:
        t["gender"] = guess_gender(t["username"])
        t["imageCount"] = len(t["images"])
        t["imageUrl"] = t["images"][0] if t["images"] else "none"
        t["matchUrl"] = t["imageUrl"]
        t["decision"] = ""
        t["faceCount"] = t["faceGender"] = t["faceDet"] = t["clipPos"] = None

        if args.filter == "any" and t["imageCount"] == 0:
            continue
        if args.filter == "like":
            if t["imageCount"] == 0:
                continue
            from classify import load_image
            matched = False; info = {}
            for url in t["images"]:
                try:
                    info = clf.classify(load_image(cache_image(url)))
                except Exception as e:
                    info = {"match": False, "reason": f"err:{e}"}
                t["faceCount"], t["faceGender"] = info.get("faceCount"), info.get("faceGender")
                t["faceDet"], t["clipPos"] = info.get("faceDet"), info.get("clipPos")
                if info.get("match"):
                    matched = True; t["matchUrl"] = url  # the image that actually matched
                    break
            t["decision"] = "match" if matched else (info.get("reason") or "reject")
            if not matched:
                continue
        else:
            t["decision"] = "match"
        kept.append(t)

    print(f"  {len(kept)} kept after filter='{args.filter}'")
    (config.OUT / "tweets.json").write_text(json.dumps(tweets, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(config.OUT / "tweets.csv", tweets)
    write_csv(config.OUT / "tweets_filtered.csv", kept)
    contact_sheet(kept if args.filter != "all" else tweets, config.OUT / "contact_sheet.jpg")
    print("Wrote out/tweets.json, out/tweets.csv, out/tweets_filtered.csv, out/contact_sheet.jpg")


if __name__ == "__main__":
    main()
