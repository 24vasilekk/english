from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import UserService
from services.word_service import WordService
from services.quiz_service import QuizService
from utils.database import get_db_session
from utils.helpers import is_premium_feature_available
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()

class QuizState(StatesGroup):
    taking_quiz = State()
    word_quiz = State()

@router.callback_query(F.data == "take_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    """Начало обычного квиза"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return
            
            # Проверяем доступ к премиум функциям
            if not is_premium_feature_available(user):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="subscription")]
                ])
                
                await callback.message.answer(
                    "🔒 <b>Квизы доступны только по подписке!</b>\n\n"
                    "Оформите подписку за 99₽ и получите доступ ко всем функциям:\n"
                    "• Неограниченные квизы\n"
                    "• Аудио произношение\n"
                    "• Детальная статистика\n"
                    "• Персональные планы обучения",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                return
            
            # Типы квизов
            quiz_types = [
                ("📚 Словарный квиз", "vocabulary"),
                ("📖 Обратный перевод", "reverse_vocabulary"),
                ("📝 Грамматика", "grammar"),
                ("🎲 Смешанный", "mixed")
            ]
            
            keyboard_rows = []
            for name, quiz_type in quiz_types:
                keyboard_rows.append([InlineKeyboardButton(
                    text=name, 
                    callback_data=f"quiz_type_{quiz_type}"
                )])
            
            keyboard_rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            
            text = """
🎯 <b>Выберите тип квиза:</b>

📚 <b>Словарный</b> - перевод с английского
📖 <b>Обратный</b> - перевод на английский  
📝 <b>Грамматика</b> - времена, предлоги, артикли
🎲 <b>Смешанный</b> - все типы вопросов

🔥 <b>Серия дней:</b> {user.streak_days} (бонус x{1.5 if user.streak_days >= 7 else 1})
            """.format(user=user)
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in start_quiz: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data.startswith("quiz_type_"))
async def select_quiz_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа квиза"""
    quiz_type = callback.data.split("_")[2]
    
    await state.set_state(QuizState.taking_quiz)
    await state.update_data(
        quiz_type=quiz_type,
        quiz_score=0,
        quiz_questions=0,
        questions_data=[],
        start_time=datetime.utcnow()
    )
    
    await send_quiz_question(callback.message, state)

async def send_quiz_question(message, state: FSMContext):
    """Отправка вопроса квиза"""
    async for db_session in get_db_session():
        try:
            data = await state.get_data()
            quiz_type = data.get("quiz_type")
            quiz_questions = data.get("quiz_questions", 0)
            
            if quiz_questions >= 10:
                await finish_quiz(message, state)
                return
            
            user_service = UserService(db_session)
            word_service = WordService(db_session)
            quiz_service = QuizService(db_session)
            
            user = await user_service.get_user(message.chat.id)
            
            question_data = None
            
            if quiz_type in ["vocabulary", "reverse_vocabulary"]:
                # Словарные квизы
                word = await word_service.get_word_of_day(user)
                if word:
                    if quiz_type == "vocabulary":
                        question_data = await quiz_service.create_vocabulary_quiz(user, word)
                    else:
                        question_data = await quiz_service.create_reverse_vocabulary_quiz(user, word)
            
            elif quiz_type == "grammar":
                # Грамматические квизы
                questions = await quiz_service.get_quiz_questions(user, 1, "grammar")
                if questions:
                    question_data = questions[0]
            
            else:  # mixed
                # Смешанный тип
                import random
                selected_type = random.choice(["vocabulary", "reverse_vocabulary", "grammar"])
                
                if selected_type == "grammar":
                    questions = await quiz_service.get_quiz_questions(user, 1, "grammar")
                    if questions:
                        question_data = questions[0]
                else:
                    word = await word_service.get_word_of_day(user)
                    if word:
                        if selected_type == "vocabulary":
                            question_data = await quiz_service.create_vocabulary_quiz(user, word)
                        else:
                            question_data = await quiz_service.create_reverse_vocabulary_quiz(user, word)
            
            if not question_data:
                await message.answer("❌ Не удалось создать вопрос. Попробуйте позже.")
                await state.clear()
                return
            
            # Сохраняем данные вопроса
            await state.update_data(current_question=question_data)
            
            # Формируем сообщение
            question_text = f"🎯 <b>Вопрос {quiz_questions + 1}/10</b>\n\n"
            
            if question_data.get("transcription"):
                question_text += f"{question_data['question']}\n📝 [{question_data['transcription']}]\n\n"
            else:
                question_text += f"{question_data['question']}\n\n"
            
            # Кнопки с вариантами ответов
            keyboard_rows = []
            for i, option in enumerate(question_data["options"]):
                keyboard_rows.append([InlineKeyboardButton(
                    text=f"{i+1}. {option}", 
                    callback_data=f"quiz_answer_{i}"
                )])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            
            await message.answer(question_text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error sending quiz question: {e}")
            await message.answer("❌ Произошла ошибка при создании вопроса")
            await state.clear()

@router.callback_query(F.data.startswith("quiz_answer_"))
async def process_quiz_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа в квизе"""
    answer_index = int(callback.data.split("_")[-1])
    
    async for db_session in get_db_session():
        try:
            data = await state.get_data()
            current_question = data.get("current_question")
            
            if not current_question:
                await callback.answer("❌ Ошибка данных вопроса")
                return
            
            correct_answer = current_question["correct_answer"]
            is_correct = answer_index == correct_answer
            
            # Обновляем статистику квиза
            quiz_score = data.get("quiz_score", 0)
            quiz_questions = data.get("quiz_questions", 0) + 1
            questions_data = data.get("questions_data", [])
            
            if is_correct:
                quiz_score += 1
                await callback.answer("✅ Правильно!", show_alert=True)
            else:
                correct_option = current_question["options"][correct_answer]
                await callback.answer(f"❌ Неправильно. Правильный ответ: {correct_option}", show_alert=True)
            
            # Сохраняем результат вопроса
            question_result = {
                "question": current_question["question"],
                "selected_answer": answer_index,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": current_question.get("explanation", "")
            }
            questions_data.append(question_result)
            
            # Отмечаем слово как изученное если это словарный квиз
            if current_question.get("word_id"):
                word_service = WordService(db_session)
                user_service = UserService(db_session)
                
                user = await user_service.get_user(callback.from_user.id)
                await word_service.mark_word_studied(
                    user.id, 
                    current_question["word_id"], 
                    is_correct
                )
            
            # Записываем результат квиза в базу если есть quiz_id
            if current_question.get("id"):
                quiz_service = QuizService(db_session)
                await quiz_service.record_quiz_result(
                    callback.from_user.id,
                    current_question["id"],
                    is_correct,
                    answer_index
                )
            
            await state.update_data(
                quiz_score=quiz_score,
                quiz_questions=quiz_questions,
                questions_data=questions_data
            )
            
            if quiz_questions >= 10:
                await finish_quiz(callback.message, state)
            else:
                await send_quiz_question(callback.message, state)
                
        except Exception as e:
            logger.error(f"Error processing quiz answer: {e}")
            await callback.answer("❌ Произошла ошибка")

