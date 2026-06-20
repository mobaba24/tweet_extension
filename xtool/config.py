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
DET_SCORE_MIN = 0.55                    # min face-detection confidence
FACE_SIZE_MIN = 0.06                    # face bbox width / image width (portrait framing)
ALLOW_FACES = 1                         # exactly this many faces = "solo"

# ---- CLIP (second / ensemble model, zero-shot) ------------------------------
CLIP_MODEL = "ViT-B-32"
CLIP_PRETRAINED = "openai"
CLIP_POS = [
    "a selfie of a woman",
    "a portrait photo of a woman",
    "a photo of a woman",
]
CLIP_NEG = [
    "a photo of a man",                 # index 0 of the negatives == "man"
    "a group of people",
    "a landscape photograph",
    "a screenshot or chart",
    "a collage of pictures",
    "a photo of an object",
]
CLIP_MIN = 0.35                         # min softmax mass on the positive (woman) prompts

# ---- Ensemble ---------------------------------------------------------------
# "and"  : InsightFace AND CLIP must agree (high precision) — default
# "or"   : either model is enough (high recall)
# "blend": weighted score >= BLEND_THRESH
VOTE = "and"
BLEND_THRESH = 0.50
