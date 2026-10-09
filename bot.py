import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai
from PIL import Image
import io

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 1. ENVIRONMENT VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
GEMINI_KEYS_RAW = os.getenv("GEMINI_KEYS", "")

# Parse 99 Gemini API Keys
API_KEYS = [key.strip() for key in GEMINI_KEYS_RAW.split(",") if key.strip()]
current_key_index = 0

def get_next_gemini_model(keys_list):
    """Rotates through 99 API keys dynamically on rate limits (Error 429)."""
    global current_key_index
    if not keys_list:
        raise ValueError("No Gemini API keys provided in GEMINI_KEYS environment variable.")
    
    key = keys_list[current_key_index]
    current_key_index = (current_key_index + 1) % len(keys_list)
    genai.configure(api_key=key)
    return genai.GenerativeModel('gemini-1.5-flash')

# 2. RAG DATABASE SEARCH (books.db)
DB_PATH = "books.db"

def search_textbook_db(query, limit=3):
    """Searches textbook_data table for relevant content."""
    if not os.path.exists(DB_PATH):
        return ""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT book_name, page_number, content FROM textbook_data WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        )
        results = cursor.fetchall()
        conn.close()
        
        context_text = ""
        for book, page, content in results:
            context_text += f"\n--- [{book} - Page {page}] ---\n{content}\n"
        return context_text
    except Exception as e:
        logger.error(f"Database search error: {e}")
        return ""

# 3. SYSTEM PROMPT
SYSTEM_PROMPT = """
You are 'FAF ELA AI' (ፋፍ ኤላ ኤአይ), an elite educational assistant created for Ethiopian high school students (Grades 9-12).
Rules:
1. Always respond in the exact language used by the user (Amharic Ge'ez script, Latin/Fideliz Amharic, or English).
2. Use the provided textbook context from Ethiopian curriculum when available.
3. If context is missing, use your foundational internal knowledge smoothly without explicitly stating that data was missing.
4. Provide step-by-step clear explanations for mathematical, scientific, or complex questions.
5. Keep explanations warm, encouraging, concise, and structured with bullet points.
"""

# 4. TELEGRAM BOT HANDLERS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command with interactive main menu."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📚 ክፍል እና ትምህርት ምረጥ (Select Subject)", callback_data="select_grade")],
        [InlineKeyboardButton("📝 ኪውዝ / ፈተናዎች (Take Quiz)", callback_data="start_quiz")],
        [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About FAF ELA AI)", callback_data="about_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"ሰላም {user.first_name}! 👋\n\n"
        f"እንኳን ወደ **FAF ELA AI** የትምህርት ረዳት ቦት በሰላም መጣህ/ሽ!\n"
        f"ከ 9ኛ እስከ 12ኛ ክፍል ያሉ ማንኛውንም ጥያቄዎች በጽሁፍ ወይም በፎቶ መጠየቅ ትችላለህ/ሽ።\n\n"
        f"ለመጀመር ከስር ካሉት አማራጮች አንዱን መረጥ፦"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline button interactions."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "select_grade":
        keyboard = [
            [InlineKeyboardButton("Grade 9", callback_data="g9"), InlineKeyboardButton("Grade 10", callback_data="g10")],
            [InlineKeyboardButton("Grade 11", callback_data="g11"), InlineKeyboardButton("Grade 12", callback_data="g12")],
            [InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]
        ]
        await query.edit_message_text("እባክህ የምትማርበትን ክፍል ምረጥ፦", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif query.data == "about_bot":
        about_text = (
            "🤖 **FAF ELA AI Assistant**\n\n"
            "ይህ ቦት የኢትዮጵያን የ 9ኛ-12ኛ ክፍል አዲሱን እና የቆየውን ካሪኩለም መሰረት በማድረግ የተሰራ የኤአይ የትምህርት ረዳት ነው[span_5](start_span)[span_5](end_span)።\n"
            "ማንኛውንም ጥያቄ በጽሁፍ፣ በፎቶ ወይም በድምጽ መጠየቅ ትችላለህ!"
        )
        keyboard = [[InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]]
        await query.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif query.data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📚 ክፍል እና ትምህርት ምረጥ (Select Subject)", callback_data="select_grade")],
            [InlineKeyboardButton("📝 ኪውዝ / ፈተናዎች (Take Quiz)", callback_data="start_quiz")],
            [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About FAF ELA AI)", callback_data="about_bot")]
        ]
        await query.edit_message_text("ዋና ማውጫ፦", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles student text and photo queries with Gemini API failover rotation."""
    user_text = update.message.text or update.message.caption or ""
    photo = update.message.photo
    
    status_msg = await update.message.reply_text("🤔 በማሰብ ላይ ነው... እባክህ ትንሽ ጠብቅ...")
    
    # Extract Context from books.db
    db_context = search_textbook_db(user_text) if user_text else ""
    
    prompt = f"{SYSTEM_PROMPT}\n\n"
    if db_context:
        prompt += f"Use this textbook context if relevant:\n{db_context}\n\n"
    prompt += f"Student Query: {user_text}"
    
    # Process image if uploaded
    image_data = None
    if photo:
        file = await context.bot.get_file(photo[-1].file_id)
        image_bytes = await file.download_as_bytearray()
        image_data = Image.open(io.BytesIO(image_bytes))

    # Execute Gemini API call with 99-key rotation fallback
    success = False
    attempts = 0
    max_attempts = len(API_KEYS) if API_KEYS else 1
    
    while not success and attempts < max_attempts:
        try:
            model = get_next_gemini_model(API_KEYS)
            if image_data:
                response = model.generate_content([prompt, image_data])
            else:
                response = model.generate_content(prompt)
            
            await status_msg.edit_text(response.text)
            success = True
        except Exception as e:
            logger.warning(f"Gemini API Key failed (Attempt {attempts + 1}): {e}")
            attempts += 1
            
    if not success:
        await status_msg.edit_text("❌ ይቅርታ፣ በአሁኑ ሰዓት መልስ መስጠት አልተቻለም። እባክህ ትንሽ ቆይተህ ድጋሚ ሞክር።")

# 5. MAIN EXECUTION
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing! Please set it in Render Environment Variables.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    logger.info("FAF ELA AI Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
