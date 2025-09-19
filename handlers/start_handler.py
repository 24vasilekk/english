from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import UserService
from services.word_service import WordService
from utils.database import get_db_session
from utils.helpers import get_user_level_info
import logging

logger = logging.getLogger(__name__)
router = Router()

class UserState(StatesGroup):
    taking_level_test = State()
    selecting_topics = State()

# Тест на определение уровня
LEVEL_TEST_QUESTIONS = [
    {
        "question": "What ___ your name?",
        "options": ["am", "is", "are", "be"],
        "correct": 1,
        "level": "A1"
    },
    {
        "question": "I ___ to the cinema yesterday.",
        "options": ["go", "went", "have gone", "going"],
        "correct": 1,
        "level": "A2"
    },
    {
        "question": "If I ___ rich, I would travel the world.",
        "options": ["am", "was", "were", "be"],
        "correct": 2,
        "level": "B1"
    },
    {
        "question": "The project ___ by next Friday.",
        "options": ["will finish", "will be finished", "finishes", "finished"],
        "correct": 1,
        "level": "B2"
    },
    {
        "question": "Had she studied harder, she ___ the exam.",
        "options": ["would pass", "would have passed", "passed", "will pass"],
        "correct": 1,
        "level": "C1"
    },
    {
        "question": "The theory ___ by Einstein revolutionized physics.",
        "options": ["proposed", "proposing", "to propose", "having proposed"],
        "correct": 0,
        "level": "C2"
    }
]

@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(message.from_user.id)
            
            if not user:
                # Новый пользователь
                user = await user_service.create_user(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                
                await show_welcome_message(message, state)
            else:
                # Существующий пользователь
                await show_main_menu(message, user)
                
        except Exception as e:
            logger.error(f"Error in start_handler: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def show_welcome_message(message: Message, state: FSMContext):
    """Приветственное сообщение для новых пользователей"""
    welcome_text = """
🎉 <b>Добро пожаловать в English Learning Bot!</b>

🚀 <b>Что вас ждет:</b>
- Персонализированное обучение на вашем уровне
- Ежедневные слова и фразы  
- Интервальные повторения для лучшего запоминания
- Система достижений и мотивации

💰 <b>Специальное предложение:</b>
Подписка всего 99₽/месяц
🎁 <b>БОНУС:</b> Занимайтесь 30 дней подряд и получите месяц БЕСПЛАТНО!

⚡ <b>Первые 3 дня бесплатно</b> для всех новых пользователей

Давайте определим ваш уровень английского!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Пройти тест на уровень", callback_data="start_level_test")],
        [InlineKeyboardButton(text="ℹ️ Узнать больше о боте", callback_data="info")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

async def show_main_menu(message: Message, user):
    """Главное меню для существующих пользователей"""
    from datetime import datetime
    
    days_left = 0
    if user.subscription_end:
        days_left = max(0, (user.subscription_end - datetime.utcnow()).days)
    
    level_info = get_user_level_info(user.level)
    premium_status = f"🔓 Premium активен ({days_left} дней)" if user.is_premium and days_left > 0 else "🔒 Базовая версия"
    
    menu_text = f"""
🏠 <b>Главное меню</b>

👤 <b>Ваш уровень:</b> {level_info['color']} {user.level} ({level_info['name']})
🔥 <b>Серия дней:</b> {user.streak_days}
⭐ <b>Очки:</b> {user.total_points:,}
📚 <b>Слов изучено:</b> {user.words_learned}

{premium_status}
    """
    
    keyboard_rows = [
        [InlineKeyboardButton(text="📖 Слово дня", callback_data="word_of_day")],
        [InlineKeyboardButton(text="🎯 Квиз", callback_data="take_quiz")],
        [InlineKeyboardButton(text="📊 Прогресс", callback_data="progress")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    ]
    
    if not user.is_premium or days_left <= 0:
        keyboard_rows.append([InlineKeyboardButton(text="💳 Подписка", callback_data="subscription")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.answer(menu_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            if user:
                await show_main_menu(callback.message, user)
            else:
                await callback.message.answer("❌ Пользователь не найден. Нажмите /start")
                
        except Exception as e:
            logger.error(f"Error in main_menu_callback: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    """Показ информации о боте"""
    info_text = """
ℹ️ <b>О English Learning Bot</b>

🎯 <b>Персонализированное обучение:</b>
- Тест определяет ваш уровень (A1-C2)
- Слова и упражнения подстраиваются под вас
- Тематические словари (работа, путешествия, еда)

🧠 <b>Эффективная методика:</b>
- Интервальные повторения для лучшего запоминания
- Алгоритм адаптируется под ваши успехи
- Разнообразные типы упражнений

🎮 <b>Мотивация и прогресс:</b>
- Система очков и достижений
- Серии дней с бонусами
- Подробная статистика

💎 <b>Premium возможности:</b>
- Безлимитные квизы
- Аудио произношение
- Расширенная статистика
- Персональные планы

🎁 <b>Специальная акция:</b>
Занимайтесь 30 дней подряд = месяц бесплатно!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать тест", callback_data="start_level_test")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.answer(info_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "start_level_test")
async def start_level_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста на определение уровня"""
    await state.set_state(UserState.taking_level_test)
    await state.update_data(
        question_index=0,
        correct_answers=0,
        user_answers=[],
        start_time=callback.message.date
    )
    
    test_intro = """
📝 <b>Тест на определение уровня английского</b>

Вам будет предложено 6 вопросов разной сложности.
Выберите наиболее подходящий вариант ответа.

⏱️ Время не ограничено, отвечайте спокойно.

Готовы начать?
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать тест", callback_data="begin_test")]
    ])
    
    await callback.message.answer(test_intro, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "begin_test")
