"""Ensemble image classifier: keep only solo-female-portrait photos.

Model A — InsightFace (buffalo_l): face detection + gender. Gives how many faces,
          each face's gender, detection confidence and size.
Model B — CLIP (zero-shot): semantic score of the whole image against
          "woman selfie/portrait" prompts vs man/group/landscape/screenshot/etc.

A photo matches when (default VOTE="and") BOTH agree it's a solo woman portrait.
The two models are complementary: InsightFace nails face-count/gender, CLIP catches
non-person scenes (landscapes, screenshots, collages) and overall "selfie-ness".
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
        pos_mass = float(probs[:self.n_pos].sum())
        man = float(probs[self.n_pos])  # first negative prompt is "a photo of a man"
        return {"posMass": pos_mass, "womanOverMan": pos_mass > man}

    # ---- ensemble decision -------------------------------------------------
    def classify(self, pil):
        faces = self._insight(pil)
        clip = self._clip(pil)
        face = faces[0] if faces else None

        insight_ok = (
            len(faces) == config.ALLOW_FACES
            and face is not None
            and face["gender"] == "female"
            and face["det"] >= config.DET_SCORE_MIN
            and face["wFrac"] >= config.FACE_SIZE_MIN
        )
        clip_ok = clip["posMass"] >= config.CLIP_MIN and clip["womanOverMan"]

        if config.VOTE == "and":
            match = insight_ok and clip_ok
        elif config.VOTE == "or":
            match = insight_ok or clip_ok
        else:  # blend
            score = 0.5 * (1.0 if insight_ok else 0.0) + 0.5 * clip["posMass"]
            match = score >= config.BLEND_THRESH

        return {
            "match": bool(match),
            "reason": self._reason(faces, face, insight_ok, clip_ok),
            "faceCount": len(faces),
            "faceGender": face["gender"] if face else None,
            "faceDet": round(face["det"], 3) if face else None,
            "faceSizeFrac": round(face["wFrac"], 3) if face else None,
            "clipPos": round(clip["posMass"], 3),
            "clipWomanOverMan": clip["womanOverMan"],
            "insightOk": insight_ok,
            "clipOk": clip_ok,
        }

    @staticmethod
    def _reason(faces, face, insight_ok, clip_ok):
        if not faces:
            return "no-face"
        if len(faces) > config.ALLOW_FACES:
            return "group"
        if face and face["gender"] != "female":
            return "not-female"
        if face and face["wFrac"] < config.FACE_SIZE_MIN:
            return "face-too-small"
        if not clip_ok:
            return "clip-reject"
        if insight_ok and clip_ok:
            return "match"
        return "reject"


def load_image(path):
    return Image.open(path)
