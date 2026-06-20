# xtool — standalone X scraper + image classifier (Python)

A local, testable tool that takes X posts (from the extension's export — recommended
— or via Playwright) and filters images with an **ensemble of two models**:

- **InsightFace** (`buffalo_l`) — face detection + gender. Gives face count, gender
  and face size.
- **CLIP** (zero-shot) — semantic score: "woman selfie/portrait" vs man / group /
  landscape / screenshot / collage.

A post is kept (`--filter like`) only when a photo is a **solo female portrait**.
The decision (`classify.decide`) combines both models. Default is **STRICT** (tuned
for zero wrong images — every keep is trustworthy):
- `>1 face` → group (reject); `0 faces` → reject.
- `1 face` → keep only if InsightFace says **female**, the face is large enough
  (`FACE_SIZE_MIN`), detection is confident (`DET_SCORE_MIN`), and CLIP confirms
  "woman" (`CLIP_MIN`, woman > man).

This deliberately drops faceless/body shots and back/distant shots (no verifiable
face). To **loosen** and also keep those (at the cost of occasional wrong images),
set in `config.py`: `NOFACE_RESCUE_CLIP = 0.85` (keep 0-face images CLIP is sure are
women) and `GENDER_TRUST_SIZE = 0.20` (let confident CLIP override a small-face
`male` call). All thresholds are in `config.py`; `eval.py` measures the effect.

## Setup

```bash
cd xtool
python3.12 -m venv .venv          # needs a Python built with lzma (3.12 here)
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

First model run downloads weights once: InsightFace `buffalo_l` (~300 MB) to
`~/.insightface`, CLIP ViT-B/32 (~340 MB) to the HF cache.

## Use

### Recommended: extension → ingest (X blocks automated browsers)

X detects and blocks Playwright/automation at login, so let the **extension** do the
scraping from your real, logged-in session, then feed its export to this tool:

1. In Chrome, open the X timeline/profile you want, click the **Tweet Scraper**
   extension, set the **Image filter** to **"Only posts with an image"**, and run it.
   It downloads `tweets.json` (every post + all image URLs).
2. Classify that export here — no browser, fully offline:

```bash
.venv/bin/python run.py --input ~/Downloads/tweets.json --filter like
```

`--input` accepts the extension's `tweets.json` **or** `tweets.csv`.

### Alternative: Playwright (only if X isn't blocking you)

```bash
.venv/bin/python login.py                                   # log into X once
.venv/bin/python run.py --url "https://x.com/SomeHandle" --scrolls 10 --filter like
```

Outputs in `out/`:
- `tweets.json` / `tweets.csv` — every scraped post + diagnostics
  (`faceCount, faceGender, faceDet, clipPos, decision`)
- `tweets_filtered.csv` — only the matches
- `contact_sheet.jpg` — labeled grid (green=match, red=reason) to eyeball results

Each record also has the account **gender** inferred from the display name
(`gender_names.py`, the Persian-tuned engine ported from the extension).

## Test / tune accuracy

```bash
.venv/bin/python eval.py            # precision / recall / accuracy + misclassified list
.venv/bin/python eval.py --refresh  # recompute the (cached) model features first
```

Model inference is cached to `out/features.json`, so after the first run you can edit
thresholds in `config.py` and re-run `eval.py` in ~1s to see the effect.

Accuracy (STRICT default):
- 82-image tuning set: **precision 100%** (0 wrong images), recall 86.4%.
- 83-post out-of-sample file: 50 keeps, **all verified solo women** (0 wrong images);
  the trade is faceless/body/back/distant shots are dropped.

The previous looser setting (`NOFACE_RESCUE_CLIP = 0.85`) reached ~100% recall but
admitted occasional wrong images (a decorative plate / pet reflection CLIP misread as
a woman, a faceless group). Strict trades that recall for trustworthy keeps. Every
decision is logged in the `decision` column so you can audit it.

## Files
- `config.py` — all thresholds, CLIP prompts, paths
- `scrape.py` / `login.py` — Playwright scraper (selectors ported from the extension)
- `classify.py` — InsightFace + CLIP ensemble
- `gender_names.py` (+ `gender_names_data.py`) — name→gender
- `eval.py` — accuracy harness
- `run.py` — orchestrator

## Notes
- CPU-only is fine (Apple Silicon). Scraping X is subject to its ToS and anti-bot
  measures — log in as yourself, keep volumes modest, expect occasional breakage if
  X changes its markup.
