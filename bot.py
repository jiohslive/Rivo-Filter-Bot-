import os
import logging
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
AUTH_CHANNEL_ID = int(os.getenv("AUTH_CHANNEL_ID"))  # Numeric
AUTH_CHANNEL_USERNAME = os.getenv("AUTH_CHANNEL_USERNAME")  # @username
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

# ------------------ /start Command ------------------
@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id

    joined = await check_force_sub(user_id)
    if not joined:
        await message.reply_text(
            "⚠️ You must join the auth channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{AUTH_CHANNEL_USERNAME}")]]
            ),
        )
        return

    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}, Welcome!\n\nSelect season:",
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

    # Dynamic season & quality fetch
    if data.startswith("season"):
        parts = data.split("_")
        season = int(parts[0].replace("season", ""))
        quality = parts[1]

        files = list(db["files"].find({
            "season": season,
            "quality": {"$regex": quality, "$options": "i"}
        }))

        if not files:
            await callback_query.message.edit_text("❌ No files found for this season/quality.")
            return

        text = f"📁 Season {season} - {quality}\n\nAvailable Episodes:\n"
        for f in files:
            ep_num = f.get("episode", "-")
            title = f.get("title", "-")
            text += f"Episode {ep_num}: {title}\n"
        await callback_query.message.edit_text(text)

# ------------------ /search Command ------------------
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
        ep_num = f.get("episode", "-")
        title = f.get("title", "-")
        text += f"Episode {ep_num}: {title}\n"
    await message.reply_text(text)

# ------------------ Admin Panel ------------------
@app.on_message(filters.private & filters.user(ADMINS) & filters.command("admin"))
async def admin_panel(client, message):
    text = "🔧 Admin Panel\n\nFeatures:\n"
    text += "✅ Rename UI + AI Spell\n✅ Feature Toggles\n✅ Custom Stream\n"
    text += "Use commands to turn features On/Off."
    await message.reply_text(text)

# ------------------ Log All Messages ------------------
@app.on_message(filters.all)
async def log_messages(client, message):
    try:
        user_name = message.from_user.first_name if message.from_user else "Unknown"
        user_id = message.from_user.id if message.from_user else "N/A"
        msg_text = message.text or message.caption or "No Text"
        await app.send_message(
            LOG_CHANNEL,
            f"📩 Message from {user_name} ({user_id})\nText: {msg_text}"
        )
    except Exception as e:
        logger.error(f"LOG ERROR: {e}")

# ------------------ Run Bot ------------------
if __name__ == "__main__":
    logger.info("🚀 Bot is starting...")
    app.run()
