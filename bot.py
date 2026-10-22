import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ==========================================
# 1. RENDER KEEP-ALIVE SERVER (Flask)
# ==========================================
web_app = Flask(__name__)


@web_app.route('/')
def health_check():
    return "FAF Quiz Bot is running successfully!", 200


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)


# ==========================================
# 2. LOCALIZATION / LANGUAGES DATA
# ==========================================
STRINGS = {
    'am': {
        'select_lang': "እባክዎ ቋንቋ ይምረጡ / Please select your language:",
        'welcome': "እንኳን ደህና መጣህ {}! ወደ FAF Quiz እንኳን በደህና መጣህ።",
        'btn_quiz': "📚 ኩዊዝ (Quiz)",
        'btn_result': "📊 ውጤት (Result)",
        'btn_support': "💬 ድጋፍ (Support)",
        'btn_about': "ℹ️ ስለ እኛ (About Us)",
        'btn_main_menu': "🏠 ዋና ማኑ (Main Menu)",
        'btn_back': "⬅️ ተመለስ (Back)",
        'btn_try_again': "🔄 እንደገና ሞክር (Try Again)",
        'select_grade': "እባክዎ ክፍልዎን ይምረጡ፡",
        'select_stream': "እባክዎ ዘርፍዎን ይምረጡ፡",
        'select_subject': "እባክዎ የትምህርት ዓይነት ይምረጡ፡",
        'select_unit': "እባክዎ ዩኒት ይምረጡ፡",
        'no_questions': "እዚህ ሰብጀክት ላይ ምንም አይነት የዩኒት ጥያቄ አልተለቀቀም።",
        'available_q': "📌 የሚገኙ ጥያቄዎች ብዛት: {}\n\nእባክዎ የሚፈልጉትን የጥያቄ ብዛት ይምረጡ:",
        'quiz_finished': "🎉 ኩዊዙን አጠናቀሃል!\n\n📊 **ውጤት:** ከ {} ጥያቄዎች {} አግኝተሃል ({}%)\n\n{}",
        'review_title': "📝 **የጥያቄዎች ማብራሪያ (Review):**\n",
        'good_job': "👏 በጣም አሪፍ ስራ ነው! በርታ!",
        'keep_trying': "💪 ጥሩ ሙከራ ነው! ደግመህ በመስራት ውጤትህን አሻሽል።",
    },
    'en': {
        'select_lang': "Please select your language / እባክዎ ቋንቋ ይምረጡ:",
        'welcome': "Welcome {}! Welcome to FAF Quiz.",
        'btn_quiz': "📚 Quiz",
        'btn_result': "📊 Result",
        'btn_support': "💬 Support",
        'btn_about': "ℹ️ About Us",
        'btn_main_menu': "🏠 Main Menu",
        'btn_back': "⬅️ Back",
        'btn_try_again': "🔄 Try Again",
        'select_grade': "Please select your grade:",
        'select_stream': "Please select your stream:",
        'select_subject': "Please select a subject:",
        'select_unit': "Please select a unit:",
        'no_questions': "እዚህ ሰብጀክት ላይ ምንም አይነት የዩኒት ጥያቄ አልተለቀቀም።",
        'available_q': "📌 Available questions: {}\n\nPlease select the number of questions:",
        'quiz_finished': "🎉 Quiz Completed!\n\n📊 **Score:** You got {} out of {} ({}%)\n\n{}",
        'review_title': "📝 **Questions Review:**\n",
        'good_job': "👏 Great job! Keep it up!",
        'keep_trying': "💪 Good effort! Try again to improve your score.",
    }
}

