# xtool — standalone X scraper + image classifier (Python)

A local, testable replacement for the browser extension. It scrapes X posts with
Playwright and filters images with an **ensemble of two models**:

- **InsightFace** (`buffalo_l`) — face detection + gender. Gives face count, gender
  and face size.
- **CLIP** (zero-shot) — semantic score: "woman selfie/portrait" vs man / group /
  landscape / screenshot / collage.

A post is kept (`--filter like`) only when a photo is a **solo female portrait**.
The decision (`classify.decide`) combines both models:
- `>1 face` → group (reject); `0 faces` → reject **unless** CLIP is very confident
  it's a woman and not a group (rescues faces hidden/cropped/zoomed out).
- `1 face` → must be female, large enough, and CLIP-confirmed. InsightFace gender is
  trusted on large faces; on small faces (where it's noisier) a confident CLIP
  "woman" overrides a wrong `male` call.

All thresholds are in `config.py`; `eval.py` measures the effect of each.

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

```bash
# 1) Log into X once (persists a browser profile under out/chrome-profile)
.venv/bin/python login.py

# 2) Scrape + classify a profile/search/timeline
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

On the 82-image review set (49 samples + 33 reviewed), after correcting the labels
and adding the recall boosters: **accuracy 100%, precision 100%, recall 100%**
(up from 78% recall / 80% accuracy with the naive strict rule). Note this is the set
the thresholds were tuned on — expect somewhat lower in the wild; the transferable
wins are recovering faces the detector misses and CLIP-overriding small-face gender
errors. Every booster decision is logged in the `decision` column so you can audit it.

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
