from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from models.database import Quiz, UserQuizResult, User, Word
from utils.helpers import generate_quiz_options
import random
import logging

logger = logging.getLogger(__name__)

class QuizService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_quiz_questions(self, user: User, count: int = 10, quiz_type: str = None) -> List[Dict]:
        """Получение вопросов для квиза"""
        try:
            # Базовый запрос по уровню пользователя
            query = select(Quiz).where(Quiz.level == user.level)
            
            # Фильтр по типу квиза если указан
            if quiz_type:
                query = query.where(Quiz.quiz_type == quiz_type)
            
            # Фильтр по темам пользователя
            if user.topics:
                query = query.where(
                    (Quiz.topic.in_(user.topics)) | (Quiz.topic.is_(None))
                )
            
            result = await self.db.execute(
                query.order_by(func.random()).limit(count * 2)  # Берем больше для разнообразия
            )
            
            quizzes = result.scalars().all()
            
            if not quizzes:
                # Если нет квизов для уровня, берем более простые
                result = await self.db.execute(
                    select(Quiz).order_by(func.random()).limit(count)
                )
                quizzes = result.scalars().all()
            
            # Формируем вопросы
            questions = []
            selected_quizzes = random.sample(quizzes, min(count, len(quizzes)))
            
            for quiz in selected_quizzes:
                question_data = {
                    "id": quiz.id,
                    "question": quiz.question,
                    "options": quiz.options,
                    "correct_answer": quiz.correct_answer,
                    "quiz_type": quiz.quiz_type,
                    "explanation": quiz.explanation,
                    "difficulty": quiz.difficulty
                }
                questions.append(question_data)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting quiz questions for user {user.telegram_id}: {e}")
            return []
    
    async def create_vocabulary_quiz(self, user: User, word: Word) -> Optional[Dict]:
        """Создание словарного квиза на основе слова"""
        try:
            # Получаем случайные неправильные варианты
            result = await self.db.execute(
                select(Word.translation).where(
                    and_(
                        Word.level == user.level,
                        Word.id != word.id
                    )
                ).order_by(func.random()).limit(3)
            )
            
            wrong_translations = [row[0] for row in result.fetchall()]
            
            # Генерируем варианты ответов
            options, correct_index = generate_quiz_options(
                word.translation, wrong_translations, 4
            )
            
            question_data = {
                "word_id": word.id,
                "question": f"Как переводится слово: *{word.word}*",
                "transcription": word.transcription,
                "options": options,
                "correct_answer": correct_index,
                "quiz_type": "vocabulary",
                "explanation": f"*{word.word}* [{word.transcription}] - {word.translation}. {word.example}"
            }
            
            return question_data
            
        except Exception as e:
            logger.error(f"Error creating vocabulary quiz for word {word.id}: {e}")
            return None
    
    async def create_reverse_vocabulary_quiz(self, user: User, word: Word) -> Optional[Dict]:
        """Создание обратного словарного квиза (с русского на английский)"""
        try:
            # Получаем случайные неправильные варианты
            result = await self.db.execute(
                select(Word.word).where(
                    and_(
                        Word.level == user.level,
                        Word.id != word.id
                    )
                ).order_by