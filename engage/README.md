# engage — engagement bots (Telegram + X)

Turns scraped/classified data into **actions**: a shared Claude reply engine, a
Telegram group bot, and (later) an X reply bot via the official API.

**Guardrails:** the reply engine is instructed to be relevant + respectful and to
return `SKIP` for anything hateful/explicit or that it can't answer well — it never
flirts, sexualizes, or comments on appearance. The X side is **review-first** by
default; autonomous posting is opt-in behind hard rate limits. No mass unsolicited
commenting, no fake accounts, no detection evasion.

## Setup

```bash
cd engage
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # then fill in keys (ANTHROPIC_API_KEY required)
```

## Phase 1 — reply engine (works now, no browser/token)

```bash
.venv/bin/python demo.py ~/Downloads/tweets.json 8
```
Prints `{post -> drafted reply}` for the first N posts. Verifies the engine + the
relevance/safety gate. Tune the persona/keywords in `.env`.

## Phase 2 — Telegram group bot (auto-reply in Persian)

1. Create a bot with **@BotFather**, copy the token into `TELEGRAM_BOT_TOKEN`.
2. To let it read every group message, message @BotFather → `/setprivacy` →
   **Disable** (or add the bot as a group admin).
3. Run it:
   ```bash
   .venv/bin/python tg_group_bot.py
   ```
It replies in `TG_REPLY_LANG` (default Persian), throttled per user
(`TG_MIN_SECONDS_PER_USER`) so it isn't spammy.

## Phase 3 — X reply bot (official API)

Needs the approved X developer app keys in `.env`. Built review-first: drafts are
queued for your approval (via Telegram/CLI) before posting; `X_AUTONOMOUS=true`
enables a guarded autonomous mode under `MAX_REPLIES_PER_HOUR/DAY`. *(Coming once
the dev account is approved.)*

## Files
- `config.py` — settings + `.env` loader
- `llm.py` — shared Claude reply engine (`ReplyEngine.draft`)
- `safety.py` — cheap relevance/short-input pre-gate
- `ingest.py` — load an extension export (json/csv)
- `demo.py` — Phase-1 offline demo
- `tg_group_bot.py` — Telegram group bot (Phase 2)

## Deploy
Both bots are long-running; deploy to the VPS like the other Telegram bots
(edit → deploy → verify logs). Keep `.env` out of git (it's gitignored).
