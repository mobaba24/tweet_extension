"""Telegram caption bot — users send their OWN photo, pick platform + vibe,
toggle language, then pick the caption they like → bot returns the image + that
caption ready to post on Instagram/X. 3 free/day; earn +3 via channel/bot tasks.

    python caption_bot.py        # needs TELEGRAM_BOT_TOKEN in engage/.env
"""
import asyncio
import logging
from urllib.parse import quote

import config
import credits
import signups
import stats
import tasks
from caption import CaptionEngine, TONES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("caption-bot")
engine = CaptionEngine()

PLATFORMS = [("📸 اینستاگرام", "instagram"), ("🐦 ایکس (توییتر)", "x")]
PLAT_FA = {"instagram": "اینستاگرام", "x": "ایکس"}
TONE_FA = {
    "funny": "😄 بامزه", "romantic": "❤️ عاشقانه", "motivational": "💪 انگیزشی",
    "poetic": "🌙 شاعرانه", "minimal": "✨ مینیمال", "classy": "🕶️ باکلاس",
}
NUM = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def _is_admin(uid):
    return uid in config.TG_ADMIN_IDS


def _main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 ساخت کپشن برای عکس", callback_data="menu:new")],
        [InlineKeyboardButton("💎 اعتبار من", callback_data="menu:credits"),
         InlineKeyboardButton("ℹ️ راهنما", callback_data="menu:help")],
    ])


async def start(update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "سلام! 🤖 به ربات کپشن‌ساز خوش اومدی.\nچیکار کنم برات؟", reply_markup=_main_menu())


async def on_menu(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    what = q.data.split(":", 1)[1]
    if what == "new":
        await q.edit_message_text("یه عکس برام بفرست 📸 تا برات کپشن بسازم.")
    elif what == "credits":
        await q.edit_message_text(
            f"💎 اعتبار امروزت: {credits.available(q.from_user.id)}\n"
            f"روزی {config.FREE_PER_DAY} کپشن رایگان داری.", reply_markup=_main_menu())
    elif what == "help":
        await q.edit_message_text(
            "🔹 یه عکس بفرست\n🔹 شبکه (اینستا/ایکس) و حال‌وهوا رو انتخاب کن\n"
            "🔹 از بین کپشن‌ها شماره‌ی هرکدوم رو که خواستی بزن تا با عکس آماده‌ی پست بشه ✅\n\n"
            f"روزی {config.FREE_PER_DAY} کپشن رایگان؛ برای بیشتر، تسک‌ها رو انجام بده.",
            reply_markup=_main_menu())


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


def _result_kb(tone, lang, n):
    other = "English" if lang == "Persian" else "Persian"
    label = "🌐 English" if lang == "Persian" else "🌐 فارسی"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(NUM[i], callback_data=f"pick:{i}") for i in range(min(n, len(NUM)))],
        [InlineKeyboardButton("🔁 یه سری دیگه", callback_data=f"tone:{tone}"),
         InlineKeyboardButton(label, callback_data=f"lang:{other}")],
    ])


async def _show_tasks(q, uid, note=""):
    pending = [t for t in tasks.list_tasks() if t["id"] not in credits.done_tasks(uid)]
    if not pending:
        await q.edit_message_text(note + "اعتبار امروزت تموم شد 🙏 فردا دوباره کپشن رایگان داری 🌙")
        return
    rows = [[InlineKeyboardButton(("📢 " if t["type"] == "channel" else "🤖 ") + t["title"], url=t["url"])]
            for t in pending]
    rows.append([InlineKeyboardButton("✅ بررسی و دریافت اعتبار", callback_data="verify")])
    await q.edit_message_text(
        note + "اعتبار رایگان امروزت تموم شد 🙏\n"
        f"برای {config.TASK_BONUS} کپشن بیشتر یکی از کارهای زیر رو انجام بده، بعد «بررسی» رو بزن:",
        reply_markup=InlineKeyboardMarkup(rows))


