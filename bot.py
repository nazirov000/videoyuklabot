import os
import re
import logging
import tempfile
import asyncio
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
import yt_dlp
from moviepy.editor import VideoFileClip

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- TOKEN ---
BOT_TOKEN = "7847943870:AAF3rm4iunNZ7NL0CcjKhW86DKjZ625bYWc"

# --- LIMITS ---
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB
TEMP_DIR = tempfile.mkdtemp()
USER_DATA = {}
FILE_PATHS = {}

# --- INSTAGRAM LINK TEKSHIRISH ---
def is_instagram_url(url):
    pattern = r"(https?://(?:www\.)?instagram\.com/[^ ]+)"
    return re.match(pattern, url) is not None

def get_video_id(url):
    clean = re.sub(r"[^\w]", "", url.split("/")[-1])
    return clean[:20]

# --- VIDEO MA'LUMOTLARINI OLISH ---
def get_video_info(video_path):
    try:
        clip = VideoFileClip(video_path)
        duration = int(clip.duration) if clip.duration else 0
        size = os.path.getsize(video_path)
        width, height = clip.size
        clip.close()
        return {
            "duration": duration,
            "size_mb": round(size / (1024*1024), 2),
            "resolution": f"{width}x{height}"
        }
    except Exception as e:
        logger.error(f"Video info olishda xato: {e}")
        return {"duration": 0, "size_mb": 0, "resolution": "Noma'lum"}

# --- INSTAGRAM VIDEO YUKLASH ---
def download_instagram_video(url, quality="720"):
    video_id = get_video_id(url)
    out_path = os.path.join(TEMP_DIR, f"{video_id}_{quality}.mp4")

    ydl_opts = {
        "outtmpl": out_path,
        "quiet": True,
        "format": f"best[height<={quality}]/best",
        "noplaylist": True,
        "merge_output_format": "mp4",
        "geo_bypass": True,
        "user_agent": "Mozilla/5.0",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        return out_path if os.path.exists(out_path) else None
    except Exception as e:
        logger.error(f"Instagram yuklashda xato: {e}")
        return None

# --- AUDIO AJRATISH ---
def extract_audio_from_file(video_path):
    try:
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            return None
        audio_path = os.path.splitext(video_path)[0] + ".mp3"
        clip.audio.write_audiofile(audio_path, codec="mp3", bitrate="192k", logger=None)
        clip.close()
        return audio_path
    except Exception as e:
        logger.error(f"Audio ajratishda xato: {e}")
        return None

# --- TUGMALAR ---
def get_delete_only_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("O‘chirish", callback_data=f"delete_{vid}")]
    ])

def get_video_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("MP3 yuklash", callback_data=f"mp3_{vid}")],
        [InlineKeyboardButton("O‘chirish", callback_data=f"delete_{vid}")]
    ])

# --- VIDEO YUBORISH ---
async def send_video_file(message, video_path, caption="", vid=None):
    size = os.path.getsize(video_path)
    if size > MAX_FILE_SIZE:
        await message.reply_text("Fayl juda katta (1 GB dan ortiq).")
        return False

    if vid:
        FILE_PATHS.setdefault(vid, {})["video"] = video_path

    caption_text = (
        f"{caption}\n\n"
        "`Bot foydali bo'lsa`\n\n"
        "*Ota-onamni va meni duo qiling*\n\n"
    )

    with open(video_path, "rb") as f:
        await message.reply_video(
            f,
            caption=caption_text,
            parse_mode="Markdown",
            reply_markup=get_video_keyboard(vid) if vid else None
        )
    return True

# --- AUDIO YUBORISH (faqat O‘chirish tugmasi) ---
async def send_audio_file(message, audio_path, caption="", vid=None):
    size = os.path.getsize(audio_path)
    if size > MAX_FILE_SIZE:
        await message.reply_text("Fayl juda katta.")
        return False

    if vid:
        FILE_PATHS.setdefault(vid, {})["audio"] = audio_path

    caption_text = (
        f"{caption}\n\n"
        "`Bot foydali bo'lsa`\n"
        "*Ota-onamni va meni duo qiling*\n\n"
    )

    with open(audio_path, "rb") as f:
        await message.reply_audio(
            f,
            caption=caption_text,
            parse_mode="Markdown",
            reply_markup=get_delete_only_keyboard(vid) if vid else None
        )
    return True

# --- MENU ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Bot haqida"), KeyboardButton("Bog‘lanish")]],
        resize_keyboard=True
    )

BOT_ABOUT_TEXT = (
    "*Instagram Video & MP3 Bot*\n\n"
    "Reels, Post, Story — hammasini yuklab beraman!\n\n"
    "• 360p / 480p / 720p video\n"
    "• Toza MP3 musiqa\n"
    "• 1 GB gacha fayl\n\n"
    "Muallif: [@Nazirov_Azamjon](https://t.me/Nazirov_Azamjon)"
)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum!\n\n"
        "Instagram link yuboring — men sizga **videoni va musiqasini** yuklab beraman!\n\n"
        "Reels | Post | Story | IGTV",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

# --- MENU HANDLER ---
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Bog‘lanish":
        await update.message.reply_text(
            "Aloqa: [@Nazirov_Azamjon](https://t.me/Nazirov_Azamjon)",
            parse_mode="Markdown",
            reply_markup=get_main_menu()
        )
    elif text == "Bot haqida":
        await update.message.reply_text(BOT_ABOUT_TEXT, parse_mode="Markdown", reply_markup=get_main_menu())
    else:
        await handle_message(update, context)

