import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

# 1. Environment Variables ን ማንበብ
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN በ Render Environment Variables ውስጥ አልተገኘም!")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY በ Render Environment Variables ውስጥ አልተገኘም!")

# 2. Bot, Dispatcher እና Gemini Client ማዘጋጀት
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# AIው እንደ ኢትዮጵያ ሁለተኛ ደረጃ መምህር ሆኖ እንዲመልስ የተሰጠ መመሪያ
SYSTEM_INSTRUCTION = (
    "እርስዎ የኢትዮጵያ የሁለተኛ ደረጃ ትምህርት ቤት (High School) ጎበዝ እና ታጋሽ መምህር ነዎት። "
    "ተማሪዎች በፊዚክስ፣ ባዮሎጂ፣ ኬሚስትሪ፣ ማቲማቲክስ እና በሌሎች ትምህርቶች የሚያነሱትን ጥያቄ "
    "በግልጽ፣ በአጭሩ እና ለመረዳት በሚያመች መልኩ ያስረዱ። "
    "መልስዎን በአማርኛ እና በሚያስፈልጉ ቦታዎች ላይ የእንግሊዝኛ የትምህርት ቃላትን በመጠቀም አብራሩ።"
)

# 3. Render 'No open ports' ኤረር እንዳያመጣ የሚያደርግ Health Check Web Server
async def handle_ping(request):
    return web.Response(text="FAFELAai Bot is awake & running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# 4. /start ኮማንድ
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 ሰላም <b>{message.from_user.first_name}</b>!\n\n"
        "እኔ የትምህርት እና የጥናት ረዳት AI ነኝ። 🎓\n"
        "ማንኛውንም የትምህርት ጥያቄ በጽሁፍ መጻፍ ወይም የጥያቄውን ፎቶ ለክተው መጠየቅ ይችላሉ!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])
    await message.answer(welcome_text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    menu_text = "🎓 <b>የጥናት ረዳት AI</b>\n\nጥያቄዎን በጽሁፍ ይጻፉ ወይም የጥያቄውን ፎቶ ያያይዙልኝ፦"
    await callback.message.edit_text(menu_text, parse_mode="HTML")
    await callback.answer()

# 5. የጽሁፍ ጥያቄዎችን አስተናጋጅ (Text Query Handler)
@dp.message(F.text)
async def handle_text_query(message: types.Message):
    thinking_msg = await message.answer("🤔 <i>ጥያቄዎትን እያሰብኩበት ነው... እባክዎ ትንሽ ይጠብቁ...</i>", parse_mode="HTML")
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config={'system_instruction': SYSTEM_INSTRUCTION}
        )
        
        answer_text = response.text if response.text else "ይቅርታ፣ ለዚህ ጥያቄ መልስ ማፍለቅ አልቻልኩም።"
        await thinking_msg.edit_text(answer_text)

    except Exception as e:
        await thinking_msg.edit_text(f"❌ <b>ስህተት ተፈጥሯል:</b>\n<code>{e}</code>", parse_mode="HTML")

# 6. የፎቶ ጥያቄዎችን አስተናጋጅ (Image Query Handler)
@dp.message(F.photo)
async def handle_photo_query(message: types.Message):
    thinking_msg = await message.answer("🔍 <i>የላኩትን ፎቶ እያነበብኩ ነው... እባክዎ ትንሽ ይጠብቁ...</i>", parse_mode="HTML")
    
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_bytes = downloaded_file.read()

        prompt = message.caption if message.caption else "እባክዎን በዚህ ፎቶ ላይ ያለውን የትምህርት ጥያቄ በዝርዝር አብራርተው መልሱልኝ።"

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                genai.types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                prompt
            ],
            config={'system_instruction': SYSTEM_INSTRUCTION}
        )

        answer_text = response.text if response.text else "ይቅርታ፣ በፎቶው ላይ ያለውን ጥያቄ ማነብ አልቻልኩም።"
        await thinking_msg.edit_text(answer_text)

    except Exception as e:
        await thinking_msg.edit_text(f"❌ <b>ስህተት ተፈጥሯል:</b>\n<code>{e}</code>", parse_mode="HTML")

# 7. ቦቱን እና ዌብ ሰርቨሩን አብሮ ማስነሳት
async def main():
    print("🤖 የ AI ጥናት ረዳት ቦት እና ዌብ ሰርቨር ስራ ጀምረዋል...")
    await asyncio.gather(start_web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