async def _render(q, ctx):
    uid = q.from_user.id
    tone = ctx.user_data.get("tone")
    file_id = ctx.user_data.get("photo_id")
    platform = ctx.user_data.get("platform", "instagram")
    lang = ctx.user_data.get("lang", config.TG_REPLY_LANG)
    if not (file_id and tone):
        await q.edit_message_text("اول یه عکس بفرست تا شروع کنیم 🙂")
        return
    if credits.available(uid) <= 0:
        await _show_tasks(q, uid)
        return
    try:
        f = await ctx.bot.get_file(file_id)
        img = bytes(await f.download_as_bytearray())
        caps = await asyncio.to_thread(engine.generate, img, "image/jpeg", platform, lang, tone)
    except Exception as e:  # noqa: BLE001
        log.warning("caption failed: %s", e)
        await q.edit_message_text("یه مشکلی پیش اومد 😅 دوباره امتحان کن.")
        return
    credits.consume(uid)
    stats.record(uid)
    ctx.user_data["caps"] = caps
    head = TONE_FA.get(tone, "") + ("" if lang == "Persian" else " · EN")
    body = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(caps))
    await q.edit_message_text(
        f"کپشن‌ها {head}:\n\n{body}\n\nکدومش رو می‌خوای؟ شماره‌شو بزن 👇\n"
        f"— اعتبار باقی‌مونده: {credits.available(uid)}",
        reply_markup=_result_kb(tone, lang, len(caps)))


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


async def on_pick(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    idx = int(q.data.split(":", 1)[1])
    caps = ctx.user_data.get("caps") or []
    file_id = ctx.user_data.get("photo_id")
    platform = ctx.user_data.get("platform", "instagram")
    if not caps or idx >= len(caps) or not file_id:
        await q.answer("دوباره امتحان کن 🙂")
        return
    await q.answer("آماده شد ✅")
    cap = caps[idx]
    chat_id = q.message.chat_id
    # the photo + chosen caption, ready to post
    await ctx.bot.send_photo(chat_id, file_id, caption=cap)
    # the caption alone + share helpers (honest: a link can't attach the image)
    share_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🐦 آماده‌سازی توییت (فقط متن)", url=f"https://twitter.com/intent/tweet?text={quote(cap)}")],
        [InlineKeyboardButton("📸 باز کردن اینستاگرام", url="https://www.instagram.com/")],
    ])
    await ctx.bot.send_message(
        chat_id,
        "📋 کپشن آماده‌ست:\n\n" + cap +
        "\n\n⚠️ تلگرام نمی‌تونه عکس رو مستقیم تو پست ایکس/اینستا بذاره. پس:\n"
        "۱) روی عکس بالا بزن و ذخیره‌ش کن 💾\n"
        "۲) ایکس: دکمه‌ی پایین متن رو آماده می‌کنه، عکس رو خودت ضمیمه کن.\n"
        "۳) اینستاگرام: پست جدید بساز، عکس رو بذار و کپشن رو پیست کن.",
        reply_markup=share_kb)