# ==========================================
# 3. SAMPLE DATA (GRADE 11 MATHS UNIT 1 - STRICTLY ENGLISH)
# ==========================================
SAMPLE_QUESTIONS = [
    {
        "id": 1,
        "question": "1. What is the main difference between a Sequence and a Series?",
        "options": [
            "A) Sequence is a sum, Series is an ordered list",
            "B) Sequence is an ordered list, Series is the sum of terms",
            "C) Both are identical",
            "D) None of the above"
        ],
        "correct": 1,
        "explanation": "A sequence is an ordered list of numbers, whereas a series is the sum of the terms of a sequence."
    },
    {
        "id": 2,
        "question": "2. What symbol represents the common difference in an Arithmetic Sequence?",
        "options": ["A) r", "B) d", "C) S_n", "D) a_n"],
        "correct": 1,
        "explanation": "In an Arithmetic Sequence, the common difference is represented by 'd'."
    },
    {
        "id": 3,
        "question": "3. What is the 10th term (a_10) of the sequence 2, 4, 6, 8, ...?",
        "options": ["A) 18", "B) 20", "C) 22", "D) 24"],
        "correct": 1,
        "explanation": "a_n = a_1 + (n-1)d -> a_10 = 2 + (9)(2) = 20."
    },
    {
        "id": 4,
        "question": "4. What defines a Geometric Sequence?",
        "options": [
            "A) Having a common difference",
            "B) Having a common ratio 'r'",
            "C) Having a common sum",
            "D) None"
        ],
        "correct": 1,
        "explanation": "A Geometric Sequence is formed by multiplying the previous term by a common ratio 'r'."
    },
    {
        "id": 5,
        "question": "5. What is the sum of 1 + 2 + 3 + ... + 10?",
        "options": ["A) 45", "B) 50", "C) 55", "D) 60"],
        "correct": 2,
        "explanation": "S_n = n(n+1)/2 -> S_10 = 10(11)/2 = 55."
    }
]

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================
async def edit_or_send(update: Update, text: str, reply_markup=None):
    """ Cleans chat by replacing current message or sending new one """
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")


# ==========================================
# 5. COMMAND & MENU HANDLERS
# ==========================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang')
    if not lang:
        await cmd_lang(update, context)
    else:
        await show_main_menu(update, context)


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"{STRINGS['am']['select_lang']}\n\n{STRINGS['en']['select_lang']}"
    await edit_or_send(update, text, reply_markup)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    user_name = update.effective_user.first_name

    welcome_txt = STRINGS[lang]['welcome'].format(user_name)
    keyboard = [
        [InlineKeyboardButton(STRINGS[lang]['btn_quiz'], callback_data="menu_quiz")],
        [InlineKeyboardButton(STRINGS[lang]['btn_result'], callback_data="menu_result")],
        [InlineKeyboardButton(STRINGS[lang]['btn_support'], callback_data="menu_support")],
        [InlineKeyboardButton(STRINGS[lang]['btn_about'], callback_data="menu_about")]
    ]
    await edit_or_send(update, welcome_txt, InlineKeyboardMarkup(keyboard))


async def cmd_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    keyboard = [
        [InlineKeyboardButton("📌 Grade 9", callback_data="grade_9"), InlineKeyboardButton("📌 Grade 10", callback_data="grade_10")],
        [InlineKeyboardButton("📌 Grade 11", callback_data="grade_11"), InlineKeyboardButton("📌 Grade 12", callback_data="grade_12")],
        [InlineKeyboardButton(STRINGS[lang]['btn_main_menu'], callback_data="main_menu")]
    ]
    await edit_or_send(update, STRINGS[lang]['select_grade'], InlineKeyboardMarkup(keyboard))