async def finish_quiz(message, state: FSMContext):
    """Завершение квиза"""
    async for db_session in get_db_session():
        try:
            data = await state.get_data()
            score = data.get("quiz_score", 0)
            start_time = data.get("start_time")
            quiz_type = data.get("quiz_type", "mixed")
            
            user_service = UserService(db_session)
            user = await user_service.get_user(message.chat.id)
            
            # Рассчитываем время прохождения
            time_taken = 0
            if start_time:
                time_taken = int((datetime.utcnow() - start_time).total_seconds() / 60)
            
            # Определяем результат
            if score >= 9:
                result_emoji = "🏆"
                result_text = "Превосходно!"
                base_points = 100
            elif score >= 7:
                result_emoji = "🥇"
                result_text = "Отлично!"
                base_points = 80
            elif score >= 5:
                result_emoji = "🥈"
                result_text = "Хорошо!"
                base_points = 60
            else:
                result_emoji = "📚"
                result_text = "Нужно больше практики"
                base_points = 40
            
            # Добавляем очки с бонусами
            points_earned = await user_service.add_points(user, base_points)
            
            # Обновляем серию дней
            streak_info = await user_service.update_streak(user)
            
            # Записываем прогресс
            await user_service.record_daily_progress(
                user,
                quizzes_passed=1,
                correct_answers=score,
                total_answers=10,
                points_earned=points_earned,
                time_spent=time_taken
            )
            
            # Проверяем достижения
            new_achievements = await user_service.check_achievements(user)
            
            # Формируем сообщение с результатами
            result_message = f"""
{result_emoji} <b>Квиз завершен!</b>

📊 <b>Результат:</b> {score}/10 ({score * 10}%)
⭐ <b>Очки получено:</b> {points_earned}
⏱️ <b>Время:</b> {time_taken} мин

🔥 <b>Серия дней:</b> {user.streak_days}
📈 <b>Всего очков:</b> {user.total_points:,}

<i>{result_text}</i>
            """
            
            if streak_info.get("free_month_granted"):
                result_message += "\n🎁 <b>Поздравляем! Вы получили бесплатный месяц за 30 дней подряд!</b>"
            
            if new_achievements:
                result_message += "\n\n🏆 <b>Новые достижения:</b>\n"
                for achievement in new_achievements:
                    result_message += f"• {achievement['icon']} {achievement['name']}\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Еще квиз", callback_data="take_quiz")],
                [InlineKeyboardButton(text="📊 Подробные результаты", callback_data="quiz_details")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            # Сохраняем данные для детального просмотра
            await state.update_data(final_results=data)
            await state.set_state(None)
            
            await message.answer(result_message, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error finishing quiz: {e}")
            await message.answer("❌ Произошла ошибка при завершении квиза")
            await state.clear()

@router.callback_query(F.data == "quiz_details")
async def show_quiz_details(callback: CallbackQuery, state: FSMContext):
    """Показ детальных результатов квиза"""
    data = await state.get_data()
    final_results = data.get("final_results", {})
    questions_data = final_results.get("questions_data", [])
    
    if not questions_data:
        await callback.answer("❌ Данные результатов не найдены")
        return
    
    details_text = "📋 <b>Детальные результаты:</b>\n\n"
    
    for i, question_data in enumerate(questions_data):
        status = "✅" if question_data["is_correct"] else "❌"
        details_text += f"{status} <b>Вопрос {i+1}:</b>\n"
        details_text += f"<i>{question_data['question'][:50]}...</i>\n"
        
        if not question_data["is_correct"] and question_data.get("explanation"):
            details_text += f"💡 {question_data['explanation'][:100]}...\n"
        
        details_text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])
    
    await callback.message.answer(details_text, reply_markup=keyboard, parse_mode="HTML")

async def start_word_quiz(callback: CallbackQuery, word_id: int):
    """Начало квиза по конкретному слову"""
    # Реализация квиза по конкретному слову
    pass  # Добавьте реализацию при необходимости