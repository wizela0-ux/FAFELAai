import os
import sqlite3
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
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

# 1. RENDER WEB SERVICE PORT BINDING FIX (Dummy HTTP Server)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FAF ELA AI Bot is Live and Healthy!")

    def log_message(self, format, *args):
        return  # Suppress default HTTP logging

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check HTTP server running on port {port}")
    server.serve_forever()

# Start HTTP server in a separate background thread
threading.Thread(target=run_health_server, daemon=True).start()

# 2. ENVIRONMENT VARIABLES
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
GEMINI_KEYS_RAW = os.getenv("GEMINI_KEYS", "")

# Parse 99 Gemini API Keys
API_KEYS = [key.strip() for key in GEMINI_KEYS_RAW.split(",") if key.strip()]
current_key_index = 0

def get_next_gemini_model(keys_list):
    """Rotates through 99 API keys dynamically on rate limits."""
    global current_key_index
    if not keys_list:
        raise ValueError("No Gemini API keys provided in GEMINI_KEYS environment variable.")
    
    key = keys_list[current_key_index]
    current_key_index = (current_key_index + 1) % len(keys_list)
    genai.configure(api_key=key)
    return genai.GenerativeModel('gemini-1.5-flash')

# 3. RAG DATABASE SEARCH (books.db)
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

# 4. SYSTEM PROMPT
SYSTEM_PROMPT = """
You are 'FAF ELA AI' (ፋፍ ኤላ ኤአይ), an elite educational assistant created for Ethiopian high school students (Grades 9-12).
Rules:
1. Always respond in the exact language used by the user (Amharic Ge'ez script, Latin/Fideliz Amharic, or English).
2. Use the provided textbook context from Ethiopian curriculum when available.
3. If context is missing, use your foundational internal knowledge smoothly without explicitly stating that data was missing.
4. Provide step-by-step clear explanations for mathematical, scientific, or complex questions.
5. Keep explanations warm, encouraging, concise, and structured with bullet points.
"""

