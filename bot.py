import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ================= CONFIG =================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
DATABASE_URI = os.environ.get("DATABASE_URI")
ADMINS = list(map(int, os.environ.get("ADMINS").split()))
CHANNELS = os.environ.get("CHANNELS")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))
FORCE_SUB = os.environ.get("FORCE_SUB")

# ================ DATABASE =================

mongo = AsyncIOMotorClient(DATABASE_URI)
db = mongo["RIO_BOT"]
settings = db.settings

DEFAULT_FEATURES = {
    "rename": True,
    "spell": True,
    "pm_search": False,
    "auto_delete": False,
    "stream": False,
    "season_quality": True
}

async def get_features():
    data = await settings.find_one({"_id": "features"})
    if not data:
        await settings.insert_one({"_id": "features", **DEFAULT_FEATURES})
        return DEFAULT_FEATURES
    return data

# ================ BOT ======================

app = Client(
    "RIO-BOT",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ================ FORCE SUB =================

async def force_sub_check(client, user_id):
    if not FORCE_SUB:
        return True
    try:
        await client.get_chat_member(FORCE_SUB, user_id)
        return True
    except:
        return False

# ================ START =====================

@app.on_message(filters.command("start"))
async def start(client, message):
    ok = await force_sub_check(client, message.from_user.id)
    if not ok:
        return await message.reply(
            f"Join {FORCE_SUB} first.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB.replace('@','')}")]]
            )
        )
    await message.reply("Welcome to Rio Commercial Bot 🚀")

# ================ ADMIN PANEL ===============

@app.on_message(filters.command("panel") & filters.user(ADMINS))
async def panel(client, message):
    feat = await get_features()
    text = "⚙ Feature Status:\n\n"
    for k,v in feat.items():
        text += f"{k} : {'ON' if v else 'OFF'}\n"
    await message.reply(text)

@app.on_message(filters.command("feature") & filters.user(ADMINS))
async def toggle_feature(client, message):
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Usage: /feature season_quality on")

    feature = parts[1]
    state = parts[2].lower()

    data = await get_features()
    if feature not in data:
        return await message.reply("Invalid feature")

    data[feature] = True if state == "on" else False
    await settings.update_one({"_id": "features"}, {"$set": data})
    await message.reply(f"{feature} turned {state}")

# ================ AI SPELL ==================

def ai_spell(text):
    corrections = {
        "movi": "movie",
        "filim": "film",
        "hollywod": "hollywood"
    }
    for wrong, right in corrections.items():
        text = re.sub(wrong, right, text, flags=re.IGNORECASE)
    return text

# ================ SEARCH WITH SEASON/QUALITY ===============

@app.on_message(filters.text & filters.private)
async def search_handler(client, message):
    feat = await get_features()

    if not feat["season_quality"]:
        return

    query = message.text

    if feat["spell"]:
        query = ai_spell(query)

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Season 1", callback_data=f"season|1|{query}"),
            InlineKeyboardButton("Season 2", callback_data=f"season|2|{query}")
        ],
        [
            InlineKeyboardButton("480p", callback_data=f"quality|480p|{query}"),
            InlineKeyboardButton("720p", callback_data=f"quality|720p|{query}")
        ],
        [
            InlineKeyboardButton("1080p", callback_data=f"quality|1080p|{query}")
        ]
    ])

    await message.reply(f"Select Season / Quality for:\n{query}", reply_markup=buttons)

@app.on_callback_query(filters.regex("season|quality"))
async def season_quality_callback(client, callback_query):
    data = callback_query.data.split("|")
    type_ = data[0]
    value = data[1]
    query = data[2]

    await callback_query.message.reply(
        f"Searching {query}\nSelected {type_}: {value}\n\n(Connect your database search logic here)"
    )

# ================ RENAME ====================

@app.on_message(filters.document)
async def rename_handler(client, message):
    feat = await get_features()
    if not feat["rename"]:
        return

    file = message.document
    file_name = file.file_name

    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Rename Now", callback_data=f"rename|{file.file_id}")]]
    )
    await message.reply(f"File: {file_name}", reply_markup=buttons)

@app.on_callback_query(filters.regex("^rename"))
async def rename_callback(client, callback_query):
    await callback_query.message.reply("Send new filename.")

# ================ AUTO DELETE ===============

@app.on_message(filters.private & filters.document)
async def auto_delete(client, message):
    feat = await get_features()
    if feat["auto_delete"]:
        await asyncio.sleep(60)
        await message.delete()

# ================ LOGGING ===================

@app.on_message(filters.all)
async def logger(client, message):
    if LOG_CHANNEL:
        try:
            await message.forward(LOG_CHANNEL)
        except:
            pass

# ================ RUN =======================

print("Rio Commercial Bot With Season/Quality Started 🚀")
app.run()
