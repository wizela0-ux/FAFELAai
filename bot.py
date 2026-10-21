import os
import asyncio
import aiohttp
import html
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables & Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
# የሰጠኸው የ Firebase ዳታቤዝ ዩአርኤል
FIREBASE_DB_URL = "https://project-1f5123e4-74a0-48eb-88e-default-rtdb.firebaseio.com/".rstrip('/')

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN አልተገኘም!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# 📚 SUBJECTS MAPPING (አንተ የሰጠሃቸው ትምህርቶች)
# ==========================================
SUBJECTS_9_10 = [
    "English", "Math's", "Biology", "Physics", "Chemistry", 
    "Geography", "History", "Citizenship", "IT", "HPE", 
    "ሲልጢኘ", "አማርኛ", "Economics"
]

SUBJECTS_NATURAL = [
    "Biology", "Physics", "Chemistry", "Math's", 
    "English", "Agriculture", "Construction", "IT"
]

SUBJECTS_SOCIAL = [
    "Economics", "Citizenship", "History", "Maths", 
    "English", "Journal", "Geography", "Art"
]

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
        async with session.put(url, json=data)

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

class QuizState(StatesGroup):
    grade = State()
    stream = State()
    subject = State()
    unit = State()
    question_count = State()
    answering = State()

# ==========================================
# 🌐 KEYBOARDS & UI HELPERS
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

def get_grades_keyboard(lang: str = "am"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="9ኛ ክፍል (Grade 9)", callback_data="grade_9"),
            InlineKeyboardButton(text="10ኛ ክፍል (Grade 10)", callback_data="grade_10")
        ],
        [
            InlineKeyboardButton(text="11ኛ ክፍል (Grade 11)", callback_data="grade_11"),
            InlineKeyboardButton(text="12ኛ ክፍል (Grade 12)", callback_data="grade_12")
        ],
        [InlineKeyboardButton(text="🏠 ዋና ማውጫ (Main Menu)", callback_data="main_menu")]
    ])

def get_streams_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧬 ናቹራል ሳይንስ (Natural Science)", callback_data="stream_natural")],
        [InlineKeyboardButton(text="📚 ሶሻል ሳይንስ (Social Science)", callback_data="stream_social")],
        [InlineKeyboardButton(text="🔙 ተመለስ (Back)", callback_data="quiz_menu")]
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

@dp.message(Command("lang"))
async def cmd_lang(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_language)
    await message.answer("🌐 እባክዎ ቋንቋ ይምረጡ / Select language:", reply_markup=get_language_keyboard())

@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message, state: FSMContext):
    await start_quiz_process(message, state)

@dp.callback_query(UserState.waiting_for_language, F.data.startswith("lang_"))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    selected_lang = "am" if callback.data == "lang_am" else "en"
    user = callback.from_user
    
    await save_user(user.id, user.username, user.first_name, selected_lang)
    await state.clear()
    
    text = "🏠 <b>ዋና ማውጫ (Main Menu)</b>\n\nከታች ካሉት አማራጮች ይምረጡ፦" if selected_lang == "am" else "🏠 <b>Main Menu</b>\n\nChoose an option below:"
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(selected_lang), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_language(callback.from_user.id)
    text = "🏠 <b>ዋና ማውጫ (Main Menu)</b>\n\nከታች ካሉት አማራጮች ይምረጡ፦" if lang == "am" else "🏠 <b>Main Menu</b>\n\nChoose an option below:"
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(lang), parse_mode="HTML")
    await callback.answer()

# ==========================================
# 📝 QUIZ MODULE FLOW HANDLERS
# ==========================================
async def start_quiz_process(event, state: FSMContext):
    await state.clear()
    await state.set_state(QuizState.grade)
    text = "📚 <b>የክፍል ምርጫ (Grade Selection)</b>\n\nእባክዎ የሚማሩበትን ክፍል ይምረጡ፦"
    
    if isinstance(event, types.Message):
        await event.answer(text, reply_markup=get_grades_keyboard(), parse_mode="HTML")
    else:
        await event.message.edit_text(text, reply_markup=get_grades_keyboard(), parse_mode="HTML")
        await event.answer()

@dp.callback_query(F.data == "quiz_menu")
async def quiz_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await start_quiz_process(callback, state)

@dp.callback_query(QuizState.grade, F.data.startswith("grade_"))
async def process_grade_selection(callback: types.CallbackQuery, state: FSMContext):
    grade = callback.data.split("_")[1] # 9, 10, 11, 12
    await state.update_data(grade=grade)
    
    if grade in ["11", "12"]:
        await state.set_state(QuizState.stream)
        text = f"🧬 <b>ስትሪም ምርጫ ({grade}ኛ ክፍል)</b>\n\nእባክዎ ስትሪምዎን ይምረጡ፦"
        await callback.message.edit_text(text, reply_markup=get_streams_keyboard(), parse_mode="HTML")
    else:
        # Grade 9 or 10 -> Show Subjects directly
        await show_subjects(callback.message, state, grade, None)
    await callback.answer()