async def begin_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста"""
    await send_test_question(callback.message, state)

async def send_test_question(message: Message, state: FSMContext):
    """Отправка вопроса теста"""
    data = await state.get_data()
    question_index = data.get("question_index", 0)
    
    if question_index >= len(LEVEL_TEST_QUESTIONS):
        await finish_level_test(message, state)
        return
    
    question = LEVEL_TEST_QUESTIONS[question_index]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i+1}. {option}", callback_data=f"test_answer_{i}")]
        for i, option in enumerate(question["options"])
    ])
    
    text = f"""
📝 <b>Вопрос {question_index + 1}/{len(LEVEL_TEST_QUESTIONS)}</b>

{question["question"]}

Выберите правильный вариант:
    """
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("test_answer_"))
async def process_test_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа в тесте"""
    answer_index = int(callback.data.split("_")[-1])
    data = await state.get_data()
    
    question_index = data.get("question_index", 0)
    question = LEVEL_TEST_QUESTIONS[question_index]
    
    correct_answers = data.get("correct_answers", 0)
    user_answers = data.get("user_answers", [])
    
    is_correct = answer_index == question["correct"]
    if is_correct:
        correct_answers += 1
        await callback.answer("✅ Правильно!", show_alert=False)
    else:
        await callback.answer("❌ Неправильно", show_alert=False)
    
    user_answers.append({
        "question_index": question_index,
        "answer": answer_index,
        "correct": is_correct,
        "level": question["level"]
    })
    
    await state.update_data(
        question_index=question_index + 1,
        correct_answers=correct_answers,
        user_answers=user_answers
    )
    
    await send_test_question(callback.message, state)

async def finish_level_test(message: Message, state: FSMContext):
    """Завершение теста и определение уровня"""
    data = await state.get_data()
    correct_answers = data.get("correct_answers", 0)
    user_answers = data.get("user_answers", [])
    
    # Определяем уровень на основе правильных ответов
    if correct_answers >= 5:
        level = "C1"
    elif correct_answers >= 4:
        level = "B2"
    elif correct_answers >= 3:
        level = "B1"
    elif correct_answers >= 2:
        level = "A2"
    else:
        level = "A1"
    
    # Сохраняем уровень пользователя
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(message.from_user.id)
            
            if user:
                user.level = level
                await db_session.commit()
                
                level_info = get_user_level_info(level)
                
                result_text = f"""
🎉 <b>Тест завершен!</b>

📊 <b>Результат:</b> {correct_answers}/{len(LEVEL_TEST_QUESTIONS)}
🎯 <b>Ваш уровень:</b> {level_info['color']} {level} ({level_info['name']})

📝 <b>Описание уровня:</b>
{level_info['description']}

Теперь выберите интересные темы для изучения:
                """
                
                await message.answer(result_text, parse_mode="HTML")
                await show_topic_selection(message, state)
            
        except Exception as e:
            logger.error(f"Error finishing level test: {e}")
            await message.answer("❌ Произошла ошибка при сохранении результатов")

async def show_topic_selection(message: Message, state: FSMContext):
    """Выбор тем для изучения"""
    topics = [
        ("💼", "work", "Работа и карьера"),
        ("✈️", "travel", "Путешествия"),
        ("🍕", "food", "Еда и рестораны"),
        ("💻", "technology", "Технологии"),
        ("🏥", "health", "Здоровье"),
        ("🎵", "entertainment", "Развлечения"),
        ("🎓", "education", "Образование"),
        ("🏠", "home", "Дом и семья")
    ]
    
    keyboard_rows = []
    for emoji, topic, name in topics:
        keyboard_rows.append([InlineKeyboardButton(
            text=f"{emoji} {name}", 
            callback_data=f"topic_{topic}"
        )])
    
    keyboard_rows.append([InlineKeyboardButton(text="✅ Готово", callback_data="topics_done")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    text = """
🎯 <b>Выберите интересные темы</b> (можно несколько):

Это поможет подобрать слова и фразы, которые вам пригодятся!
Вы сможете изменить темы позже в настройках.
    """
    
    await state.set_state(UserState.selecting_topics)
    await state.update_data(selected_topics=[])
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("topic_"))
async def toggle_topic(callback: CallbackQuery, state: FSMContext):
    """Переключение темы"""
    topic = callback.data.split("_")[1]
    data = await state.get_data()
    selected_topics = data.get("selected_topics", [])
    
    if topic in selected_topics:
        selected_topics.remove(topic)
        await callback.answer(f"❌ Тема убрана", show_alert=False)
    else:
        selected_topics.append(topic)
        await callback.answer(f"✅ Тема добавлена", show_alert=False)
    
    await state.update_data(selected_topics=selected_topics)

@router.callback_query(F.data == "topics_done")
async def finish_topic_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора тем"""
    data = await state.get_data()
    selected_topics = data.get("selected_topics", [])
    
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            if user:
                user.topics = selected_topics
                await db_session.commit()
                
                await state.clear()
                
                success_text = f"""
🎉 <b>Настройка завершена!</b>

✅ Ваш уровень: {user.level}
✅ Выбрано тем: {len(selected_topics)}

🚀 <b>Теперь вы можете:</b>
- Изучать слова дня
- Проходить персональные квизы
- Отслеживать прогресс
- Получать достижения

💡 <b>Совет:</b> Занимайтесь каждый день хотя бы 5 минут для максимального эффекта!
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📖 Первое слово", callback_data="word_of_day")],
                    [InlineKeyboardButton(text="🎯 Пройти квиз", callback_data="take_quiz")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ])
                
                await callback.message.answer(success_text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error finishing topic selection: {e}")
            await callback.answer("❌ Произошла ошибка при сохранении")