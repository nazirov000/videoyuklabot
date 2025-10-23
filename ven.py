import os
import re
from io import BytesIO
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

BOT_TOKEN = "8453982051:AAGsRUdNwI6g4wES4yzAeNN6_QoAnNX5k7k"
USER_URLS = {}

# --- Instagram URL ni ddinstagram bilan o‘zgartirish ---
def convert_to_ddinstagram(url: str) -> str:
    return url.replace("https://www.instagram.com", "https://ddinstagram.com").replace("https://instagram.com", "https://ddinstagram.com")

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

def get_video_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 MP3 yuklash", callback_data=f"mp3_{vid}")],
        [InlineKeyboardButton("🗑️ O‘chirish", callback_data=f"delete_{vid}")]
    ])

def get_delete_only_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ O‘chirish", callback_data=f"delete_{vid}")]
    ])

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

    url = convert_to_ddinstagram(url)
    user_id = msg.from_user.id
    vid = f"{user_id}_{msg.message_id}"
    USER_URLS[vid] = url

    keyboard = [
        [InlineKeyboardButton("🎬 Video", callback_data=f"video_{vid}")],
        [InlineKeyboardButton("🎵 MP3", callback_data=f"mp3_{vid}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await msg.reply_text("⬇️ Yuklab olish turini tanlang:", reply_markup=reply_markup)

# --- VIDEO YUKLASH (RAMga) ---
def download_video_to_bytes(url: str, vid: str) -> BytesIO:
    ydl_opts = {
        "outtmpl": f"{vid}.mp4",
        "format": "best",
        "quiet": True,
        "no_warnings": True
    }
    buffer = BytesIO()
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
        with open(video_path, "rb") as f:
            buffer.write(f.read())
        os.remove(video_path)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"❌ Yuklab olishda xato: {e}")
        return None

# --- MP3 AJRATISH (vaqtincha fayl bilan) ---
def extract_mp3_temp(video_bytes: BytesIO, vid: str) -> BytesIO:
    temp_video = f"{vid}.mp4"
    temp_audio = f"{vid}.mp3"

    with open(temp_video, "wb") as f:
        f.write(video_bytes.read())

    os.system(f"ffmpeg -i {temp_video} -vn -ar 44100 -ac 2 -b:a 64k {temp_audio} -y")

    mp3_bytes = BytesIO()
    with open(temp_audio, "rb") as f:
        mp3_bytes.write(f.read())

    os.remove(temp_video)
    os.remove(temp_audio)

    mp3_bytes.seek(0)
    return mp3_bytes

# --- CALLBACK HANDLER ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data
    vid = action.split("_", 1)[1]
    url = USER_URLS.get(vid)

    if not url:
        await q.message.reply_text("❌ Link topilmadi.")
        return

    await q.message.reply_text("⏳ Yuklanmoqda...")

    video_bytes = download_video_to_bytes(url, vid)
    if not video_bytes:
        await q.message.reply_text("❌ Yuklab bo‘lmadi.")
        return

    if action.startswith("video_"):
        await q.message.reply_video(video_bytes, caption=get_caption(), reply_markup=get_video_keyboard(vid), parse_mode="HTML")
    elif action.startswith("mp3_"):
        mp3_bytes = extract_mp3_temp(video_bytes, vid)
        await q.message.reply_audio(mp3_bytes, caption=get_caption(), reply_markup=get_delete_only_keyboard(vid), parse_mode="HTML")
    elif action.startswith("delete_"):
        await q.message.delete()
        USER_URLS.pop(vid, None)

# --- BOTNI ISHGA TUSHIRISH ---
def main():
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=600.0)
    app = Application.builder().token(BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