@dp.callback_query(QuizState.stream, F.data.startswith("stream_"))
async def process_stream_selection(callback: types.CallbackQuery, state: FSMContext):
    stream = callback.data.split("_")[1] # natural or social
    await state.update_data(stream=stream)
    data = await state.get_data()
    grade = data.get("grade")
    
    await show_subjects(callback.message, state, grade, stream)
    await callback.answer()

async def show_subjects(message: types.Message, state: FSMContext, grade: str, stream: str = None):
    await state.set_state(QuizState.subject)
    
    if grade in ["9", "10"]:
        sub_list = SUBJECTS_9_10
    else:
        sub_list = SUBJECTS_NATURAL if stream == "natural" else SUBJECTS_SOCIAL
        
    buttons = []
    for sub in sub_list:
        buttons.append([InlineKeyboardButton(text=sub, callback_data=f"sub_{sub}")])
    buttons.append([InlineKeyboardButton(text="🔙 ተመለስ (Back)", callback_data="quiz_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"📖 <b>የትምህርት አይነት ምርጫ ({grade}ኛ ክፍል)</b>\n\nእባክዎ የሚፈተኑበትን ትምህርት ይምረጡ፦"
    
    await message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(QuizState.subject, F.data.startswith("sub_"))
async def process_subject_selection(callback: types.CallbackQuery, state: FSMContext):
    subject = callback.data[4:] # get subject name
    await state.update_data(subject=subject)
    await state.set_state(QuizState.unit)
    
    # Fetch units from Firebase or show default dynamic units
    data = await state.get_data()
    grade = data.get("grade")
    stream = data.get("stream", "general")
    
    # Path in firebase: quizzes/Grade_X/Stream/Subject/units
    db_path = f"quizzes/Grade_{grade}/{stream}/{subject}/units"
    units_data = await fb_get(db_path)
    
    buttons = []
    if units_data and isinstance(units_data, dict):
        for unit_key in units_data.keys():
            buttons.append([InlineKeyboardButton(text=f"📂 {unit_key}", callback_data=f"unit_{unit_key}")])
    else:
        # Default sample units if none uploaded yet
        buttons.append([InlineKeyboardButton(text="📂 Unit 1", callback_data="unit_Unit_1")])
        buttons.append([InlineKeyboardButton(text="📂 Unit 2", callback_data="unit_Unit_2")])
        
    buttons.append([InlineKeyboardButton(text="➕ አዲስ ዩኒት ጨምር (Add Unit)", callback_data="unit_add_custom")])
    buttons.append([InlineKeyboardButton(text="🔙 ተመለስ (Back)", callback_data="quiz_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"📂 <b>የዩኒት ምርጫ ({subject})</b>\n\nእባክዎ ዩኒት ይምረጡ ወይም አዲስ ያክሉ፦"
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(QuizState.unit, F.data.startswith("unit_"))
async def process_unit_selection(callback: types.CallbackQuery, state: FSMContext):
    unit_action = callback.data[5:]
    
    if unit_action == "add_custom":
        await callback.message.edit_text("✍️ እባክዎ አዲሱን የዩኒት ስም/ቁጥር በጽሁፍ ይላኩ (ለምሳሌ፡ Unit 3)፦")
        # Can handle text input for custom unit here, or keep simple
        await callback.answer()
        return
        
    await state.update_data(unit=unit_action)
    await state.set_state(QuizState.question_count)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 ጥያቄ", callback_data="cnt_5"),
            InlineKeyboardButton(text="10 ጥያቄ", callback_data="cnt_10")
        ],
        [
            InlineKeyboardButton(text="15 ጥያቄ", callback_data="cnt_15"),
            InlineKeyboardButton(text="ሙሉውን (All)", callback_data="cnt_all")
        ],
        [InlineKeyboardButton(text="🔙 ተመለስ", callback_data="quiz_menu")]
    ])
    
    text = "🔢 <b>የጥያቄ ብዛት ምርጫ</b>\n\nስንት ጥያቄ መስራት ይፈልጋሉ?"
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(QuizState.question_count, F.data.startswith("cnt_"))
async def process_question_count(callback: types.CallbackQuery, state: FSMContext):
    count_type = callback.data.split("_")[1]
    
    data = await state.get_data()
    grade = data.get("grade")
    stream = data.get("stream", "general")
    subject = data.get("subject")
    unit = data.get("unit")
    
    # Fetch questions from Firebase
    db_path = f"quizzes/Grade_{grade}/{stream}/{subject}/{unit}/questions"
    questions = await fb_get(db_path)
    
    if not questions or not isinstance(questions, dict):
        # Sample questions fallback for testing immediately!
        questions = {
            "q1": {
                "question": f"Sample Question 1 for {subject} ({unit})?",
                "options": {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
                "correct": "B",
                "explanation": "This is a detailed explanation for question 1."
            },
            "q2": {
                "question": f"Sample Question 2 for {subject} ({unit})?",
                "options": {"A": "Choice A", "B": "Choice B", "C": "Choice C", "D": "Choice D"},
                "correct": "A",
                "explanation": "This is a detailed explanation for question 2."
            }
        }
        
    q_list = list(questions.values())
    if count_type != "all":
        limit = int(count_type)
        q_list = q_list[:limit]
        
    await state.update_data(questions=q_list, current_index=0, score=0, user_answers=[])
    await state.set_state(QuizState.answering)
    
    await send_quiz_question(callback.message, state, edit=True)
    await callback.answer()

async def send_quiz_question(message: types.Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    q_list = data.get("questions")
    index = data.get("current_index")
    
    if index >= len(q_list):
        await show_quiz_results(message, state)
        return
        
    q_data = q_list[index]
    total = len(q_list)
    
    text = (
        f"📝 <b>ጥያቄ {index + 1} / {total}</b>\n\n"
        f"<b>{html.escape(q_data['question'])}</b>\n\n"
        f"A) {html.escape(q_data['options']['A'])}\n"
        f"B) {html.escape(q_data['options']['B'])}\n"
        f"C) {html.escape(q_data['options']['C'])}\n"
        f"D) {html.escape(q_data['options']['D'])}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data="ans_A"),
            InlineKeyboardButton(text="B", callback_data="ans_B")
        ],
        [
            InlineKeyboardButton(text="C", callback_data="ans_C"),
            InlineKeyboardButton(text="D", callback_data="ans_D")
        ]
    ])
    
    if edit:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(QuizState.answering, F.data.startswith("ans_"))
async def process_answer_selection(callback: types.CallbackQuery, state: FSMContext):
    selected_option = callback.data.split("_")[1]
    data = await state.get_data()
    
    q_list = data.get("questions")
    index = data.get("current_index")
    score = data.get("score")
    user_answers = data.get("user_answers")
    
    current_q = q_list[index]
    correct_option = current_q["correct"]
    
    is_correct = (selected_option == correct_option)
    if is_correct:
        score += 1
        
    user_answers.append({
        "question": current_q["question"],
        "options": current_q["options"],
        "selected": selected_option,
        "correct": correct_option,
        "explanation": current_q.get("explanation", "ማብራሪያ የለውም"),
        "is_correct": is_correct
    })
    
    await state.update_data(score=score, user_answers=user_answers, current_index=index + 1)
    await send_quiz_question(callback.message, state, edit=True)
    await callback.answer()

async def show_quiz_results(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score")
    q_list = data.get("questions")
    user_answers = data.get("user_answers")
    total = len(q_list)
    percentage = int((score / total) * 100) if total > 0 else 0
    
    if percentage >= 80:
        feedback = "🌟 እጅግ በጣም ጎበዝ! ድንቅ ውጤት!"
    elif percentage >= 50:
        feedback = "👍 ጥሩ ነው! ግን አሁንም ማሻሻል ትችላለህ።"
    else:
        feedback = "⚠️ የበለጠ ጥናት ያስፈልግሃል! ድጋሚ ሞክር።"
        
    summary_text = (
        f"📊 <b>የኪዝ ማጠቃለያ ውጤት (Quiz Results)</b>\n\n"
        f"🎯 ያገኙት ውጤት፦ <b>{score} / {total} ({percentage}%)</b>\n"
        f"ግምገማ፦ {feedback}\n\n"
        f"👇 <b>ዝርዝር ግምገማ (Detailed Review):</b>\n"
    )
    
    for i, ans in enumerate(user_answers, 1):
        status = "✅" if ans["is_correct"] else "❌"
        summary_text += (
            f"\n<b>{i}. {html.escape(ans['question'])}</b>\n"
            f"{status} የእርስዎ መልስ: <b>{ans['selected']}</b> | ትክክለኛው: <b>{ans['correct']}</b>\n"
            f"💡 ማብራሪያ: {html.escape(ans['explanation'])}\n"
        )
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 ድጋሚ ይሞክሩ (Retry)", callback_data="quiz_menu"),
            InlineKeyboardButton(text="🏠 ዋና ማውጫ", callback_data="main_menu")
        ]
    ])
    
    await state.clear()
    await message.edit_text(summary_text, reply_markup=kb, parse_mode="HTML")

# Placeholder Callbacks for About & Support
@dp.callback_query(F.data == "about_us")
async def show_about_us(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 ዋና ማውጫ", callback_data="main_menu")]])
    text = "ℹ️ <b>ስለ እኛ</b>\n\nይህ የሁለተኛ ደረጃ ትምህርት ቤት የፈተና እና የኪዝ ቦት ነው።" if lang == "am" else "ℹ️ <b>About Us</b>\n\nEducational high school quiz and exam bot."
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    lang = await get_user_language(callback.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 ዋና ማውጫ", callback_data="main_menu")]])
    text = "☎️ <b>ድጋፍ</b>\n\nማንኛውም ጥያቄ ካለዎት አድሚኑን ያናግሩ።" if lang == "am" else "☎️ <b>Support</b>\n\nContact your administrator."
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
# 🔄 WEB SERVER FOR 24/7 HOSTING
# ==========================================
async def handle_ping(request):
    return web.Response(text="Educational High School Bot is active!")

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
