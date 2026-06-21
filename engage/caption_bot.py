"""Telegram caption bot — users send their OWN photo, pick a platform + vibe,
toggle language, and get post-ready captions. Clearly a bot; people come to it.

    python caption_bot.py        # needs TELEGRAM_BOT_TOKEN in engage/.env
"""
import asyncio
import logging

import config
import stats
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


def _is_admin(uid):
    return uid in config.TG_ADMIN_IDS


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


def _result_kb(tone, lang):
    other = "English" if lang == "Persian" else "Persian"
    label = "🌐 English" if lang == "Persian" else "🌐 فارسی"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 یه سری دیگه بساز", callback_data=f"tone:{tone}")],
        [InlineKeyboardButton(label, callback_data=f"lang:{other}")],
    ])


async def _render(q, ctx):
    tone = ctx.user_data.get("tone")
    file_id = ctx.user_data.get("photo_id")
    platform = ctx.user_data.get("platform", "instagram")
    lang = ctx.user_data.get("lang", config.TG_REPLY_LANG)
    if not (file_id and tone):
        await q.edit_message_text("اول یه عکس بفرست تا شروع کنیم 🙂")
        return
    try:
        f = await ctx.bot.get_file(file_id)
        img = bytes(await f.download_as_bytearray())
        caps = await asyncio.to_thread(engine.generate, img, "image/jpeg", platform, lang, tone)
    except Exception as e:  # noqa: BLE001
        log.warning("caption failed: %s", e)
        await q.edit_message_text("یه مشکلی پیش اومد 😅 دوباره امتحان کن.")
        return
    stats.record(q.from_user.id)
    head = TONE_FA.get(tone, "") + ("" if lang == "Persian" else " · EN")
    await q.edit_message_text(f"کپشن‌ها {head}:\n\n{caps}", reply_markup=_result_kb(tone, lang))


async def on_tone(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("دارم می‌سازم… ⏳")
    ctx.user_data["tone"] = q.data.split(":", 1)[1]
    await _render(q, ctx)


async def on_lang(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("زبان عوض شد…")
    ctx.user_data["lang"] = q.data.split(":", 1)[1]
    await _render(q, ctx)


# ---- Admin commands ---------------------------------------------------------
async def cmd_stats(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    s = stats.summary()
    await update.effective_message.reply_text(
        f"📊 آمار ربات\nکاربرها: {s['users']}\nکپشن‌های ساخته‌شده: {s['captions']}")


async def cmd_broadcast(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    text = " ".join(ctx.args).strip()
    if not text:
        await update.effective_message.reply_text("استفاده: /broadcast پیام شما")
        return
    ids = stats.summary()["user_ids"]
    sent = 0
    for uid in ids:
        try:
            await ctx.bot.send_message(uid, text)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:  # noqa: BLE001 - skip blocked/deleted users
            pass
    await update.effective_message.reply_text(f"✅ ارسال شد به {sent} از {len(ids)} کاربر.")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in engage/.env (see .env.example)")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(CallbackQueryHandler(on_platform, pattern=r"^plat:"))
    app.add_handler(CallbackQueryHandler(on_tone, pattern=r"^tone:"))
    app.add_handler(CallbackQueryHandler(on_lang, pattern=r"^lang:"))
    log.info("Caption bot running (default lang=%s, model=%s, admins=%s)…",
             config.TG_REPLY_LANG, config.MODEL, config.TG_ADMIN_IDS)
    app.run_polling()


if __name__ == "__main__":
    main()
