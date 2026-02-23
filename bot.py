import asyncio
import re
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from pymongo import MongoClient

# ================== CONFIG ==================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
DATABASE_URI = os.environ.get("DATABASE_URI")
ADMINS = list(map(int, os.environ.get("ADMINS").split()))

app = Client("RioRenameBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

mongo = MongoClient(DATABASE_URI)
db = mongo["RioBot"]
settings_db = db["settings"]
rename_db = db["rename"]

# ================== DEFAULT SETTINGS ==================

DEFAULT_SETTINGS = {
    "_id": "main",
    "rename": True,
    "pm_search": True,
    "auto_delete": True,
    "premium": False,
    "refer": False,
    "token": False
}

async def get_settings():
    data = settings_db.find_one({"_id": "main"})
    if not data:
        settings_db.insert_one(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    return data

# ================== AI SPELL ==================

def smart_spell(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    corrections = {
        "movvie": "movie",
        "filim": "film",
        "hindhi": "hindi",
        "tamill": "tamil",
        "telgu": "telugu",
        "englsih": "english",
        "seasson": "season",
        "episod": "episode"
    }
    words = text.split()
    fixed = [corrections.get(word, word) for word in words]
    return " ".join(fixed)

# ================== START ==================

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 Welcome To Rio Advanced Rename Bot\n\nSend Any File To Rename."
    )

# ================== RENAME SYSTEM ==================

@app.on_message(filters.document & filters.private)
async def rename_handler(client, message):

    settings = await get_settings()
    if not settings.get("rename"):
        return

    file = message.document
    user_id = message.from_user.id

    rename_db.update_one(
        {"_id": user_id},
        {"$set": {"file_id": file.file_id, "file_name": file.file_name}},
        upsert=True
    )

    await message.reply(
        f"📂 Current File Name:\n{file.file_name}\n\nSend New Name Without Extension:",
        reply_markup=ForceReply(selective=True)
    )

@app.on_message(filters.reply & filters.private)
async def rename_process(client, message):

    data = rename_db.find_one({"_id": message.from_user.id})
    if not data:
        return

    new_name = message.text.strip()
    old_name = data["file_name"]
    ext = old_name.split(".")[-1]
    final_name = f"{new_name}.{ext}"

    sent = await message.reply_document(
        data["file_id"],
        file_name=final_name,
        caption=f"✅ Renamed To: {final_name}"
    )

    settings = await get_settings()
    if settings.get("auto_delete"):
        await asyncio.sleep(60)
        await sent.delete()

    rename_db.delete_one({"_id": message.from_user.id})

# ================== FEATURE TOGGLE ==================

@app.on_message(filters.command("settings") & filters.user(ADMINS))
async def settings_panel(client, message):

    settings = await get_settings()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Rename: {'ON' if settings['rename'] else 'OFF'}",
                callback_data="toggle_rename"
            )
        ],
        [
            InlineKeyboardButton(
                f"Auto Delete: {'ON' if settings['auto_delete'] else 'OFF'}",
                callback_data="toggle_delete"
            )
        ]
    ])

    await message.reply("⚙️ Bot Settings:", reply_markup=keyboard)

@app.on_callback_query()
async def callbacks(client, callback):

    settings = await get_settings()

    if callback.data == "toggle_rename":
        settings_db.update_one(
            {"_id": "main"},
            {"$set": {"rename": not settings["rename"]}}
        )

    elif callback.data == "toggle_delete":
        settings_db.update_one(
            {"_id": "main"},
            {"$set": {"auto_delete": not settings["auto_delete"]}}
        )

    await callback.answer("Updated")
    await callback.message.delete()

# ================== RUN ==================

print("🔥 Rio Advanced Bot Running...")
app.run()
