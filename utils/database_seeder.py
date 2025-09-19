import json
import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import Word, Quiz, Achievement
from utils.database import get_db_session

logger = logging.getLogger(__name__)

async def seed_database():
    """Заполнение базы данных начальными данными"""
    async for db_session in get_db_session():
        try:
            await seed_words(db_session)
            await seed_quizzes(db_session) 
            await seed_achievements(db_session)
            await db_session.commit()
            logger.info("Database seeded successfully!")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Error seeding database: {e}")
            raise

async def seed_words(db_session: AsyncSession):
    """Заполнение таблицы слов"""
    words_file = Path("data/words.json")
    
    if not words_file.exists():
        logger.warning("Words file not found, skipping word seeding")
        return
    
    with open(words_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for word_data in data["words"]:
        # Проверяем, существует ли слово
        existing = await db_session.execute(
            select(Word).where(Word.word == word_data["word"])
        )
        
        if existing.scalar_one_or_none():
            continue
        
        word = Word(
            word=word_data["word"],
            transcription=word_data["transcription"],
            translation=word_data["translation"],
            definition=word_data.get("definition"),
            example=word_data.get("example"),
            level=word_data["level"],
            topic=word_data.get("topic"),
            frequency_rank=word_data.get("frequency_rank")
        )
        
        db_session.add(word)
    
    logger.info(f"Added {len(data['words'])} words to database")

async def seed_quizzes(db_session: AsyncSession):
    """Заполнение таблицы квизов"""
    quizzes_file = Path("data/quizzes.json")
    
    if not quizzes_file.exists():
        logger.warning("Quizzes file not found, skipping quiz seeding")
        return
    
    with open(quizzes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for quiz_data in data["quizzes"]:
        quiz = Quiz(### 22. `handlers/word_handler.py`
```python
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService
from services.word_service import WordService
from services.audio_service import AudioService
from utils.database import get_db_session
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "word_of_day")
async def word_of_day_handler(callback: CallbackQuery):
    """Обработчик слова дня"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            word_service = WordService(db_session)
            audio_service = AudioService()
            
            user = await user_service.get_user(callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return
            
            # Получаем слово дня
            word = await word_service.get_word_of_day(user)
            if not word:
                await callback.answer("❌ Слова не найдены для вашего уровня")
                return
            
            # Обновляем активность пользователя
            await user_service.update_user_activity(user)
            
            # Формируем сообщение
            word_text = f"""
📖 <b>Слово дня</b>

🔤 <b>{word.word}</b> [{word.transcription}]
🇷🇺 {word.translation}

📝 <i>Определение:</i> {word.definition or 'Не указано'}

💬 <b>Пример:</b>
<i>{word.example}</i>

🎯 <b>Уровень:</b> {word.level}
🏷️ <b>Тема:</b> {word.topic or 'Общая'}
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔊 Произношение", callback_data=f"audio_{word.id}")],
                [InlineKeyboardButton(text="✅ Изучено", callback_data=f"mark_learned_{word.id}")],
                [InlineKeyboardButton(text="🎯 Квиз по этому слову", callback_data=f"word_quiz_{word.id}")],
                [InlineKeyboardButton(text="🔄 Другое слово", callback_data="word_of_day")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await callback.message.answer(word_text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in word_of_day_handler: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data.startswith("audio_"))
async def audio_handler(callback: CallbackQuery):
    """Обработчик аудио произношения"""
    word_id = int(callback.data.split("_")[1])
    
    async for db_session in get_db_session():
        try:
            word_service = WordService(db_session)
            audio_service = AudioService()
            
            # Получаем слово
            result = await            result = await self.db.execute(
                select(Word.word).where(
                    and_(
                        Word.level == user.level,
                        Word.id != word.id
                    )
                ).order_by(func.random()).limit(3)
            )
            
            wrong_words = [row[0] for row in result.fetchall()]
            
            # Генерируем варианты ответов
            options, correct_index = generate_quiz_options(
                word.word, wrong_words, 4
            )
            
            question_data = {
                "word_id": word.id,
                "question": f"Как переводится: *{word.translation}*",
                "options": options,
                "correct_answer": correct_index,
                "quiz_type": "reverse_vocabulary",
                "explanation": f"{word.translation} - *{word.word}* [{word.transcription}]. {word.example}"
            }
            
            return question_data
            
        except Exception as e:
            logger.error(f"Error creating reverse vocabulary quiz for word {word.id}: {e}")
            return None
    
    async def record_quiz_result(self, user_id: int, quiz_id: int, is_correct: bool, 
                                selected_answer: int, time_taken: int = None) -> None:
        """Запись результата квиза"""
        try:
            quiz_result = UserQuizResult(
                user_id=user_id,
                quiz_id=quiz_id,
                is_correct=is_correct,
                selected_answer=selected_answer,
                time_taken=time_taken
            )
            
            self.db.add(quiz_result)
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording quiz result: {e}")
    
    async def get_user_quiz_statistics(self, user_id: int, days: int = 7) -> Dict:
        """Получение статистики квизов пользователя"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                select(UserQuizResult).where(
                    and_(
                        UserQuizResult.user_id == user_id,
                        UserQuizResult.created_at >= start_date
                    )
                )
            )
            
            results = result.scalars().all()
            
            if not results:
                return {
                    "total_quizzes": 0,
                    "correct_answers": 0,
                    "accuracy": 0,
                    "average_time": 0,
                    "best_streak": 0
                }
            
            total_quizzes = len(results)
            correct_answers = sum(1 for r in results if r.is_correct)
            accuracy = round((correct_answers / total_quizzes) * 100, 1)
            
            # Средний время ответа
            times = [r.time_taken for r in results if r.time_taken]
            average_time = round(sum(times) / len(times), 1) if times else 0
            
            # Лучшая серия правильных ответов
            best_streak = 0
            current_streak = 0
            
            for result in sorted(results, key=lambda x: x.created_at):
                if result.is_correct:
                    current_streak += 1
                    best_streak = max(best_streak, current_streak)
                else:
                    current_streak = 0
            
            return {
                "total_quizzes": total_quizzes,
                "correct_answers": correct_answers,
                "accuracy": accuracy,
                "average_time": average_time,
                "best_streak": best_streak
            }
            
        except Exception as e:
            logger.error(f"Error getting quiz statistics for user {user_id}: {e}")
            return {}
    
    async def get_quiz_by_id(self, quiz_id: int) -> Optional[Quiz]:
        """Получение квиза по ID"""
        try:
            result = await self.db.execute(
                select(Quiz).where(Quiz.id == quiz_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting quiz {quiz_id}: {e}")
            return None