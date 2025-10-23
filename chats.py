import asyncio
import os
from yt_dlp import YoutubeDL
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from telegram.request import HTTPXRequest

# --- TOKEN ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN environment variable is not set!")

# --- URL saqlash uchun dict ---
USER_URLS = {}

# --- MENU ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("ℹ️ Bot haqida"), KeyboardButton("📞 Bog'lanish")],
            [KeyboardButton("🎓 Talabalar uchun qulaylik")]
        ],
        resize_keyboard=True
    )

BOT_ABOUT_TEXT = (
    "<b>📱 Instagram Video Bot</b>\n\n"
    "🎬 Reels, Post, Story — hammasini yuklab beraman!\n\n"
    "• 📹 Video yuklash\n"
    "• 💾 50 MB gacha fayl (Telegram limiti)\n\n"
    "👨‍💻 Muallif: <a href='https://t.me/Nazirov_Azamjon'>@Nazirov_Azamjon</a>"
)

# --- Umumiy caption ---
def get_caption():
    return (
        "✅ @vidgramuz_bot orqali yuklab olindi!\n\n"
        "✅ Bot foydali bo'lsa\n"
        "🤲 Ota-onamni va meni duo qiling\n\n"
        "🎓 Talabalar uchun qulaylik: "
        "<a href='https://t.me/talabauchunqulay'>@talabauchunqulay</a>"
    )

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "📸 Instagram link yuboring — men sizga <b>video</b> qilib yuboraman.",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# --- MENU HANDLER ---
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "📞 Bog'lanish":
        await update.message.reply_text(
            "📱 Aloqa: <a href='https://t.me/Nazirov_Azamjon'>@Nazirov_Azamjon</a>",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
    elif text == "ℹ️ Bot haqida":
        await update.message.reply_text(BOT_ABOUT_TEXT, parse_mode="HTML", reply_markup=get_main_menu())
    elif text == "🎓 Talabalar uchun qulaylik":
        await update.message.reply_text(
            "<b>🎓 Talabalar uchun qulaylik!</b>\n\n"
            "📄 Referat, kurs ishi, slayd va mustaqil ishlar\n"
            "💻 Android ilova, sayt, bot va boshqa dasturlar\n\n"
            "<b>📞 Buyurtma uchun:</b> <a href='https://t.me/talabauchunqulay'>@talabauchunqulay</a>\n\n"
            "<b>⚡ Tez, sifatli, arzon!</b>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=get_main_menu()
        )
    else:
        await handle_message(update, context)

# --- XABARLARNI QAYTA ISHLASH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    url = msg.text.strip()

    if "instagram.com" not in url:
        await msg.reply_text("📸 Instagram link yuboring.", reply_markup=get_main_menu())
        return

    user_id = msg.from_user.id
    vid = f"{user_id}_{msg.message_id}"
    USER_URLS[vid] = url

    keyboard = [
        [InlineKeyboardButton("🎬 Video yuklab olish", callback_data=f"video_{vid}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await msg.reply_text("⬇️ Video yuklab olinmoqda...", reply_markup=reply_markup)

# --- Direct URL olish (User-Agent bilan) ---
def get_instagram_url(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "*/*",
            "Referer": "https://www.instagram.com/",
        },
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"], info.get("title", "file")

# --- CALLBACK HANDLER ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data

    if action.startswith("video_"):
        vid = action.split("_", 1)[1]
        url = USER_URLS.get(vid)
        if not url:
            await q.message.reply_text("❌ Link topilmadi.")
            return

        progress_msg = await q.message.reply_text("⏳ Video tayyorlanmoqda...")

        try:
            vurl, title = get_instagram_url(url)
            await q.message.reply_video(
                vurl,
                caption=get_caption(),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"❌ Video yuborishda xato: {e}")
            try:
                ydl_opts = {"outtmpl": f"{vid}.mp4", "format": "best", "quiet": True, "no_warnings": True}
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_path = ydl.prepare_filename(info)
                with open(video_path, "rb") as f:
                    await q.message.reply_video(
                        f,
                        caption=get_caption(),
                        parse_mode="HTML"
                    )
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as fallback_error:
                await q.message.reply_text(f"❌ Video yuklab olib bo'lmadi: {str(fallback_error)[:100]}")

        await progress_msg.delete()

# --- BOTNI ISHGA TUSHIRISH ---
def main():
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=600.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ Bot ishga tushdi!")

    try:
        asyncio.run(app.run_polling(stop_signals=None))
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to'xtatildi.")
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")
        raise


if __name__ == "__main__":
    main()