# --- YUKLANGAN VIDEO ISHLATISH ---
async def handle_uploaded_video(msg, context):
    user_id = msg.from_user.id
    vid = f"upl_{user_id}_{msg.message_id}"
    file = await msg.video.get_file()
    vpath = os.path.join(TEMP_DIR, f"{vid}.mp4")

    # 1. Darhol javob
    progress_msg = await msg.reply_text("Video qabul qilindi. Musiqa ajratilmoqda...")

    # 2. Yuklab olish
    await file.download_to_drive(vpath)

    # 3. Ma'lumotlar
    info = get_video_info(vpath)
    caption = (
        f"*Video ma'lumotlari:*\n"
        f"• Davomiylik: `{info['duration']}s`\n"
        f"• Hajmi: `{info['size_mb']} MB`\n"
        f"• O‘lchami: `{info['resolution']}`"
    )

    # 4. Videoni yuborish
    await send_video_file(msg, vpath, caption, vid)

    # 5. Progress animatsiya
    steps = ["Musiqa ajratilmoqda.", "Musiqa ajratilmoqda..", "Musiqa ajratilmoqda...", "MP3 tayyor!"]
    for step in steps:
        await asyncio.sleep(1.2)
        await progress_msg.edit_text(step)

    # 6. Audio ajratish
    apath = extract_audio_from_file(vpath)
    if apath:
        FILE_PATHS[vid] = {"video": vpath, "audio": apath}
        await send_audio_file(msg, apath, "MP3 tayyor!", vid)
    else:
        await progress_msg.edit_text("Bu videoda musiqa yo‘q.")
        if os.path.exists(vpath):
            os.remove(vpath)

    try:
        await progress_msg.delete()
    except:
        pass

# --- XABARLARNI QAYTA ISHLASH ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id

    # Instagram link
    if msg.text and is_instagram_url(msg.text.strip()):
        url = msg.text.strip()
        vid = get_video_id(url)
        USER_DATA.setdefault(user_id, {})[vid] = url

        keyboard = [
            [
                InlineKeyboardButton("360p", callback_data=f"v360_{vid}"),
                InlineKeyboardButton("480p", callback_data=f"v480_{vid}")
            ],
            [InlineKeyboardButton("720p", callback_data=f"v720_{vid}")],
            [InlineKeyboardButton("MP3", callback_data=f"audio_{vid}")]
        ]
        await msg.reply_text("Sifatni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Foydalanuvchi video yukladi
    if msg.video:
        await handle_uploaded_video(msg, context)
        return

    await msg.reply_text("Instagram link yuboring.", reply_markup=get_main_menu())

# --- CALLBACK HANDLER ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data

    try:
        action, vid = data.split("_", 1)
        paths = FILE_PATHS.get(vid, {})
        vpath = paths.get("video")
        apath = paths.get("audio")

        # --- MP3 yuklash (Progress bilan) ---
        if action == "mp3":
            progress_msg = await q.message.reply_text("Musiqa ajratilmoqda...")

            if apath and os.path.exists(apath):
                await send_audio_file(q.message, apath, "Saqlangan MP3", vid)
                await progress_msg.edit_text("MP3 tayyor!")
            elif vpath and os.path.exists(vpath):
                apath = extract_audio_from_file(vpath)
                if apath:
                    FILE_PATHS.setdefault(vid, {})["audio"] = apath
                    await send_audio_file(q.message, apath, "Yangi MP3", vid)
                    await progress_msg.edit_text("MP3 tayyor!")
                else:
                    await progress_msg.edit_text("Audio topilmadi.")
            else:
                await progress_msg.edit_text("Video topilmadi.")

            # progress xabarini bir oz ko'rsatib o'ldirish (asl video xabari o'chirilmaydi)
            await asyncio.sleep(2)
            try:
                await progress_msg.delete()
            except:
                pass

        # --- O‘chirish ---
        elif action == "delete":
            await q.message.delete()
            if vid in FILE_PATHS:
                for path in FILE_PATHS[vid].values():
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
                del FILE_PATHS[vid]
            if vid in USER_DATA.get(user_id, {}):
                del USER_DATA[user_id][vid]

        # --- Video sifati ---
        elif action.startswith("v"):
            quality = action[1:]
            url = USER_DATA.get(user_id, {}).get(vid)
            if not url:
                await q.edit_message_text("Link topilmadi.")
                return

            await q.edit_message_text(f"{quality}p yuklanmoqda...")
            vpath = download_instagram_video(url, quality)
            if vpath:
                FILE_PATHS[vid] = {"video": vpath}
                await send_video_file(q.message, vpath, "@Vidgramuzbot orqali yuklab olindi!", vid)
            else:
                await q.edit_message_text("Video yuklanmadi.")
            await q.message.delete()

        # --- MP3 tanlash ---
        elif action == "audio":
            url = USER_DATA.get(user_id, {}).get(vid)
            if not url:
                await q.edit_message_text("Link topilmadi.")
                return

            progress_msg = await q.edit_message_text("Musiqa ajratilmoqda...")
            vpath = download_instagram_video(url, "720")
            if not vpath:
                await progress_msg.edit_text("Video yuklanmadi.")
                return
            apath = extract_audio_from_file(vpath)
            if not apath:
                await progress_msg.edit_text("Audio topilmadi.")
                if os.path.exists(vpath):
                    os.remove(vpath)
                return

            FILE_PATHS[vid] = {"video": vpath, "audio": apath}
            await send_audio_file(q.message, apath, "MP3 tayyor!", vid)
            await progress_msg.delete()
            await q.message.delete()

    except Exception as e:
        logger.error(f"Callback xatosi: {e}")
        try:
            await q.edit_message_text("Xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.")
        except:
            pass

# --- BOTNI ISHGA TUSHIRISH ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Bot ishga tushdi | @Vidgramuzbot")
    app.run_polling()

if __name__ == "__main__":
    main()