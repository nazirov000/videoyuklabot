import os
import re
import logging
import tempfile
import asyncio
import json
from pathlib import Path
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
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
BOT_TOKEN = "7906977951:AAE7Z1T5CeUlbRf9si1-PxIPrR1QREbvq-M"

# --- LIMITS & PATHS ---
MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB
TEMP_DIR = tempfile.mkdtemp()
COOKIES_DIR = "cookies"
USERS_FILE = "users.json"
Path(COOKIES_DIR).mkdir(exist_ok=True)

USER_DATA = {}
FILE_PATHS = {}

# --- USERS JSON ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

USERS = load_users()

# --- INSTAGRAM LINK TEKSHIRISH ---
def is_instagram_url(url):
    pattern = r"(https?://(?:www\.)?instagram\.com/(?:reel|p|stories)/[^ ?]+)"
    return re.match(pattern, url.strip()) is not None

def get_video_id(url):
    clean = re.sub(r"[^\w]", "", url.split("/")[-1].split("?")[0])
    return clean[:20]

# --- VIDEO INFO ---
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
        logger.error(f"Video info xatosi: {e}")
        return {"duration": 0, "size_mb": 0, "resolution": "Noma'lum"}

# --- COOKIE YARATISH ---
def create_instagram_cookie(username, password, cookie_path):
    try:
        ydl_opts = {
            "quiet": True,
            "cookiefile": cookie_path,
            "username": username,
            "password": password,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(["https://www.instagram.com/"])
        return os.path.exists(cookie_path) and os.path.getsize(cookie_path) > 100
    except Exception as e:
        logger.error(f"Cookie yaratishda xato: {e}")
        return False

# --- VIDEO YUKLASH ---
def download_instagram_video(url, quality="720", user_id=None):
    video_id = get_video_id(url)
    out_path = os.path.join(TEMP_DIR, f"{video_id}_{quality}.mp4")

    ydl_opts = {
        "outtmpl": out_path,
        "quiet": True,
        "format": f"best[height<={quality}]/best",
        "noplaylist": True,
        "merge_output_format": "mp4",
        "geo_bypass": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "retries": 3,
    }

    # Foydalanuvchi cookie si
    if user_id and str(user_id) in USERS:
        cookie_file = USERS[str(user_id)]["cookie_file"]
        if os.path.exists(cookie_file):
            ydl_opts["cookiefile"] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
        return out_path if os.path.exists(out_path) else None
    except Exception as e:
        logger.error(f"Yuklash xatosi: {e}")
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
    return InlineKeyboardMarkup([[InlineKeyboardButton("O'chirish", callback_data=f"delete_{vid}")]])

def get_video_keyboard(vid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("MP3 yuklash", callback_data=f"mp3_{vid}")],
        [InlineKeyboardButton("O'chirish", callback_data=f"delete_{vid}")]
    ])

# --- YUBORISH ---
async def send_video_file(message, video_path, caption="", vid=None):
    size = os.path.getsize(video_path)
    if size > MAX_FILE_SIZE:
        await message.reply_text("Fayl juda katta (1 GB+).")
        return False

    if vid:
        FILE_PATHS.setdefault(vid, {})["video"] = video_path

    caption_text = f"{caption}\n\n`Bot foydali bo'lsa`\n\n*Ota-onamni duo qiling*"

    with open(video_path, "rb") as f:
        await message.reply_video(f, caption=caption_text, parse_mode="Markdown", reply_markup=get_video_keyboard(vid) if vid else None)
    return True

async def send_audio_file(message, audio_path, caption="", vid=None):
    size = os.path.getsize(audio_path)
    if size > MAX_FILE_SIZE:
        await message.reply_text("Fayl juda katta.")
        return False

    if vid:
        FILE_PATHS.setdefault(vid, {})["audio"] = audio_path

    caption_text = f"{caption}\n\n`Bot foydali bo'lsa`\n\n*Ota-onamni duo qiling*"

    with open(audio_path, "rb") as f:
        await message.reply_audio(f, caption=caption_text, parse_mode="Markdown", reply_markup=get_delete_only_keyboard(vid) if vid else None)
    return True

