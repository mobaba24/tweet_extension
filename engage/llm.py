"""Shared reply engine — drafts one short, relevant, respectful reply with Claude.
Used by both the Telegram group bot and the X engagement bot."""
import re
import anthropic
import config

SYSTEM = """You write a single short reply to a social-media post or chat message.

You are {persona}.

Rules:
- Write ONE short reply, 1-2 sentences, the way a real person leaves a comment. No preamble, no surrounding quotes, no hashtag spam, no emoji spam.
- Be genuinely relevant: react to what they actually said or shared.
- Reply in {lang}.
- Be warm and respectful. NEVER flirt, sexualize, demean, harass, or comment on someone's body or appearance. Keep it about the content/topic, not the person.
- Do not give medical, legal, or financial advice; do not impersonate anyone; do not ask for personal info.
- If the content is hateful/explicit, or you cannot write something genuinely relevant AND respectful, reply with exactly: SKIP
- Output ONLY the reply text, or SKIP. Nothing else."""


def detect_lang(text):
    return "Persian" if re.search(r"[؀-ۿ]", text or "") else "English"


class ReplyEngine:
    def __init__(self, model=None):
        self.client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
        self.model = model or config.MODEL

    def draft(self, text, lang=None, persona=None, context=None):
        """Return a reply string, or None if the model declined (SKIP)."""
        lang = lang or detect_lang(text)
        system = SYSTEM.format(persona=persona or config.PERSONA, lang=lang)
        user = (f"Context: {context}\n\n" if context else "") + f"Post / message:\n{text}"
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=config.MAX_REPLY_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        if not out or out.strip().upper().rstrip(".!") == "SKIP":
            return None
        return out
