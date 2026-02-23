import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient
from dotenv import load_dotenv
import openai
import datetime

# -----------------------
# Load Environment
# -----------------------
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
DATABASE_URI = os.environ.get("DATABASE_URI")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ADMINS = list(map(int, os.environ.get("ADMINS", "").split()))
CHANNELS = list(map(int, os.environ.get("CHANNELS", "").split()))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))
AUTH_CHANNEL = int(os.environ.get("AUTH_CHANNEL"))
FORCE_SUB = int(os.environ.get("FORCE_SUB"))

# -----------------------
# MongoDB Setup
# -----------------------
client = MongoClient(DATABASE_URI)
db = client['rio_bot']

# Feature toggles default
if db.features.count_documents({}) == 0:
    db.features.insert_one({
        "premium": True,
        "ai_spell": True,
        "rename": True,
        "stream": True,
        "auto_approve": True,
        "pm_search": True,
        "custom_stream": True,
    })

# -----------------------
# OpenAI Setup
# -----------------------
openai.api_key = OPENAI_API_KEY

# -----------------------
# Initialize Bot
# -----------------------
bot = Client(
    "rio_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# -----------------------
# Admin Check
# -----------------------
def is_admin(user_id):
    return user_id in ADMINS

# -----------------------
# Helper: Log Events
# -----------------------
async def log_event(text):
    try:
        await bot.send_message(LOG_CHANNEL, text)
    except:
        print("Failed to log event:", text)

# -----------------------
# Start / Force Sub
# -----------------------
@bot.on_message(filters.private & filters.command("start"))
async def start_msg(client, message):
    user_id = message.from_user.id
    # Force subscribe check
    try:
        await bot.get_chat_member(FORCE_SUB, user_id)
    except:
        await message.reply_text(
            f"Please join our channel first: https://t.me/{FORCE_SUB}"
        )
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Search 🔍", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("Season 6 🎬", callback_data="season_6")],
        [InlineKeyboardButton("Help ❓", callback_data="help")]
    ])
    await message.reply_text("Welcome to Rio Bot – Big Boss Marathi Season 6! 🔥", reply_markup=keyboard)
    await log_event(f"User {user_id} started the bot.")

# -----------------------
# Help Panel
# -----------------------
@bot.on_callback_query(filters.regex("help"))
async def help_panel(_, query):
    await query.answer()
    text = (
        "Help Panel:\n"
        "- /rename : Rename file\n"
        "- /season : Select Season/Quality\n"
        "- Search files inline\n"
        "- Premium features available"
    )
    await query.message.edit_text(text)

# -----------------------
# Rename UI
# -----------------------
@bot.on_message(filters.private & filters.command("rename"))
async def rename_ui(client, message):
    if not db.features.find_one({})["rename"]:
        return await message.reply_text("Rename feature is turned off.")
    await message.reply_text("Send me the new name for your file:")

# -----------------------
# AI Spell Check
# -----------------------
@bot.on_message(filters.private & filters.text)
async def ai_spell_check(client, message):
    if not db.features.find_one({})["ai_spell"]:
        return
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":message.text}]
        )
        corrected = response.choices[0].message.content
        await message.reply_text(f"AI Spell Check:\n{corrected}")
    except Exception as e:
        print("OpenAI Error:", e)

# -----------------------
# Season 6 & Quality Inline
# -----------------------
@bot.on_message(filters.private & filters.command("season"))
async def season_quality(client, message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Season 6 ✅", callback_data="season_6")],
        [
            InlineKeyboardButton("480p", callback_data="quality_480p"),
            InlineKeyboardButton("720p", callback_data="quality_720p"),
            InlineKeyboardButton("1080p", callback_data="quality_1080p")
        ]
    ])
    await message.reply_text("Select Season 6 and Quality:", reply_markup=keyboard)

@bot.on_callback_query()
async def cb_handler(_, query):
    data = query.data
    if data.startswith("season_6"):
        await query.answer("You selected Big Boss Marathi Season 6")
    elif data.startswith("quality_"):
        await query.answer(f"Quality set to {data.replace('quality_', '').upper()}")

# -----------------------
# PM Search Feature
# -----------------------
@bot.on_message(filters.private & filters.command("search"))
async def pm_search(client, message):
    if not db.features.find_one({})["pm_search"]:
        return await message.reply_text("PM Search feature is turned off.")
    text = message.text.replace("/search ", "")
    await message.reply_text(f"Searching for: {text}\n(Only Season 6)")
    # Simulate search
    await asyncio.sleep(1)
    await message.reply_text(f"Results for '{text}' in Season 6:\n1. Episode 1\n2. Episode 2\n3. Episode 3 ...")

# -----------------------
# Auto Approve / Premium Toggle
# -----------------------
@bot.on_message(filters.private & filters.command("premium"))
async def premium_toggle(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("You are not admin.")
    feature = db.features.find_one({})
    db.features.update_one({}, {"$set":{"premium": not feature["premium"]}})
    await message.reply_text(f"Premium toggled to {not feature['premium']}")

@bot.on_message(filters.private & filters.command("autoapprove"))
async def auto_approve_toggle(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply_text("You are not admin.")
    feature = db.features.find_one({})
    db.features.update_one({}, {"$set":{"auto_approve": not feature["auto_approve"]}})
    await message.reply_text(f"Auto Approve toggled to {not feature['auto_approve']}")

# -----------------------
# Stream Feature Example
# -----------------------
@bot.on_message(filters.private & filters.command("stream"))
async def stream_feature(client, message):
    if not db.features.find_one({})["stream"]:
        return await message.reply_text("Stream feature is turned off.")
    await message.reply_text("Streaming Big Boss Marathi Season 6...")
    # Simulate multiple player support
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Player 1", callback_data="player1")],
        [InlineKeyboardButton("Player 2", callback_data="player2")]
    ])
    await message.reply_text("Choose Player:", reply_markup=keyboard)

# -----------------------
# Run the Bot
# -----------------------
print(f"[{datetime.datetime.now()}] Rio Bot – Season 6 Full Features is running...")
bot.run()
