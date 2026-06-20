"""Ensemble image classifier: keep only solo-female-portrait photos.

Model A — InsightFace (buffalo_l): face detection + gender. Gives how many faces,
          each face's gender, detection confidence and size.
Model B — CLIP (zero-shot): semantic score of the whole image against
          "woman selfie/portrait" prompts vs man/group/landscape/screenshot/etc.

A photo matches when the combined rule in decide() is satisfied. The two models are
complementary: InsightFace nails face-count/gender, CLIP catches non-person scenes
(landscapes, screenshots, collages) and rescues faces the detector misses.
"""
import numpy as np
from PIL import Image
import config


class Classifier:
    def __init__(self):
        self._init_insight()
        self._init_clip()

    # ---- model init --------------------------------------------------------
    def _init_insight(self):
        from insightface.app import FaceAnalysis
        self.app = FaceAnalysis(name=config.INSIGHT_MODEL,
                                providers=["CPUExecutionProvider"])
        self.app.prepare(ctx_id=-1, det_size=config.DET_SIZE)

    def _init_clip(self):
        import torch, open_clip
        self.torch = torch
        model, _, preprocess = open_clip.create_model_and_transforms(
            config.CLIP_MODEL, pretrained=config.CLIP_PRETRAINED)
        model.eval()
        self.clip_model = model
        self.preprocess = preprocess
        tokenizer = open_clip.get_tokenizer(config.CLIP_MODEL)
        prompts = list(config.CLIP_POS) + list(config.CLIP_NEG)
        with torch.no_grad():
            tf = model.encode_text(tokenizer(prompts))
            tf /= tf.norm(dim=-1, keepdim=True)
        self.text_features = tf
        self.n_pos = len(config.CLIP_POS)

    # ---- per-model inference ----------------------------------------------
    def _insight(self, pil):
        bgr = np.ascontiguousarray(np.array(pil.convert("RGB"))[:, :, ::-1])
        H, W = bgr.shape[:2]
        faces = []
        for f in self.app.get(bgr):
            x1, y1, x2, y2 = f.bbox
            faces.append({
                "gender": "female" if int(f.gender) == 0 else "male",
                "det": float(f.det_score),
                "wFrac": float((x2 - x1) / W),
            })
        faces.sort(key=lambda d: d["wFrac"], reverse=True)  # largest face first
        return faces

    def _clip(self, pil):
        torch = self.torch
        img = self.preprocess(pil.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            imf = self.clip_model.encode_image(img)
            imf /= imf.norm(dim=-1, keepdim=True)
            probs = (100.0 * imf @ self.text_features.T).softmax(dim=-1).squeeze(0).numpy()
        return {
            "posMass": float(probs[:self.n_pos].sum()),   # woman-portrait mass
            "man": float(probs[self.n_pos]),               # "a photo of a man"
            "group": float(probs[self.n_pos + 1]),         # "a group of people"
        }

    # ---- raw signals (for tuning / diagnostics) ---------------------------
    def features(self, pil):
        faces = self._insight(pil)
        clip = self._clip(pil)
        big = faces[0] if faces else None
        return {
            "faceCount": len(faces),
            "faceGender": big["gender"] if big else None,
            "faceDet": round(big["det"], 3) if big else None,
            "faceSizeFrac": round(big["wFrac"], 3) if big else None,
            "clipPos": round(clip["posMass"], 3),
            "clipMan": round(clip["man"], 3),
            "clipGroup": round(clip["group"], 3),
        }

    def classify(self, pil):
        return decide(self.features(pil))


def decide(f, cfg=config):
    """Ensemble decision -> solo female portrait? Operates on features() output.

    Rules (tuned on the labeled review set):
      - >1 face                         -> group (reject)
      - 0 faces but CLIP confident "woman" -> keep (face hidden/cropped/zoomed, or a
        faceless body shot), unless CLIP also reads "group". NOTE: a faceless image
        can't be face-counted, so a faceless group of women can slip through here.
      - 1 face: must be female & large enough & CLIP agrees. InsightFace gender is
        trusted on large faces; on small faces (where it's noisier) a confident CLIP
        "woman" can override a 'male' call.
    """
    n = f["faceCount"]
    clip_pos, clip_man, clip_group = f["clipPos"], f["clipMan"], f["clipGroup"]
    clip_woman = clip_pos > clip_man

    def out(match, reason):
        return {"match": bool(match), "reason": reason, **f}

    if n > cfg.ALLOW_FACES:
        return out(False, "group")

    if n == 0:
        if (cfg.NOFACE_RESCUE_CLIP is not None and clip_pos >= cfg.NOFACE_RESCUE_CLIP
                and clip_woman and clip_group <= cfg.NOFACE_MAX_GROUP):
            return out(True, "rescue-noface")
        return out(False, "no-face")

    size, det, female = f["faceSizeFrac"], f["faceDet"], f["faceGender"] == "female"
    if det < cfg.DET_SCORE_MIN:
        return out(False, "low-det")

    if size < cfg.FACE_SIZE_MIN:
        # solo but small face — keep only if CLIP rescue is on and confident
        if cfg.NOFACE_RESCUE_CLIP is not None and clip_pos >= cfg.NOFACE_RESCUE_CLIP and clip_woman:
            return out(True, "small-but-clip")
        return out(False, "face-too-small")

    if not female:
        # trust a 'male' call on a big/clear face; on smaller faces defer to CLIP
        if size >= cfg.GENDER_TRUST_SIZE:
            return out(False, "male-confident")
        if not (clip_pos >= cfg.GENDER_CLIP_OVERRIDE and clip_woman):
            return out(False, "not-female")
        # else: CLIP overrides a small-face male -> treat as female

    if clip_pos >= cfg.CLIP_MIN and clip_woman:
        return out(True, "match")
    return out(False, "clip-reject")


def load_image(path):
    return Image.open(path)
