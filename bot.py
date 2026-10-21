import os
import asyncio
import aiohttp
import html
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").rstrip('/')
SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 🗄 FIREBASE HELPER FUNCTIONS
# ==========================================
async def fb_get(path: str):
    if not FIREBASE_DB_URL:
        return None
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
    return None

async def fb_put(path: str, data):
    if not FIREBASE_DB_URL:
        return
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        await session.put(url, json=data)

async def fb_post(path: str, data):
    if not FIREBASE_DB_URL:
        return None
    url = f"{FIREBASE_DB_URL}/{path}.json"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as resp:
            if resp.status == 200:
                res = await resp.json()
                return res.get("name")
    return None

async def save_user(user_id: int, username: str, first_name: str, lang: str = "am"):
    user_data = {
        "username": username or "",
        "first_name": first_name or "",
        "language": lang
    }
    await fb_put(f"users/{user_id}", user_data)

async def get_user_language(user_id: int) -> str:
    user = await fb_get(f"users/{user_id}")
    if user and isinstance(user, dict):
        return user.get("language", "am")
    return "am"

# ==========================================
# 📝 FSM STATES
# ==========================================
class UserState(StatesGroup):
    waiting_for_language = State()

# ==========================================
# 🌐 LANGUAGE KEYBOARDS & UI HELPERS
# ==========================================
def get_language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇪🇹 አማርኛ", callback_data="lang_am"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])

def get_main_menu_keyboard(lang: str = "am"):
    if lang == "en":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Take Quiz", callback_data="quiz_menu")],
            [InlineKeyboardButton(text="📊 Student Result", callback_data="result_menu")],
            [
                InlineKeyboardButton(text="ℹ️ About Us", callback_data="about_us"),
                InlineKeyboardButton(text="☎️ Support", callback_data="support")
            ]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ኪዝ ይስሩ (Quiz)", callback_data="quiz_menu")],
            [InlineKeyboardButton(text="📊 ውጤት ማያ (Result)", callback_data="result_menu")],
            [
                InlineKeyboardButton(text="ℹ️ ስለ እኛ (About)", callback_data="about_us"),
                InlineKeyboardButton(text="☎️ ድጋፍ (Support)", callback_data="support")
            ]
        ])

# ==========================================
# 🚀 COMMAND HANDLERS
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        f"👋 Welcome <b>{html.escape(message.from_user.first_name)}</b>!\n"
        "እንኳን ወደ ትምህርታዊ ቦት በደህና መጡ! 🇪🇹\n\n"
        "Please select your language | እባክዎ ቋንቋ ይምረጡ፦"
    )
    await state.set_state(UserState.waiting_for_language)
    await message.answer(welcome_text, reply_markup=get_language_keyboard(), parse_mode="HTML")

@dp.callback_query(UserState.waiting_for_language, F.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    selected_lang = "am" if callback.data == "lang_am" else "en"
    user = callback.from_user
    
    await save_user(user.id, user.username, user.first_name, selected_lang)
    await state.clear()
    
    if selected_lang == "en":
        text = (
            f"👋 Hello <b>{html.escape(user.first_name)}</b>!\n\n"
            "Welcome to the Educational High School Bot.\n"
            "Choose an option below to get started:"
        )
    else:
        text = (
            f"👋 ሰላም <b>{html.escape(user.first_name)}</b>!\n\n"
            "እንኳን ወደ ሁለተኛ ደረጃ ትምህርት ቤት ቦት በደህና መጡ።\n"
            "ለመጀመር ከታች ካሉት አማራጮች አንዱን ይምረጡ፦"
        )
        
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(selected_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_language(callback.from_user.id)
    
    if lang == "en":
        text = "🏠 <b>Main Menu</b>\n\nChoose an option below:"
    else:
        text = "🏠 <b>ዋና ማውጫ (Main Menu)</b>\n\nከታች ካሉት አማራጮች ይምረጡ፦"
        
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(lang), parse_mode="HTML")
    await callback.answer()

# Placeholder Callbacks for upcoming modules
@dp.callback_query(F.data == "about_us")
async def show_about_us(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu" if lang == "en" else "🏠 ዋና ማውጫ", callback_data="main_menu")]])
    
    if lang == "en":
        text = "ℹ️ <b>About Us</b>\n\nThis educational Telegram bot helps Ethiopian high school students practice quizzes and view their examination results efficiently."
    else:
        text = "ℹ️ <b>ስለ እኛ</b>\n\nይህ የትምህርት ቦት የኢትዮጵያ ሁለተኛ ደረጃ ተማሪዎች የትምህርት ጥያቄዎችን እንዲለማመዱ እና የፈተና ውጤታቸውን በቀላሉ እንዲያዩ የተዘጋጀ ነው።"
        
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu" if lang == "en" else "🏠 ዋና ማውጫ", callback_data="main_menu")]])
    
    if lang == "en":
        text = "☎️ <b>Support</b>\n\nIf you have any questions or issues, please contact your school administrator or teacher."
    else:
        text = "☎️ <b>ድጋፍ</b>\n\nማንኛውም ጥያቄ ወይም አስተያየት ካለዎት እባክዎ የትምህርት ቤቱን አድሚን ወይም መምህሩን ያናግሩ።"
        
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🔄 WEB SERVER FOR 24/7 HOSTING
# ==========================================
async def handle_ping(request):
    return web.Response(text="Edu Bot is awake & running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    print("ትምህርታዊ ቦቱ ስራ ጀምሯል...")
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
