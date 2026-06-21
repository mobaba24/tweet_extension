"""Caption engine — given a user's photo + options, write post-ready captions
for Instagram or X using Claude's vision."""
import base64
import anthropic
import config

# tone key -> description for the prompt
TONES = {
    "funny": "funny / playful, a bit cheeky",
    "romantic": "romantic / dreamy",
    "motivational": "motivational / confident",
    "poetic": "poetic / deep and a little artsy",
    "minimal": "minimal, very short, almost one-word",
    "classy": "classy / stylish",
}

SYSTEM = """You write social-media captions. You'll see a photo and write {n} captions for a {platform} post, in {lang}, with a {tone} vibe.

Rules:
- Base them on what's ACTUALLY in the photo — the scene, mood, outfit, activity, setting, lighting.
- Make them natural and post-ready — the kind a real person actually posts.
- Tasteful and respectful: it's the user's own photo. Caption the vibe, never make crude or sexual remarks about anyone's body.
- {platform_rule}
- Output EXACTLY {n} captions, each on its own line, numbered "1." "2." "3.". No preamble, no explanation, nothing else."""

_RULES = {
    "instagram": "Instagram style: a short line or two; you may add 2-4 relevant hashtags at the end of each.",
    "x": "X (Twitter) style: punchy and short, usually one line, at most 1-2 hashtags, fits in a tweet.",
}


class CaptionEngine:
    def __init__(self, model=None):
        self.client = anthropic.Anthropic()
        self.model = model or config.MODEL

    def generate(self, image_bytes, media_type="image/jpeg", platform="instagram",
                 lang="Persian", tone="funny", n=3):
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        system = SYSTEM.format(
            n=n,
            platform="Instagram" if platform == "instagram" else "X (Twitter)",
            lang=lang,
            tone=TONES.get(tone, tone),
            platform_rule=_RULES.get(platform, _RULES["instagram"]),
        )
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": f"Write {n} {tone} captions for my {platform} post."},
            ]}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()
