import os
import re
import sqlite3
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 1. Logging Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 2. Telegram Bot Token
TELEGRAM_BOT_TOKEN = "8411023752:AAFJGMStLQLM3CySiOCbcMxb7oU91rGwbhk"

# 3. 99 Gemini API Keys List
GEMINI_API_KEYS = [
    "AQ.Ab8RN6JWpbUdI4tfJKwpv6fPpSSvKb9KaJcMRjf8VC5fcs7YVg",
    "AQ.Ab8RN6L_g9N4Gkoo_xODqFZZbNuHQAOXayy_8Ca6X6LmxSWfQA",
    "AQ.Ab8RN6IFHxCWm6fo6kGq3kyYd26K0cQdX1VLlL6Esx2EOM4DBg",
    "AQ.Ab8RN6KmvnaXNkf0ZgfPCip8AtRqSg04DuUnHJIEXvYtUojZxA",
    "AQ.Ab8RN6Jkt3LZO_yIEGMZVmJtTn7lT5CTQGwBo3W7SO9CCSJIhQ",
    "AQ.Ab8RN6LNswcWQgc7LW2mIdBNipbnxoyDMUPC2udapcicXsZfBw",
    "AQ.Ab8RN6IcAsJ4ntr1GRcazxhOCtHYuGXD6O8gwj10ZeECDIly4A",
    "AQ.Ab8RN6Ja1N7ZTUqhe9exn33LJkWahxgVOtAvEcOpRst-drxDIA",
    "AQ.Ab8RN6KhAbWf-uqdpTW8C29mjrgDQFfk1_LXnHEsjvLGSghDsg",
    "AQ.Ab8RN6K1z3NtSHuWo2Ustov6mPJYSwKcwWwT0h0iGot5T6BZ4w",
    "AQ.Ab8RN6KYozU8jyBWuYuCXK7vrexHHR4e2IrbaLprJLC5W4s2bw",
    "AQ.Ab8RN6IVXu6H7HHmrsXu9Tuigz33Nw7aD097Kvnm1BrXTc7SAQ",
    "AQ.Ab8RN6J34_nKnbk7cYq3aG2DbHFuOKSwy1Xjtdeucr-piBpYhw",
    "AQ.Ab8RN6LXYF1HE_-Z-OR4aNaHVEOmutlta0Bnx3VbD4cedzLKcQ",
    "AQ.Ab8RN6J7Y21aBq8RZTCkmHkx5yA6nLzPVBxvSzTXJAyVvviA-A",
    "AQ.Ab8RN6JsJYSD2VjAsQgO4ESxYWChWLHB8Ac9c6FOih-JXZTXEQ",
    "AQ.Ab8RN6LGFwHuRUb4G-QRk8cVheDLVboLUjlMDy5pFKD_VGsgxw",
    "AQ.Ab8RN6Kze-r8LliCDBHCiHMl9Bk16g6UG22IWSifLmC-eAg8mg",
    "AQ.Ab8RN6LGL3zqWwcYpPFBJciDUqa-Ps0_t4v7aT8nG450cojIIw",
    "AQ.Ab8RN6IjwL6ibOQDoMLdWUu0opjwr66L16p7EnbZolnablLlow",
    "AQ.Ab8RN6Km-D3CEBRHh9IFvESannemrPifDBrWqI1xA1wQvoW8Kw",
    "AQ.Ab8RN6IiB036aEQFNyfRxOCkDs-BIHWy6UNQWwmnI201TSgRmA",
    "AQ.Ab8RN6IGui8IhiCpCW8SNKBVIwJSb-QmyCwoYpJfLBzf6WYSzQ",
    "AQ.Ab8RN6J1y8C1-55XVsPm61CpZP2cNmAaoZet5ulFxQiO1uiXSw",
    "AQ.Ab8RN6Jo1zjcjY7Pnk71eV4qwul6dYw8NrveH6HDDsQ9lYYd1w",
    "AQ.Ab8RN6LWSF6jvnHxX-rCW1z1TdSDTYWpx6BpVOrxYwUnJRFSew",
    "AQ.Ab8RN6IBCAIF-5Juxy6ptO2wBn1lZi5h5sTQYoGXXS83VsuQOQ",
    "AQ.Ab8RN6I1-AjTD0MPxKxcOG9ajDXM4Yp5zsRbLjMe-O6s3o2lLQ",
    "AQ.Ab8RN6L8i4r6wnfJd2_a62dQsSKd4UX5-XVWAXpogOpwVTqm4A",
    "AQ.Ab8RN6I1UKVSmwH8SetG62KdQYV93vj-rmacOO8WC6kq9Q5sDg",
    "AQ.Ab8RN6Kx8_EOLVSXtpS-p9zPrw1wZOOcmIzKmeOpit5LCvHDIg",
    "AQ.Ab8RN6IEtGJcTYsWk6v9P809f8IZvO98OCUhmvXRvGkRgYGNsA",
    "AQ.Ab8RN6LHkpbF4piLmZh_DwQVCfZiXnJepaf8jt_V-hsraD6W9g",
    "AQ.Ab8RN6KJB4GNpETYJgfyAJwqpYx2KRrosfLqvGEOg0c2THI7ZQ",
    "AQ.Ab8RN6Lle3O8SwrpUjpAYI7G6fG1QS58Q1OspW5N6JS0KxlxeA",
    "AQ.Ab8RN6K92DFmY3qeZn3jtn7l2c9WH19-TzAbd6r-8cvY6DDxsg",
    "AQ.Ab8RN6LNBnoAj1AHIf2EDMitM1fT20-sdkUNCZq-9Ftz8cR9lA",
    "AQ.Ab8RN6I13ziQcPBrdT4ez18TvNM688-kKf6k2V-GnXomh-CZqQ",
    "AQ.Ab8RN6I_zLsqGBhnH3TBhrRvBQ75vlIyOR5JobeQleYuFLTdWA",
    "AQ.Ab8RN6J1534dkJROfaPGcYVxlrwOgxPr-BaqWREvrPFjWCbs2w",
    "AQ.Ab8RN6JyWOJbd5AXhum9GEd9jzlzUqB9An6bYtvODySiVS9vkg",
    "AQ.Ab8RN6IMxas44_Sn56nqe8ZngRJjkpXYJsBdPNK9_LUh-YUKVQ",
    "AQ.Ab8RN6L4bla4xwRJ0m5Lg-uvA7Oz_uUdUuhC1zZhxs3znQvcVQ",
    "AQ.Ab8RN6IEtYAfWhKSgDeTAsG0mbkJW9vbZSQXAqbf6XPu7pua3A",
    "AQ.Ab8RN6L_8u_uE3wE6_GGVuWpbENw2w7LNJG3jQu5eHocldiyRg",
    "AQ.Ab8RN6JSCAHpZjD_gKx5InNsiX-W8wf01sOk23heXL1ybEOTrw",
    "AQ.Ab8RN6LsSG9hpTZ6uvI8Uf36uoBQSV0gt5Yy0VIaWxFRmXbZ_g",
    "AQ.Ab8RN6JKg4fVJTb4vkKjcMn84DV0b6QUGXzJWfJ8ok7IHsKAOQ",
    "AQ.Ab8RN6IVUIc2sZH7jRsf0QrET4RgbzqyFxrYf61Lp0MXoBXfsg",
    "AQ.Ab8RN6K1WiqgWRB3qLAw6e83YD8-KuxQ_gGck6KZNnhWJpyvZA",
    "AQ.Ab8RN6Je49z7nBCwNhSkQjQ2rNWu3GIAbrtv6-3pNhJ5umV5xg",
    "AQ.Ab8RN6KXABmLBHKcfsnFA74DzGj6H8LsXmqU7n5uhNbrPMVSeg",
    "AQ.Ab8RN6KwbCqgjpFtaRx6MuEAb08xJGY5tFulZdFiQJPeaSQwdQ",
    "AQ.Ab8RN6JBTYSd1I-0R9lmCOO1kiprpVdn2EUq9XHC6_VXKUEw5Q",
    "AQ.Ab8RN6I_X1ApS7sb-LnSvGTgsHtXIu7IwsdfDLMzxlg3CuM2fA",
    "AQ.Ab8RN6IFOuTvmzy-7IdM7-xnfEii-L7rSiLvozbwFKfOQQfbyw",
    "AQ.Ab8RN6J6zJm06Lo4UjaqqeDpEZbmQo1zybjgMkb0C2-O1Jiphw",
    "AQ.Ab8RN6Krz7IIYgSivI7MBJEW-Z7-h-YmAITvb6f1PHkd7IxyDg",
    "AQ.Ab8RN6LN4FTiGadsRet_ASxyPI5ywC2FC9j-7WnuzJYooP9LtA",
    "AQ.Ab8RN6IajM9bUuxZk6cdl7k5AAZqci7U0rPC88FyY4j2HTFmtw",
    "AQ.Ab8RN6Jd302Pjl6Igm1q3iw6QuUR4_LUOpxz0ouiBR-9-VZAsw",
    "AQ.Ab8RN6KHPqh-C8ha_Ln6naxDdWWfO_MRTBRnCvoBCFdZQc1vfQ",
    "AQ.Ab8RN6Lw5ARmkZYmYxMzd5Qkx4PJ9S3G-623Lq0F96_Z2W0lJQ",
    "AQ.Ab8RN6KIqbbPGZ6J4MmqhMXDYrO1D_qlIzCP3FYLov1mq5RLGg",
    "AQ.Ab8RN6IGrwdGi3XEJ6s7-V9YKQ3AGqMcrNJW9y9WWuefDO0BRw",
    "AQ.Ab8RN6LShB-E-mUy9kRk0blNuz5QDX9B15WJqN6euFc4NCNP0Q",
    "AQ.Ab8RN6IxKdI2SkxKHSCaaMJjMRdolw5NP15xV7x5Megr9ijWiA",
    "AQ.Ab8RN6Lu2beS_XhQP01Qwd1GG6bt51SFd-pqlYQxfLP-13qYXg",
    "AQ.Ab8RN6JdT_4ptdSAW_TzJ4a-50cw0kzsWWHh8pJSXwTGov5Aqg",
    "AQ.Ab8RN6JynpNXVYGo2fbGp5XL025-wLt-nBUlecwI4MlADCoA3g",
    "AQ.Ab8RN6Jcf0x_ppuUviazNldf2pqnUP-WkWJGckF4eHy5W1xerA",
    "AQ.Ab8RN6L_A7O0sYzJreqSp79kIfrA-Ns21yZfvzIevAV0KVgFBg",
    "AQ.Ab8RN6J7dvVa2c8G5XhmQGMPbU-zRBMO9MeSo01cWv0RkFmiUw",
    "AQ.Ab8RN6LKJdsRX91wsn0Ggb4X-zXJs2sMyjSGD-OWJtXZsyklBg",
    "AQ.Ab8RN6JhGXfWvIPc7_ld3IYpFOkkbwmgrg_8tSSbAnZcZTy5aQ",
    "AQ.Ab8RN6JECGGo-p7hMeWtGJNzWPOjy0ldA5wNJbJZsE_56BDquw",
    "AQ.Ab8RN6LkI73vF4Zb4NDzRx_lDLSwcCkdIShc8sdVNsXY9Qqkrg",
    "AQ.Ab8RN6IQnQe76El-Ze2YbK7a871F_vpoSFpRRgaQ1arLlUcE-w",
    "AQ.Ab8RN6IbS4IJGkRXq7r39lAB_GJ4-Wre5aqffxSQAPnlBiBl4w",
    "AQ.Ab8RN6IdDr5gnL-GPev9RtW2zlhgrqxiSMbrVr0T--O8KIT2YQ",
    "AQ.Ab8RN6LCUKV0SkmfJjrpA861JjxfD9QajIRLmhVfTGwXRLtpxQ",
    "AQ.Ab8RN6IMed9W9K3KjFGpPH1C57Pd1EdEjtTUnZYuJAGjNMMyNA",
    "AQ.Ab8RN6L5EdCdHHqx9ddZhj3FpMaUusvXFMR_miz50qfLcWO5YA",
    "AQ.Ab8RN6IrTqCK2A63lkTEOMtHWUMuTecHxUPia2_SsaiaRxJqew",
    "AQ.Ab8RN6K9QIrtVEHM1NhRuRLVUsVAK2MmX2BFOsOBfei7y4REOw",
    "AQ.Ab8RN6JOvX6RIctTS8Ey_p0Wqd7lNVz5GnKO1bTX1BvHDZRXLA",
    "AQ.Ab8RN6L04e-I0l-J-sFbH6lFVKSnl81QaYTdI5HCr3NmW2UWwQ",
    "AQ.Ab8RN6KH59opEtDSvVuVe-2xJymSxLbcEuVXgdFfcnXXhA4NnA",
    "AQ.Ab8RN6JYYwkNcp2JULO5cHPwHFqlNXv2kh48Hz21zvEZaiJkSw",
    "AQ.Ab8RN6I665eTEXskUUCFWFEQsarNGYqG1ecWDv-rLuD6sMpirw",
    "AQ.Ab8RN6LrLgHmD6c32d1zqLPTbH3iorqqjMcnd5xJRtD9963D8A",
    "AQ.Ab8RN6I47SDQNGExUItz1yHf9DKIHaM-JITDQV0uOQdqKAJ80w",
    "AQ.Ab8RN6KHR2BC_2ckLWAAla0rLF2PYVeOf1Euu5NBr2IzL4qIvA",
    "AQ.Ab8RN6JQFJxqCYM5Rrv5XzBBlf9ERi3FugUj4fRa4ohU7vX7FA",
    "AQ.Ab8RN6LLyE-KOZ9LTanUymgroiKY3b1aBrab1FTq9qBQ7VB1ZQ",
    "AQ.Ab8RN6KwxxL0UrgyMW6N7aYzBHIjMDSoEXOc_mgs7uwWa0eD_w",
    "AQ.Ab8RN6JqrgwmGc-7yKL1ZiGhZfh2P7MyhIKuXzjbt-DzSd3_eQ",
    "AQ.Ab8RN6Le7y6tPYJ9Ux46KZ3jEsTjMPChaMnbJNgywEzHuGRmHA",
    "AQ.Ab8RN6J7dvVa2c8G5XhmQGMPbU-zRBMO9MeSo01cWv0RkFmiUw"
]

