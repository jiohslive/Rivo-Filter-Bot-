import os
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
DATABASE_URI = os.getenv("DATABASE_URI")
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split()]
AUTH_CHANNEL = int(os.getenv("AUTH_CHANNEL"))
CHANNELS = [int(i) for i in os.getenv("CHANNELS", "").split()]
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB
mongo = MongoClient(DATABASE_URI)
db = mongo["vj_filter_bot"]

# Pyrogram client
app = Client("vj_filter_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# ----- Helper Functions -----
def is_admin(user_id):
    return user_id in ADMINS

def check_force_sub(user_id):
    try:
        member = app.get_chat_member(AUTH_CHANNEL, user_id)
        return member.status != "left"
    except:
        return False

# ----- Inline Buttons -----
SEASON_BUTTONS = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Season 6 - 480p", callback_data="season6_480")],
        [InlineKeyboardButton("Season 6 - 720p", callback_data="season6_720")],
        [InlineKeyboardButton("Season 6 - 1080p", callback_data="season6_1080")],
    ]
)

# ----- Command Handlers -----
@app.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    if not check_force_sub(user_id):
        await message.reply_text(
            "⚠️ You must join the auth channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{AUTH_CHANNEL}")]]
            ),
        )
        return
    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}, Welcome to the VJ Filter Bot!\n\nSelect season:",
        reply_markup=SEASON_BUTTONS,
    )

# ----- Callback Query Handlers -----
@app.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if not check_force_sub(user_id):
        await callback_query.answer("⚠️ Please join the auth channel first!", show_alert=True)
        return

    if data.startswith("season6"):
        quality = data.split("_")[1]
        # Fetch files from CHANNELS collection in DB (example)
        files = db["files"].find({"season": 6, "quality": quality})
        if files.count() == 0:
            await callback_query.message.edit_text("❌ No files found for this season/quality.")
            return

        text = f"📁 Season 6 - {quality}\n\nAvailable Episodes:\n"
        for f in files:
            text += f"Episode {f['episode']} - {f['title']}\n"
        await callback_query.message.edit_text(text)

# ----- Admin Panel -----
@app.on_message(filters.private & filters.user(ADMINS) & filters.command("admin"))
async def admin_panel(client, message):
    text = "🔧 Admin Panel\n\nFeatures:\n"
    text += "✅ Rename UI + AI Spell\n✅ Feature Toggles\n✅ Custom Stream\n"
    text += "Use commands to turn features On/Off."
    await message.reply_text(text)

# ----- PM Search -----
@app.on_message(filters.private & filters.command("search"))
async def pm_search(client, message):
    query = " ".join(message.text.split()[1:])
    if not query:
        await message.reply_text("Please provide a search query.")
        return
    results = db["files"].find({"title": {"$regex": query, "$options": "i"}})
    text = f"🔍 Search results for: {query}\n"
    for f in results:
        text += f"Episode {f['episode']} - {f['title']}\n"
    await message.reply_text(text or "No results found.")

# ----- Auto Approve Placeholder -----
@app.on_message(filters.channel)
async def auto_approve(client, message):
    # Example: auto approve logic here
    pass

# ----- Logging -----
@app.on_message(filters.all)
async def log_messages(client, message):
    try:
        await app.send_message(LOG_CHANNEL, f"📩 Message from {message.from_user.first_name} ({message.from_user.id})")
    except Exception as e:
        logger.error(e)

# ----- Run Bot -----
app.run()