# ==========================================
# 6. CALLBACK ROUTER
# ==========================================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("lang_"):
        selected_lang = data.split("_")[1]
        context.user_data['lang'] = selected_lang
        await show_main_menu(update, context)
        return

    lang = context.user_data.get('lang', 'am')

    if data == "main_menu":
        await show_main_menu(update, context)
        return

    elif data == "menu_quiz":
        await cmd_quiz(update, context)
        return

    elif data.startswith("grade_"):
        grade = data.split("_")[1]
        context.user_data['selected_grade'] = grade

        if grade in ["9", "10"]:
            subjects = [
                ("English", "sub_eng"), ("Maths", "sub_math"), ("Economics", "sub_eco"),
                ("Geography", "sub_geo"), ("Physics", "sub_phy"), ("Biology", "sub_bio"),
                ("Chemistry", "sub_chem"), ("Citizenship", "sub_cit"), ("History", "sub_his"),
                ("IT", "sub_it"), ("HPE", "sub_hpe"), ("አማርኛ", "sub_amh"), ("ስልጥኛ", "sub_slt")
            ]
            keyboard = [[InlineKeyboardButton(name, callback_data=code)] for name, code in subjects]
            keyboard.append([InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="menu_quiz")])
            await edit_or_send(update, STRINGS[lang]['select_subject'], InlineKeyboardMarkup(keyboard))

        elif grade in ["11", "12"]:
            keyboard = [
                [InlineKeyboardButton("🔬 Natural Science", callback_data="stream_nat")],
                [InlineKeyboardButton("📖 Social Science", callback_data="stream_soc")],
                [InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="menu_quiz")]
            ]
            await edit_or_send(update, STRINGS[lang]['select_stream'], InlineKeyboardMarkup(keyboard))

    elif data.startswith("stream_"):
        stream = data.split("_")[1]
        context.user_data['selected_stream'] = stream

        if stream == "nat":
            subjects = [
                ("Maths", "sub_math"), ("English", "sub_eng"), ("Physics", "sub_phy"),
                ("Biology", "sub_bio"), ("Chemistry", "sub_chem"), ("IT", "sub_it"),
                ("Agriculture", "sub_agri"), ("Construction", "sub_const")
            ]
        else:
            subjects = [
                ("Maths", "sub_math"), ("English", "sub_eng"), ("Economics", "sub_eco"),
                ("Geography", "sub_geo"), ("History", "sub_his"), ("Journalism", "sub_jour"),
                ("Citizenship", "sub_cit")
            ]

        keyboard = [[InlineKeyboardButton(name, callback_data=code)] for name, code in subjects]
        keyboard.append([InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data=f"grade_{context.user_data.get('selected_grade')}")])
        await edit_or_send(update, STRINGS[lang]['select_subject'], InlineKeyboardMarkup(keyboard))

    elif data.startswith("sub_"):
        context.user_data['selected_sub'] = data
        if data == "sub_math" and context.user_data.get('selected_grade') == "11" and context.user_data.get('selected_stream') == "nat":
            keyboard = [
                [InlineKeyboardButton("📖 Unit 1: Sequences & Series", callback_data="unit_1")],
                [InlineKeyboardButton("📖 Unit 2 (Not Released)", callback_data="unit_empty")],
                [InlineKeyboardButton(STRINGS[lang]['btn_main_menu'], callback_data="main_menu")]
            ]
            await edit_or_send(update, STRINGS[lang]['select_unit'], InlineKeyboardMarkup(keyboard))
        else:
            # Unreleased subject notification as requested
            keyboard = [[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="menu_quiz")]]
            await edit_or_send(update, STRINGS[lang]['no_questions'], InlineKeyboardMarkup(keyboard))

    elif data == "unit_empty":
        keyboard = [[InlineKeyboardButton(STRINGS[lang]['btn_back'], callback_data="sub_math")]]
        await edit_or_send(update, STRINGS[lang]['no_questions'], InlineKeyboardMarkup(keyboard))

    elif data == "unit_1":
        available_total = len(SAMPLE_QUESTIONS)
        context.user_data['available_total'] = available_total
        keyboard = [
            [InlineKeyboardButton(f"5 Questions (Available: {available_total})", callback_data="qcount_5")],
            [InlineKeyboardButton(STRINGS[lang]['btn_main_menu'], callback_data="main_menu")]
        ]
        text_msg = STRINGS[lang]['available_q'].format(available_total)
        await edit_or_send(update, text_msg, InlineKeyboardMarkup(keyboard))

    elif data == "qcount_5":
        context.user_data['quiz_index'] = 0
        context.user_data['answers'] = {}
        context.user_data['q_count'] = min(5, len(SAMPLE_QUESTIONS))
        await render_question(update, context)

    elif data.startswith("ans_"):
        parts = data.split("_")
        q_idx = int(parts[1])
        ans_idx = int(parts[2])

        answers = context.user_data.get('answers', {})
        answers[q_idx] = ans_idx
        context.user_data['answers'] = answers

        context.user_data['quiz_index'] = q_idx + 1
        await render_question(update, context)

    elif data.startswith("nav_"):
        target_idx = int(data.split("_")[1])
        context.user_data['quiz_index'] = target_idx
        await render_question(update, context)


