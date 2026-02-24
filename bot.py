import os
import logging
import re
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# ------------------ Load Env ------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
DATABASE_URI = os.getenv("DATABASE_URI")
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split()]
AUTH_CHANNEL_ID = int(os.getenv("AUTH_CHANNEL_ID"))
AUTH_CHANNEL_USERNAME = os.getenv("AUTH_CHANNEL_USERNAME")
CHANNELS = [int(i) for i in os.getenv("CHANNELS", "").split()]
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ------------------ Logging ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ MongoDB ------------------
mongo = MongoClient(DATABASE_URI)
db = mongo["vj_filter_bot"]

# ------------------ Pyrogram Client ------------------
app = Client("vj_filter_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ------------------ Helper Functions ------------------
def is_admin(user_id):
    return user_id in ADMINS

async def check_force_sub(user_id):
    try:
        member = await app.get_chat_member(AUTH_CHANNEL_ID, user_id)
        return member.status != "left"
    except Exception as e:
        logger.warning(f"Force sub check failed: {e}")
        return False

# ------------------ Inline Buttons ------------------
SEASON_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Season 6 - 480p", callback_data="season6_480p")],
        [InlineKeyboardButton("Season 6 - 720p", callback_data="season6_720p")],
        [InlineKeyboardButton("Season 6 - 1080p", callback_data="season6_1080p")],
    ]
)

# ------------------ Start Command ------------------
@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    logger.info(f"/start called by {user_id}")

    if not await check_force_sub(user_id):
        await message.reply_text(
            "⚠️ You must join the auth channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{AUTH_CHANNEL_USERNAME}")]]
            ),
        )
        return

    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}, Welcome to the VJ Filter Bot!\n\nSelect season:",
        reply_markup=SEASON_BUTTONS,
    )

# ------------------ Callback Query ------------------
@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if not await check_force_sub(user_id):
        await callback_query.answer("⚠️ Please join the auth channel first!", show_alert=True)
        return

    if data.startswith("season6"):
        quality = data.split("_")[1]  # "480p", "720p", "1080p"
        files = list(db["files"].find({"season": 6, "quality": {"$regex": quality, "$options": "i"}}))
        if not files:
            await callback_query.message.edit_text("❌ No files found for this season/quality.")
            return

        text = f"📁 Season 6 - {quality}\n\nAvailable Episodes:\n"
        for f in files:
            text += f"Episode {f.get('episode', '-')}: {f.get('title', '-')}\n"
        await callback_query.message.edit_text(text)

# ------------------ Admin Panel ------------------
@app.on_message(filters.private & filters.user(ADMINS) & filters.command("admin"))
async def admin_panel(client, message):
    text = "🔧 Admin Panel\n\nFeatures:\n"
    text += "✅ Rename UI + AI Spell\n✅ Feature Toggles\n✅ Custom Stream\n"
    text += "Use commands to turn features On/Off."
    await message.reply_text(text)

# ------------------ PM Search ------------------
@app.on_message(filters.private & filters.command("search"))
async def pm_search(client, message):
    query = " ".join(message.text.split()[1:])
    if not query:
        await message.reply_text("Please provide a search query.")
        return

    results = list(db["files"].find({"title": {"$regex": query, "$options": "i"}}))
    if not results:
        await message.reply_text("❌ No results found.")
        return

    text = f"🔍 Search results for: {query}\n"
    for f in results:
        text += f"Episode {f.get('episode', '-')}: {f.get('title', '-')}\n"
    await message.reply_text(text)

# ------------------ Auto Save Episodes from Channel ------------------
@app.on_message(filters.channel & filters.video)
async def save_channel_video(client, message):
    try:
        if message.chat.id not in CHANNELS:
            return

        title = message.video.file_name or "Unknown Title"
        file_id = message.video.file_id

        # ---------------- Pattern Handling ----------------
        # S06E44 or Daily Episodes like "Bigg Boss S06E44 Day 43 The Power Key Twist 480p JHS WEB DL"
        pattern = r"S(\d+)E(\d+).*?(\d{3,4}p)"
        match = re.search(pattern, title, re.IGNORECASE)

        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
            quality = match.group(3)
        else:
            # If pattern not found, save as daily episode with season 6 default
            season = 6
            episode = 0
            quality_search = re.search(r"(\d{3,4}p)", title)
            quality = quality_search.group(1) if quality_search else "Unknown"

        existing = db["files"].find_one({"chat_id": message.chat.id, "file_id": file_id})
        if existing:
            return

        db["files"].insert_one({
            "chat_id": message.chat.id,
            "season": season,
            "episode": episode,
            "title": title,
            "quality": quality,
            "file_id": file_id,
            "date": message.date
        })

        logger.info(f"Saved video: S{season}E{episode} - {title}")

        # ---------------- Log Channel Notification ----------------
        try:
            await app.send_message(
                LOG_CHANNEL,
                f"✅ Saved episode: S{season}E{episode} - {title} ({quality})"
            )
        except Exception as e:
            logger.error(f"LOG ERROR: {e}")

    except Exception as e:
        logger.error(f"ERROR saving channel video: {e}")

# ------------------ Logging All Messages ------------------
@app.on_message(filters.all)
async def log_messages(client, message):
    try:
        user_name = message.from_user.first_name if message.from_user else "Unknown"
        user_id = message.from_user.id if message.from_user else "N/A"
        await app.send_message(
            LOG_CHANNEL,
            f"📩 Message from {user_name} ({user_id})\nText: {message.text or 'No Text'}"
        )
    except Exception as e:
        logger.error(f"LOG ERROR: {e}")

# ------------------ Run Bot ------------------
if __name__ == "__main__":
    logger.info("🚀 Bot is starting...")
    app.run()