current_key_index = 0

def call_gemini_rest_api(prompt):
    global current_key_index
    if not GEMINI_API_KEYS:
        return None
    
    # 99ኙን Keys በየተራ በመቀያየር መጠቀሚያ (Rotation)
    api_key = GEMINI_API_KEYS[current_key_index]
    current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            logging.error(f"API Error Status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Request Error: {e}")
        return None

def is_amharic(text):
    return bool(re.search(r'[\u1200-\u137F]', text))

def search_books_db(query, grade):
    if not os.path.exists('books.db'):
        return None
    try:
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()
        sql_query = "SELECT text FROM data WHERE LOWER(text) LIKE LOWER(?) LIMIT 1"
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
    
    amharic_input = is_amharic(user_text)
    status_text = "🔍 በመፈለግ ላይ..." if amharic_input else "🔍 Searching..."
    status_msg = await update.message.reply_text(status_text)

    response_text = None

    # 1. መጀመሪያ በ SQLite ዳታቤዝ (መጽሐፉ) ውስጥ መፈለግ
    db_result = search_books_db(user_text, user_grade)
    if db_result:
        response_text = db_result

    # 2. መጽሐፉ ላይ ካላገኘ በ Gemini REST API መፈለግ
    if not response_text:
        prompt = (
            f"You are FAF ELA AI, an educational assistant for Ethiopian high school students (Grade {user_grade}).\n"
            f"User Question: {user_text}\n\n"
            "Instructions:\n"
            "- Answer accurately based on high school level content.\n"
            "- If the user asks in Amharic, respond in Amharic. If in English, respond in English."
        )
        response_text = call_gemini_rest_api(prompt)

    # 3. በሁለቱም ካላገኘ
    if not response_text:
        response_text = (
            "ይቅርታ፣ ጥያቄውን መመለስ አልተቻለም። እባክዎን ጥያቄዎን አስተካክለው ይጻፉ።" 
            if amharic_input else 
            "Sorry, I couldn't generate an answer for this prompt. Please try rephrasing your question."
        )

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
