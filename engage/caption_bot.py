"""Telegram caption bot — users send their OWN photo, pick a platform + vibe,
and get post-ready captions. Clearly a bot; people come to it on purpose.

    python caption_bot.py        # needs TELEGRAM_BOT_TOKEN in engage/.env
"""
import logging

import config
from caption import CaptionEngine, TONES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("caption-bot")
engine = CaptionEngine()

PLATFORMS = [("📸 اینستاگرام", "instagram"), ("🐦 ایکس (توییتر)", "x")]
TONE_FA = {
    "funny": "😄 بامزه", "romantic": "❤️ عاشقانه", "motivational": "💪 انگیزشی",
    "poetic": "🌙 شاعرانه", "minimal": "✨ مینیمال", "classy": "🕶️ باکلاس",
}


async def start(update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "سلام! من یه ربات کپشن‌سازم 🤖\nیه عکس برام بفرست تا برات چند تا کپشن خفن بسازم.")


async def on_photo(update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["photo_id"] = update.effective_message.photo[-1].file_id
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=f"plat:{v}")] for t, v in PLATFORMS])
    await update.effective_message.reply_text("عکست رو گرفتم 📸\nکپشن برای کدوم شبکه می‌خوای؟", reply_markup=kb)


async def on_platform(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["platform"] = q.data.split(":", 1)[1]
    keys = list(TONES)
    rows = [[InlineKeyboardButton(TONE_FA[k], callback_data=f"tone:{k}") for k in keys[i:i + 2]]
            for i in range(0, len(keys), 2)]
    await q.edit_message_text("چه حال‌وهوایی داشته باشه؟ 🎭", reply_markup=InlineKeyboardMarkup(rows))


async def on_tone(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("دارم می‌سازم… ⏳")
    tone = q.data.split(":", 1)[1]
    file_id = ctx.user_data.get("photo_id")
    platform = ctx.user_data.get("platform", "instagram")
    if not file_id:
        await q.edit_message_text("اول یه عکس بفرست تا شروع کنیم 🙂")
        return
    try:
        f = await ctx.bot.get_file(file_id)
        img = bytes(await f.download_as_bytearray())
        caps = engine.generate(img, "image/jpeg", platform=platform,
                               lang=config.TG_REPLY_LANG, tone=tone)
    except Exception as e:  # noqa: BLE001
        log.warning("caption failed: %s", e)
        await q.edit_message_text("یه مشکلی پیش اومد 😅 دوباره امتحان کن.")
        return
    again = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 یه سری دیگه بساز", callback_data=f"tone:{tone}")]])
    await q.edit_message_text(f"کپشن‌ها {TONE_FA.get(tone, '')}:\n\n{caps}", reply_markup=again)


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in engage/.env (see .env.example)")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(CallbackQueryHandler(on_platform, pattern=r"^plat:"))
    app.add_handler(CallbackQueryHandler(on_tone, pattern=r"^tone:"))
    log.info("Caption bot running (lang=%s, model=%s)…", config.TG_REPLY_LANG, config.MODEL)
    app.run_polling()


if __name__ == "__main__":
    main()
