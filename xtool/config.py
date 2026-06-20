"""Tunable settings for the X scraper + image classifier.

Everything you'd want to adjust to trade precision vs recall lives here.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
IMG_CACHE = OUT / "imgs"
PROFILE_DIR = OUT / "chrome-profile"   # persistent Playwright profile (holds X login)

# ---- Scraper ----------------------------------------------------------------
SCROLLS = 10
SCROLL_DELAY = (2.0, 3.0)               # random seconds between scrolls
HEADLESS = False                        # X login + anti-bot → run headed

# ---- InsightFace (primary face/gender model) --------------------------------
INSIGHT_MODEL = "buffalo_l"             # "buffalo_s" is smaller/faster
DET_SIZE = (640, 640)
DET_SCORE_MIN = 0.45                    # min face-detection confidence
FACE_SIZE_MIN = 0.045                   # face bbox width / image width (portrait framing)
ALLOW_FACES = 1                         # exactly this many faces = "solo"

# ---- Recall boosters (tuned on the labeled review set) ----------------------
# Recover real women InsightFace misses (faces hidden/cropped/zoomed, and faceless
# body shots — see @Atosa_Aryan). Caveat: a faceless image can't be face-counted, so
# at this threshold a faceless *group* of women can also slip through (CLIP can't tell
# them apart). Raise toward 0.96 if you want to exclude faceless body shots again.
NOFACE_RESCUE_CLIP = 0.85               # 0 faces but CLIP this confident "woman" -> keep
NOFACE_MAX_GROUP = 0.15                 #   ...unless CLIP also reads "group of people"
GENDER_TRUST_SIZE = 0.20               # trust a 'male' call only on faces this big
GENDER_CLIP_OVERRIDE = 0.90             # below that size, CLIP this confident overrides 'male'

# ---- CLIP (second / ensemble model, zero-shot) ------------------------------
CLIP_MODEL = "ViT-B-32"
CLIP_PRETRAINED = "openai"
CLIP_POS = [
    "a selfie of a woman",
    "a portrait photo of a woman",
    "a photo of a woman",
]
CLIP_NEG = [
    "a photo of a man",                 # index 0 of the negatives == "man" (decide() reads this)
    "a group of people",                # index 1 == "group" (decide() reads this)
    "a landscape photograph",
    "a screenshot or chart",
    "a collage of pictures",
    "a photo of an object",
    "a cat or a dog",                   # appended: cut down no-face object/animal false positives
    "a pet animal",
    "a decorative plate or pattern",
]
CLIP_MIN = 0.35                         # min softmax mass on the positive (woman) prompts
