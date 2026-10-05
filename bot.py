import os
import sqlite3
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 1. Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8411023752:AAFJGMStLQLM3CySiOCbcMxb7oU91rGwbhk"

# 3. Groq API Key (ከ console.groq.com ያወጣኸውን gsk_... ቁልፍ እዚህ አስገባ)
GROQ_API_KEY = "YOUR_GROQ_API_KEY_HERE"

def call_groq_api(prompt):
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            logging.error(f"Groq API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Request Error: {e}")
        return None

def search_books_db(query):
    if not os.path.exists('books.db'):
        return None
    try:
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()
        
        # ዳታቤዝ ውስጥ በቀጥታ መፈለግ
        sql_query = "SELECT content FROM textbook_data WHERE LOWER(content) LIKE LOWER(?) LIMIT 1"
        cursor.execute(sql_query, ('%' + query + '%',))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
    except Exception as e:
        logging.error(f"Database Search Error: {e}")
    return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **እንኳን ወደ FAF ELA AI ቦት በሰላም መጡ!**\n\n"
        "ከ9ኛ - 12ኛ ክፍል ባሉት ትምህርቶች ላይ የተዘጋጀ የ AI ረዳት ነው።\n"
        "እባክዎን ክፍሎትን ይምረጡ፦"
    )
    keyboard = [
        [InlineKeyboardButton("9ኛ ክፍል", callback_data='grade_9'), InlineKeyboardButton("10ኛ ክፍል", callback_data='grade_10')],
        [InlineKeyboardButton("11ኛ ክፍል", callback_data='grade_11'), InlineKeyboardButton("12ኛ ክፍል", callback_data='grade_12')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=constants.ParseMode.MARKDOWN)

async def grade_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    selected_grade = query.data.split('_')[1]
    context.user_data['grade'] = selected_grade
    
    msg = f"✅ **{selected_grade}ኛ ክፍል ተመርጧል።**\nአሁን ጥያቄዎን በጽሑፍ መላክ ይችላሉ።"
    await query.edit_message_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    user_grade = context.user_data.get('grade', '9')
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    status_msg = await update.message.reply_text("🔍 በመፈለግ ላይ...")

    response_text = None

    # 1. መጀመሪያ በ SQLite ዳታቤዝ ውስጥ መፈለግ
    db_result = search_books_db(user_text)
    if db_result:
        response_text = f"📚 **ከመጽሐፉ የተገኘ መልስ፦**\n\n{db_result}"

    # 2. ዳታቤዝ ላይ ካላገኘ በ Groq AI መፈለግ
    if not response_text:
        prompt = (
            f"You are FAF ELA AI, an educational assistant for Ethiopian high school students (Grade {user_grade}).\n"
            f"User Question: {user_text}\n\n"
            "Instructions:\n"
            "- Answer accurately based on high school level content.\n"
            "- If asked in Amharic, respond in Amharic. If in English, respond in English."
        )
        response_text = call_groq_api(prompt)

    # 3. በሁለቱም ካላገኘ
    if not response_text:
        response_text = "ይቅርታ፣ ጥያቄውን መመለስ አልተቻለም። እባክዎን ጥያቄዎን አስተካክለው ይጻፉ።"

    await status_msg.delete()
    await update.message.reply_text(response_text)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CallbackQueryHandler(grade_selection_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("🤖 FAF ELA AI Bot is running successfully...")
    app.run_polling()

if __name__ == '__main__':
    main()