async def on_verify(update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer("در حال بررسی…")
    granted = await _verify_tasks(uid, ctx)
    if granted and ctx.user_data.get("photo_id") and ctx.user_data.get("tone"):
        await _render(q, ctx)
    elif granted:
        await q.edit_message_text(f"✅ {granted} اعتبار اضافه شد! یه عکس بفرست تا کپشن بسازم.")
    else:
        await _show_tasks(q, uid, note="هنوز انجامش ندادی یا تأیید نشد 🤔\n")


async def _verify_tasks(uid, ctx):
    granted = 0
    for t in tasks.list_tasks():
        if t["id"] in credits.done_tasks(uid):
            continue
        ok = False
        if t["type"] == "channel":
            try:
                m = await ctx.bot.get_chat_member(t["target"], uid)
                ok = m.status in ("member", "administrator", "creator")
            except Exception:  # noqa: BLE001
                ok = False
        elif t["type"] == "bot":
            ok = signups.has(t["target"], uid)
        if ok and credits.grant(uid, t["id"], t.get("bonus")):
            granted += t.get("bonus", config.TASK_BONUS)
    return granted


# ---- Admin commands ---------------------------------------------------------
async def cmd_stats(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    s = stats.summary()
    await update.effective_message.reply_text(
        f"📊 آمار\nکاربرها: {s['users']}\nکپشن‌های ساخته‌شده: {s['captions']}\nتعداد تسک‌ها: {len(tasks.list_tasks())}")


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
        except Exception:  # noqa: BLE001
            pass
    await update.effective_message.reply_text(f"✅ ارسال شد به {sent} از {len(ids)} کاربر.")


async def cmd_addchannel(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.effective_message.reply_text("استفاده: /addchannel @username عنوان دلخواه")
        return
    target = ctx.args[0]
    title = " ".join(ctx.args[1:]).strip() or target
    url = "https://t.me/" + target.lstrip("@") if target.startswith("@") else target
    tid = tasks.add("channel", target, url, title)
    await update.effective_message.reply_text(
        f"✅ کانال اضافه شد (id={tid}).\n⚠️ ربات رو ادمینِ {target} کن تا بتونه عضویت رو بررسی کنه.")


async def cmd_addbot(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if len(ctx.args) < 2:
        await update.effective_message.reply_text(
            "استفاده: /addbot <code> <deeplink> عنوان\nمثال: /addbot heefan https://t.me/heefan_bot?start=cap هیفان")
        return
    code, url = ctx.args[0], ctx.args[1]
    title = " ".join(ctx.args[2:]).strip() or code
    tid = tasks.add("bot", code, url, title)
    await update.effective_message.reply_text(
        f"✅ ربات اضافه شد (id={tid}, code={code}). تأیید بعد از «تکمیل ثبت‌نام» در ربات مقصد انجام می‌شه.")


async def cmd_tasks(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    items = tasks.list_tasks()
    if not items:
        await update.effective_message.reply_text("هیچ تسکی تعریف نشده. با /addchannel یا /addbot اضافه کن.")
        return
    lines = [f"#{t['id']} [{t['type']}] {t['title']} → {t['target']}" for t in items]
    await update.effective_message.reply_text("📋 تسک‌ها:\n" + "\n".join(lines) + "\n\nحذف: /deltask <id>")


async def cmd_deltask(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.effective_message.reply_text("استفاده: /deltask <id>")
        return
    ok = tasks.remove(ctx.args[0])
    await update.effective_message.reply_text("✅ حذف شد." if ok else "پیدا نشد.")


async def cmd_grant(update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if len(ctx.args) < 2 or not ctx.args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("استفاده: /grant <user_id> <task_id>")
        return
    ok = credits.grant(int(ctx.args[0]), ctx.args[1])
    await update.effective_message.reply_text("✅ اعتبار داده شد." if ok else "قبلاً گرفته یا نامعتبره.")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in engage/.env (see .env.example)")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    for name, fn in [("start", start), ("stats", cmd_stats), ("broadcast", cmd_broadcast),
                     ("addchannel", cmd_addchannel), ("addbot", cmd_addbot), ("tasks", cmd_tasks),
                     ("deltask", cmd_deltask), ("grant", cmd_grant)]:
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(CallbackQueryHandler(on_menu, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(on_platform, pattern=r"^plat:"))
    app.add_handler(CallbackQueryHandler(on_tone, pattern=r"^tone:"))
    app.add_handler(CallbackQueryHandler(on_lang, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_pick, pattern=r"^pick:"))
    app.add_handler(CallbackQueryHandler(on_verify, pattern=r"^verify$"))
    log.info("Caption bot running (free/day=%s, bonus=%s, admins=%s)…",
             config.FREE_PER_DAY, config.TASK_BONUS, config.TG_ADMIN_IDS)
    app.run_polling()


if __name__ == "__main__":
    main()