# --- MENU ---
def get_main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Bot haqida"), KeyboardButton("Bog'lanish")],
        [KeyboardButton("Talabalar uchun")]
    ], resize_keyboard=True)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    login_status = "Kirish yo'q | /login"
    if user_id in USERS and USERS[user_id].get("logged_in"):
        login_status = f"Kirish: {USERS[user_id]['username']}"

    reklama = (
        "\n\n*Talabalar uchun!*\n\n"
        "Referat, kurs ishi, Android ilova, bot va boshqalar\n"
        "*Buyurtma:* [@talabauchunqulay](https://t.me/talabauchunqulay)"
    )

    await update.message.reply_text(
        f"Assalomu alaykum!\n\n"
        f"{login_status}\n\n"
        "Instagram link yuboring — video va MP3 yuklab beraman!\n\n"
        "Reels | Post | Story" + reklama,
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# --- /login ---
async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Instagram login ma'lumotlaringizni yuboring:\n\n"
        "`username:password`\n\n"
        "Masalan: `ali_2000:123456`",
        parse_mode="Markdown"
    )
    context.user_data["awaiting_login"] = True

# --- /logout ---
async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id in USERS:
        cookie_file = USERS[user_id]["cookie_file"]
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        del USERS[user_id]
        save_users(USERS)
        await update.message.reply_text("Chiqib ketildi!")
    else:
        await update.message.reply_text("Siz hali kirmagansiz.")

# --- MENU HANDLER ---
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "Bog'lanish":
        await update.message.reply_text("Aloqa: [@Nazirov_Azamjon](https://t.me/Nazirov_Azamjon)", parse_mode="Markdown", reply_markup=get_main_menu())
    elif text == "Bot haqida":
        await update.message.reply_text(
            "*Instagram Video & MP3 Bot*\n\n"
            "Reels, Post, Story — hammasini yuklayman!\n\n"
            "• 360p / 480p / 720p video\n"
            "• Toza MP3\n"
            "• 1 GB gacha\n\n"
            "Muallif: [@Nazirov_Azamjon](https://t.me/Nazirov_Azamjon)",
            parse_mode="Markdown", reply_markup=get_main_menu()
        )
    elif text == "Talabalar uchun":
        await update.message.reply_text(
            "*Talabalar uchun!*\n\n"
            "Referat, kurs ishi, slayd\n"
            "Android, sayt, bot dasturlash\n\n"
            "*Buyurtma:* [@talabauchunqulay](https://t.me/talabauchunqulay)",
            parse_mode="Markdown", reply_markup=get_main_menu()
        )
    else:
        await handle_message(update, context)

# --- YUKLANGAN VIDEO ---
async def handle_uploaded_video(msg, context):
    user_id = msg.from_user.id
    vid = f"upl_{user_id}_{msg.message_id}"
    file = await msg.video.get_file()
    vpath = os.path.join(TEMP_DIR, f"{vid}.mp4")

    progress_msg = await msg.reply_text("Video qabul qilindi. MP3 ajratilmoqda...")

    await file.download_to_drive(vpath)

    info = get_video_info(vpath)
    caption = f"*Video:*\n• {info['duration']}s\n• {info['size_mb']} MB\n• {info['resolution']}"
    await send_video_file(msg, vpath, caption, vid)

    for step in ["Musiqa ajratilmoqda.", "Musiqa ajratilmoqda..", "Musiqa ajratilmoqda...", "MP3 tayyor!"]:
        await asyncio.sleep(1.2)
        await progress_msg.edit_text(step)

    apath = extract_audio_from_file(vpath)
    if apath:
        FILE_PATHS[vid] = {"video": vpath, "audio": apath}
        await send_audio_file(msg, apath, "MP3 tayyor!", vid)
    else:
        await progress_msg.edit_text("Videoda musiqa yo'q.")
        if os.path.exists(vpath):
            os.remove(vpath)

    try:
        await progress_msg.delete()
    except:
        pass