async def render_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    idx = context.user_data.get('quiz_index', 0)
    answers = context.user_data.get('answers', {})
    q_count = context.user_data.get('q_count', len(SAMPLE_QUESTIONS))

    if idx >= q_count or idx >= len(SAMPLE_QUESTIONS):
        await render_summary(update, context)
        return

    q_data = SAMPLE_QUESTIONS[idx]
    q_text = q_data['question']
    options = q_data['options']

    # Display question text and options fully in message body
    msg_body = f"📍 ({idx + 1}/{q_count})\n\n**{q_text}**\n\n"
    for opt in options:
        msg_body += f"{opt}\n"

    # Inline keyboard contains only clean choice buttons [ A ] [ B ] [ C ] [ D ]
    keyboard = []
    opt_row = []
    for opt_idx, opt in enumerate(options):
        letter = opt.split(')')[0].strip()
        prefix = "✅ " if answers.get(idx) == opt_idx else ""
        opt_row.append(InlineKeyboardButton(f"{prefix}{letter}", callback_data=f"ans_{idx}_{opt_idx}"))
    
    keyboard.append(opt_row)

    nav_row = []
    if idx > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"nav_{idx-1}"))
    if idx in answers:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"nav_{idx+1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(STRINGS[lang]['btn_main_menu'], callback_data="main_menu")])

    await edit_or_send(update, msg_body, InlineKeyboardMarkup(keyboard))


async def render_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get('lang', 'am')
    answers = context.user_data.get('answers', {})
    q_count = context.user_data.get('q_count', len(SAMPLE_QUESTIONS))

    correct_count = 0
    total = q_count
    review_text = STRINGS[lang]['review_title']

    for idx in range(q_count):
        q_data = SAMPLE_QUESTIONS[idx]
        user_ans = answers.get(idx)
        correct_ans = q_data['correct']

        q_txt = q_data['question']
        exp_txt = q_data['explanation']

        if user_ans == correct_ans:
            correct_count += 1
            review_text += f"\n✅ **{q_txt}**\n💡 {exp_txt}\n"
        else:
            options = q_data['options']
            correct_option_txt = options[correct_ans]
            review_text += f"\n❌ **{q_txt}**\n👉 Correct: {correct_option_txt}\n💡 {exp_txt}\n"

    percent = int((correct_count / total) * 100) if total > 0 else 0
    feedback = STRINGS[lang]['good_job'] if percent >= 75 else STRINGS[lang]['keep_trying']
    final_msg = STRINGS[lang]['quiz_finished'].format(total, correct_count, percent, feedback) + "\n" + review_text

    keyboard = [
        [InlineKeyboardButton(STRINGS[lang]['btn_try_again'], callback_data="qcount_5")],
        [InlineKeyboardButton(STRINGS[lang]['btn_main_menu'], callback_data="main_menu")]
    ]
    await edit_or_send(update, final_msg, InlineKeyboardMarkup(keyboard))


# ==========================================
# 7. MAIN ENTRY POINT
# ==========================================
def main():
    threading.Thread(target=run_web_server, daemon=True).start()

    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable not set.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("quiz", cmd_quiz))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    print("FAF Quiz Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
