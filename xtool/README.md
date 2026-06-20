# xtool — standalone X scraper + image classifier (Python)

A local, testable replacement for the browser extension. It scrapes X posts with
Playwright and filters images with an **ensemble of two models**:

- **InsightFace** (`buffalo_l`) — face detection + gender. Gives face count, gender
  and face size.
- **CLIP** (zero-shot) — semantic score: "woman selfie/portrait" vs man / group /
  landscape / screenshot / collage.

A post is kept (`--filter like`) only when a photo is a **solo female portrait**:
exactly one face, female, large enough, AND CLIP agrees. The two models vote
(`--vote and|or|blend`), so you trade precision vs recall with a number, not by guessing.

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
.venv/bin/python run.py --url "https://x.com/SomeHandle" --scrolls 10 --filter like --vote and
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
.venv/bin/python eval.py        # runs the classifier on a labeled set, prints
                                # precision / recall / accuracy + misclassified list
```

Tune thresholds in `config.py` (`DET_SCORE_MIN`, `FACE_SIZE_MIN`, `CLIP_MIN`, `VOTE`)
and re-run `eval.py`. On the seeded review set the strict (`and`) ensemble gives
**100% precision** (no wrong images kept) at ~78% recall; loosen toward `or`/`blend`
for higher recall.

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