# 5. TELEGRAM BOT HANDLERS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command with interactive main menu and Admin check."""
    user = update.effective_user
    user_id_str = str(user.id)
    
    keyboard = [
        [InlineKeyboardButton("📚 ክፍል እና ትምህርት ምረጥ (Select Subject)", callback_data="select_grade")],
        [InlineKeyboardButton("📝 ኪውዝ / ፈተናዎች (Take Quiz)", callback_data="start_quiz")],
        [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About FAF ELA AI)", callback_data="about_bot")]
    ]
    
    # Check if user is Admin
    if ADMIN_CHAT_ID and user_id_str == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("🛠 አድሚን ፓነል (Admin Panel)", callback_data="admin_panel")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"ሰላም {user.first_name}! 👋\n\n"
        f"እንኳን ወደ **FAF ELA AI** የትምህርት ረዳት ቦት በሰላም መጣህ/ሽ!\n"
        f"ከ 9ኛ እስከ 12ኛ ክፍል ያሉ ማንኛውንም ጥያቄዎች በጽሁፍ ወይም በፎቶ መጠየቅ ትችላለህ/ሽ።\n\n"
        f"ለመጀመር ከስር ካሉት አማራጮች አንዱን መረጥ፦"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline button interactions and submenu navigation."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id_str = str(query.from_user.id)
    
    if data == "main_menu":
        keyboard = [
            [InlineKeyboardButton("📚 ክፍል እና ትምህርት ምረጥ (Select Subject)", callback_data="select_grade")],
            [InlineKeyboardButton("📝 ኪውዝ / ፈተናዎች (Take Quiz)", callback_data="start_quiz")],
            [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About FAF ELA AI)", callback_data="about_bot")]
        ]
        if ADMIN_CHAT_ID and user_id_str == ADMIN_CHAT_ID:
            keyboard.append([InlineKeyboardButton("🛠 አድሚን ፓነል (Admin Panel)", callback_data="admin_panel")])
            
        await query.edit_message_text("ዋና ማውጫ፦", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "select_grade":
        keyboard = [
            [InlineKeyboardButton("Grade 9", callback_data="grade_9"), InlineKeyboardButton("Grade 10", callback_data="grade_10")],
            [InlineKeyboardButton("Grade 11", callback_data="grade_11"), InlineKeyboardButton("Grade 12", callback_data="grade_12")],
            [InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]
        ]
        await query.edit_message_text("እባክህ የምትማርበትን ክፍል ምረጥ፦", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("grade_"):
        selected_grade = data.split("_")[1]
        context.user_data['grade'] = selected_grade
        
        keyboard = [
            [InlineKeyboardButton("ICT", callback_data=f"sub_ICT"), InlineKeyboardButton("Physics", callback_data=f"sub_Physics")],
            [InlineKeyboardButton("Chemistry", callback_data=f"sub_Chemistry"), InlineKeyboardButton("Biology", callback_data=f"sub_Biology")],
            [InlineKeyboardButton("Maths", callback_data=f"sub_Maths"), InlineKeyboardButton("English", callback_data=f"sub_English")],
            [InlineKeyboardButton("🔙 ክፍል ቀይር", callback_data="select_grade")]
        ]
        await query.edit_message_text(f"የ Grade {selected_grade} ትምህርት ምረጥ፦", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("sub_"):
        subject = data.split("_")[1]
        grade = context.user_data.get('grade', '9-12')
        context.user_data['subject'] = subject
        
        keyboard = [[InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]]
        await query.edit_message_text(
            f"✅ **Grade {grade} - {subject}** ተመርጧል!\n\n"
            f"አሁን ማንኛውንም የትምህርቱን ጥያቄ በጽሁፍ ወይም በፎቶ መጠየቅ ትችላለህ።",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "start_quiz":
        keyboard = [[InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]]
        await query.edit_message_text(
            "📝 **የ ኪውዝ ክፍለ-ጊዜ**\n\n"
            "በቅርቡ የሚለቀቁ የ 9ኛ-12ኛ ክፍል ጥያቄዎች እዚህ ይዘጋጃሉ። አሁን ጥያቄ ካለህ በጽሁፍ ጠይቀኝ!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "about_bot":
        about_text = (
            "🤖 **FAF ELA AI Assistant**\n\n"
            "ይህ ቦት የኢትዮጵያን የ 9ኛ-12ኛ ክፍል ካሪኩለም መሰረት በማድረግ የተሰራ የኤአይ የትምህርት ረዳት ነው[span_0](start_span)[span_0](end_span)።\n"
            "ተማሪዎች በፈለጉት ቋንቋ ጥያቄዎችን በጽሁፍ ወይም በፎቶ ጠይቀው ፈጣን ማብራሪያ ማግኘት ይችላሉ።"
        )
        keyboard = [[InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]]
        await query.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_panel":
        if ADMIN_CHAT_ID and user_id_str == ADMIN_CHAT_ID:
            admin_text = (
                "🛠 **FAF ELA AI - አድሚን ዳሽቦርድ**\n\n"
                "እንኳን ደህና መጣህ አድሚን! እዚህ ቦታ ላይ የቦቱን እንቅስቃሴ እና የኪውዝ ክፍሎችን ማስተዳደር ትችላለህ።"
            )
            keyboard = [[InlineKeyboardButton("🔙 ዋና ማውጫ", callback_data="main_menu")]]
            await query.edit_message_text(admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text and photo queries with Gemini API key rotation."""
    user_text = update.message.text or update.message.caption or ""
    photo = update.message.photo
    selected_subject = context.user_data.get('subject', '')
    selected_grade = context.user_data.get('grade', '')
    
    status_msg = await update.message.reply_text("🤔 በማሰብ ላይ ነው... እባክህ ትንሽ ጠብቅ...")
    
    # Database search
    search_query = f"{selected_subject} {user_text}".strip()
    db_context = search_textbook_db(search_query) if user_text else ""
    
    prompt = f"{SYSTEM_PROMPT}\n\n"
    if selected_grade and selected_subject:
        prompt += f"Selected Context: Grade {selected_grade} {selected_subject}\n"
    if db_context:
        prompt += f"Textbook Reference:\n{db_context}\n\n"
    prompt += f"Student Query: {user_text}"
    
    image_data = None
    if photo:
        file = await context.bot.get_file(photo[-1].file_id)
        image_bytes = await file.download_as_bytearray()
        image_data = Image.open(io.BytesIO(image_bytes))

    # Execute request with 99 key rotation
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

# 6. MAIN EXECUTION
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    logger.info("FAF ELA AI Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
