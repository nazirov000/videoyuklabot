import asyncio
import os
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "7906977951:AAE7Z1T5CeUlbRf9si1-PxIPrR1QREbvq-M")

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
    "<b>📱 Instagram Video & MP3 Bot</b>\n\n"
    "🎬 Reels, Post, Story — hammasini yuklab beraman!\n\n"
    "• 📹 Video yuklash\n"
    "• 🎵 Minimal hajmli MP3 musiqa\n"
    "• 💾 50 MB gacha fayl (Telegram limiti)\n\n"
    "👨‍💻 Muallif: <a href='https://t.me/Nazirov_Azamjon'>@Nazirov_Azamjon</a>"
)

# --- Tugmalar ---
def get_video_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 MP3 yuklash", callback_data=f"mp3_{vid}")],
        [InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete_{vid}")]
    ])

def get_delete_only_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete_{vid}")]
    ])

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
        "📸 Instagram link yuboring — men sizga <b>video yoki MP3</b> qilib yuboraman.",
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
        [InlineKeyboardButton("🎬 Video", callback_data=f"video_{vid}")],
        [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3_{vid}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await msg.reply_text("⬇️ Yuklab olish turini tanlang:", reply_markup=reply_markup)

# --- AUDIO AJRATISH ---
def extract_audio_from_file(video_path):
    try:
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            return None
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
        clip.audio.write_audiofile(audio_path, codec="mp3", bitrate="64k", logger=None, verbose=False)
        clip.close()
        return audio_path
    except Exception as e:
        print(f"❌ Audio ajratishda xato: {e}")
        return None

# --- Direct URL olish (User-Agent bilan) ---
def get_instagram_url(url, audio_only=False):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best" if audio_only else "best",
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
            vurl, title = get_instagram_url(url, audio_only=False)
            await q.message.reply_video(
                vurl,
                caption=get_caption(),
                reply_markup=get_video_keyboard(vid),
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
                        reply_markup=get_video_keyboard(vid),
                        parse_mode="HTML"
                    )
                if os.path.exists(video_path):
                    os.remove(video_path)
            except Exception as fallback_error:
                await q.message.reply_text(f"❌ Video yuklab olib bo'lmadi: {str(fallback_error)[:100]}")

        await progress_msg.delete()

    elif action.startswith("mp3_"):
        vid = action.split("_", 1)[1]
        url = USER_URLS.get(vid)
        if not url:
            await q.message.reply_text("❌ Link topilmadi.")
            return

        progress_msg = await q.message.reply_text("⏳ MP3 tayyorlanmoqda...")

        try:
            ydl_opts = {"outtmpl": f"{vid}.mp4", "format": "best", "quiet": True, "no_warnings": True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)

            audio_path = extract_audio_from_file(video_path)
            if audio_path:
                with open(audio_path, "rb") as f:
                    await q.message.reply_audio(
                        f,
                        caption=get_caption(),
                        reply_markup=get_delete_only_keyboard(vid),
                        parse_mode="HTML"
                    )
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            else:
                await q.message.reply_text("❌ Audio ajratib bo'lmadi.")

            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            await q.message.reply_text(f"❌ MP3 tayyorlanishda xato: {str(e)[:100]}")

        await progress_msg.delete()

    elif action.startswith("delete_"):
        await q.message.delete()
        vid = action.split("_", 1)[1]
        if vid in USER_URLS:
            del USER_URLS[vid]

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


if __name__ == "__main__":
    main()
