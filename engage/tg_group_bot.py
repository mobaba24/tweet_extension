"""Telegram group bot — auto-replies in Persian to messages, using the shared
reply engine. Add the bot to your group; for it to read every message, disable
privacy mode in @BotFather (/setprivacy -> Disable) or make it a group admin.

    python tg_group_bot.py        # needs TELEGRAM_BOT_TOKEN in engage/.env
"""
import logging
import time

import config
from llm import ReplyEngine
from safety import is_engageable
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tg")

engine = ReplyEngine()
_last = {}  # user_id -> last reply time (per-user throttle so it isn't spammy)


async def on_message(update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.text or (user and user.is_bot):
        return
    now = time.monotonic()
    if user and now - _last.get(user.id, 0) < config.TG_MIN_SECONDS_PER_USER:
        return
    ok, _ = is_engageable(msg.text)
    if not ok:
        return
    try:
        reply = engine.draft(msg.text, lang=config.TG_REPLY_LANG)
    except Exception as e:  # noqa: BLE001 - never crash the bot on one message
        log.warning("draft failed: %s", e)
        return
    if not reply:
        return
    if user:
        _last[user.id] = now
    await msg.reply_text(reply)


async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("سلام! من اینجام و به پیام‌ها جواب می‌دم 🙂")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in engage/.env (see .env.example)")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Telegram bot running (reply lang=%s, model=%s)…", config.TG_REPLY_LANG, config.MODEL)
    app.run_polling()


if __name__ == "__main__":
    main()