# --- XABARLAR ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = msg.from_user.id
    user_str = str(user_id)

    # Login kutish
    if context.user_data.get("awaiting_login"):
        text = msg.text.strip()
        if ":" not in text:
            await msg.reply_text("Noto'g'ri format. `username:password`")
            return
        username, password = text.split(":", 1)
        cookie_path = os.path.join(COOKIES_DIR, f"user_{user_id}.txt")

        progress = await msg.reply_text("Kirish amalga oshirilmoqda...")
        if create_instagram_cookie(username, password, cookie_path):
            USERS[user_str] = {
                "username": username,
                "password": password,
                "cookie_file": cookie_path,
                "logged_in": True
            }
            save_users(USERS)
            await progress.edit_text("Muvaffaqiyatli kirish! Endi video yuklay olasiz.")
        else:
            await progress.edit_text("Login yoki parol noto'g'ri.")
        context.user_data["awaiting_login"] = False
        return

    # Instagram link
    if msg.text and is_instagram_url(msg.text):
        if user_str not in USERS:
            await msg.reply_text("Avval /login buyrug'i bilan kiring.")
            return

        url = msg.text.strip()
        vid = get_video_id(url)
        USER_DATA.setdefault(user_id, {})[vid] = url

        keyboard = [
            [InlineKeyboardButton("360p", callback_data=f"v360_{vid}"),
             InlineKeyboardButton("480p", callback_data=f"v480_{vid}"),
             InlineKeyboardButton("720p", callback_data=f"v720_{vid}")],
            [InlineKeyboardButton("MP3", callback_data=f"audio_{vid}")]
        ]
        await msg.reply_text("Sifatni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if msg.video:
        await handle_uploaded_video(msg, context)
        return

    await msg.reply_text("Instagram link yuboring yoki /login buyrug'ini bosing.", reply_markup=get_main_menu())

# --- CALLBACK ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    user_str = str(user_id)
    data = q.data

    try:
        action, vid = data.split("_", 1)
        paths = FILE_PATHS.get(vid, {})
        vpath = paths.get("video")
        apath = paths.get("audio")

        # MP3
        if action == "mp3":
            progress_msg = await q.message.reply_text("MP3 ajratilmoqda...")
            if apath and os.path.exists(apath):
                await send_audio_file(q.message, apath, "Saqlangan MP3", vid)
            elif vpath and os.path.exists(vpath):
                apath = extract_audio_from_file(vpath)
                if apath:
                    FILE_PATHS[vid]["audio"] = apath
                    await send_audio_file(q.message, apath, "Yangi MP3", vid)
                else:
                    await progress_msg.edit_text("Audio topilmadi.")
            else:
                await progress_msg.edit_text("Video topilmadi.")
            await asyncio.sleep(2)
            try:
                await progress_msg.delete()
            except:
                pass

        # O'chirish
        elif action == "delete":
            await q.message.delete()
            if vid in FILE_PATHS:
                for p in FILE_PATHS[vid].values():
                    if p and os.path.exists(p):
                        os.remove(p)
                del FILE_PATHS[vid]
            if vid in USER_DATA.get(user_id, {}):
                del USER_DATA[user_id][vid]

        # Video sifati
        elif action.startswith("v"):
            quality = action[1:]
            url = USER_DATA.get(user_id, {}).get(vid)
            if not url:
                await q.edit_message_text("Link topilmadi.")
                return
            await q.edit_message_text(f"{quality}p yuklanmoqda...")
            vpath = download_instagram_video(url, quality, user_id)
            if vpath:
                FILE_PATHS[vid] = {"video": vpath}
                await send_video_file(q.message, vpath, "@vidgramuz_bot orqali yuklandi!", vid)
            else:
                await q.edit_message_text("Video yuklanmadi. Private bo'lsa — login tekshiring.")
            await q.message.delete()

        # MP3 tanlash
        elif action == "audio":
            url = USER_DATA.get(user_id, {}).get(vid)
            if not url:
                await q.edit_message_text("Link topilmadi.")
                return
            progress_msg = await q.edit_message_text("MP3 tayyorlanmoqda...")
            vpath = download_instagram_video(url, "720", user_id)
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
            await q.edit_message_text("Xatolik yuz berdi.")
        except:
            pass
# --- MAIN ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login_command))
    app.add_handler(CommandHandler("logout", logout_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))
    app.add_handler(MessageHandler(filters.VIDEO, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("🤖 Bot ishga tushdi | @Vidgramuz_bot")
    app.run_polling()

if __name__ == "__main__":
    main()