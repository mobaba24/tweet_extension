# engage — Telegram caption bot (+ reply engine)

A Telegram bot where people send their **own** photo, pick a platform and a vibe,
and get post-ready captions for Instagram or X — written by Claude's vision.
Clearly a bot; people come to it on purpose. No scraping, no targeting.

## Setup

```bash
cd engage
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN
```

## Caption bot (main product)

```bash
.venv/bin/python caption_bot.py
```

Flow: user sends a photo → bot asks **platform** (Instagram / X) → asks **vibe**
(😄 بامزه / ❤️ عاشقانه / 💪 انگیزشی / 🌙 شاعرانه / ✨ مینیمال / 🕶️ باکلاس) →
returns 3 captions, with a "🔁 یه سری دیگه بساز" button to re-roll. Replies in
`TG_REPLY_LANG` (default Persian). Instagram captions add a few hashtags; X
captions stay short and punchy.

Get a bot token from **@BotFather**, put it in `TELEGRAM_BOT_TOKEN`. Captions are
generated from the user's own uploaded photo — tasteful by design (the vibe, not
the body).

## Files
- `caption.py` — vision caption engine (`CaptionEngine.generate`)
- `caption_bot.py` — the Telegram caption bot (photo → options → captions)
- `llm.py` — generic Claude reply engine (`ReplyEngine.draft`) — used by the
  optional community reply bot below
- `tg_group_bot.py` — optional: a transparent, respectful community reply bot
  (on-topic Persian replies, not romantic, not gender-targeted)
- `safety.py`, `ingest.py`, `config.py`, `demo.py`

## Test the engine offline

```bash
.venv/bin/python - <<'PY'
from caption import CaptionEngine
print(CaptionEngine().generate(open("photo.jpg","rb").read(), tone="funny", platform="instagram"))
PY
```

## Sharing a chosen caption
After picking a caption the bot returns the **photo + that caption**, plus:
- a tip to use Telegram's own **photo → Share** (carries the image straight into
  the IG/X app — then paste the caption);
- a **🐦 prepare-tweet** button (X's share link pre-fills text only — a link can't
  attach an image), and an **open-Instagram** button.

True one-tap image+caption posting is only possible via API:
- **X** — `x_post.py` has the upload+tweet core; pending the approved X developer
  account + a per-user OAuth connect flow (see that file's header). Then a
  "🚀 پست در ایکس" button posts the photo+caption directly.
- **Instagram** — not possible for personal accounts (API is Business/Creator only),
  so IG stays save-and-paste.

## Deploy
Long-running bot — deploy to the VPS like the other Telegram bots
(edit → deploy → verify logs). `.env`, `.venv/`, `out/` are gitignored.
