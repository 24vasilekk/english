from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload
from models.database import Word, UserWord, User
from utils.helpers import calculate_next_review, update_easiness_factor
import random
import logging

logger = logging.getLogger(__name__)

class WordService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_word_of_day(self, user: User) -> Optional[Word]:
        """Получение слова дня для пользователя"""
        try:
            # Получаем слова подходящего уровня
            level_filter = Word.level == user.level
            
            # Фильтр по темам если выбраны
            topic_filter = True
            if user.topics:
                topic_filter = Word.topic.in_(user.topics)
            
            # Исключаем хорошо изученные слова (stage >= 4)
            subquery = select(UserWord.word_id).where(
                and_(
                    UserWord.user_id == user.id,
                    UserWord.stage >= 4
                )
            )
            
            result = await self.db.execute(
                select(Word).where(
                    and_(
                        level_filter,
                        topic_filter,
                        ~Word.id.in_(subquery)
                    )
                ).order_by(func.random()).limit(1)
            )
            
            word = result.scalar_one_or_none()
            
            # Если не нашли новых слов, берем любое слово уровня
            if not word:
                result = await self.db.execute(
                    select(Word).where(level_filter).order_by(func.random()).limit(1)
                )
                word = result.scalar_one_or_none()
            
            return word
            
        except Exception as e:
            logger.error(f"Error getting word of day for user {user.telegram_id}: {e}")
            return None
    
    async def get_words_for_review(self, user: User, limit: int = 10) -> List[Word]:
        """Получение слов для повторения"""
        try:
            current_time = datetime.utcnow()
            
            result = await self.db.execute(
                select(Word)
                .join(UserWord)
                .where(
                    and_(
                        UserWord.user_id == user.id,
                        UserWord.next_repeat <= current_time,
                        UserWord.stage < 5  # Не берем полностью изученные
                    )
                )
                .order_by(UserWord.next_repeat)
                .limit(limit)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting words for review for user {user.telegram_id}: {e}")
            return []
    
    async def get_random_words(self, user: User, count: int = 5, exclude_word_id: int = None) -> List[Word]:
        """Получение случайных слов для создания вариантов ответов"""
        try:
            query = select(Word).where(Word.level == user.level)
            
            if exclude_word_id:
                query = query.where(Word.id != exclude_word_id)
            
            result = await self.db.execute(
                query.order_by(func.random()).limit(count)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting random words: {e}")
            return []
    
    async def mark_word_studied(self, user_id: int, word_id: int, is_correct: bool, difficulty: int = 3) -> Dict:
        """Отметка изучения слова с обновлением алгоритма повторений"""
        try:
            # Получаем или создаем UserWord
            result = await self.db.execute(
                select(UserWord).where(
                    and_(
                        UserWord.user_id == user_id,
                        UserWord.word_id == word_id
                    )
                )
            )
            
            user_word = result.scalar_one_or_none()
            
            if not user_word:
                user_word = UserWord(
                    user_id=user_id,
                    word_id=word_id,
                    stage=0,
                    easiness_factor=2.5
                )
                self.db.add(user_word)
            
            # Обновляем статистику
            user_word.total_reviews += 1
            user_word.last_seen = datetime.utcnow()
            
            if is_correct:
                user_word.correct_count += 1
                user_word.stage = min(5, user_word.stage + 1)
            else:
                user_word.incorrect_count += 1
                user_word.stage = max(0, user_word.stage - 1)
            
            # Обновляем коэффициент легкости
            user_word.easiness_factor = update_easiness_factor(
                user_word.easiness_factor, is_correct, difficulty
            )
            
            # Рассчитываем следующее повторение
            user_word.next_repeat = calculate_next_review(
                user_word.stage, user_word.easiness_factor
            )
            
            await self.db.commit()
            
            return {
                "stage": user_word.stage,
                "next_repeat": user_word.next_repeat,
                "easiness_factor": user_word.easiness_factor,
                "total_reviews": user_word.total_reviews
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking word studied: {e}")
            return {}
    
    async def get_user_word_stats(self, user_id: int, word_id: int) -> Optional[Dict]:
        """Получение статистики пользователя по конкретному слову"""
        try:
            result = await self.db.execute(
                select(UserWord).where(
                    and_(
                        UserWord.user_id == user_id,
                        UserWord.word_id == word_id
                    )
                )
            )
            
            user_word = result.scalar_one_or_none()
            
            if not user_word:
                return None
            
            return {
                "stage": user_word.stage,
                "correct_count": user_word.correct_count,
                "incorrect_count": user_word.incorrect_count,
                "total_reviews": user_word.total_reviews,
                "accuracy": user_word.correct_count / user_word.total_reviews * 100 if user_word.total_reviews > 0 else 0,
                "next_repeat": user_word.next_repeat,
                "learned_at": user_word.learned_at,
                "last_seen": user_word.last_seen
            }
            
        except Exception as e:
            logger.error(f"Error getting user word stats: {e}")
            return None
    
    async def get_words_by_topic(self, topic: str, level: str = None, limit: int = 20) -> List[Word]:
        """Получение слов по теме"""
        try:
            query = select(Word).where(Word.topic == topic)
            
            if level:
                query = query.where(Word.level == level)
            
            result = await self.db.execute(
                query.order_by(Word.frequency_rank.nulls_last()).limit(limit)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting words by topic {topic}: {e}")
            return []
    
    async def search_words(self, query: str, limit: int = 10) -> List[Word]:
        """Поиск слов по запросу"""
        try:
            search_pattern = f"%{query.lower()}%"
            
            result = await self.db.execute(
                select(Word).where(
                    or_(
                        func.lower(Word.word).contains(search_pattern),
                        func.lower(Word.translation).contains(search_pattern)
                    )
                ).limit(limit)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error searching words with query '{query}': {e}")
            return []
    
    async def get_user_learned_words_count(self, user_id: int) -> int:
        """Получение количества изученных слов пользователя"""
        try:
            result = await self.db.execute(
                select(func.count(UserWord.id)).where(
                    and_(
                        UserWord.user_id == user_id,
                        UserWord.stage >= 3  # Считаем изученными с 3 стадии
                    )
                )
            )
            
            count = result.scalar() or 0
            
            # Обновляем счетчик в профиле пользователя
            await self.db.execute(
                update(User).where(User.id == user_id).values(words_learned=count)
            )
            await self.db.commit()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting learned words count for user {user_id}: {e}")
            return 0
    
    async def get_words_due_for_review_count(self, user_id: int) -> int:
        """Получение количества слов готовых для повторения"""
        try:
            current_time = datetime.utcnow()
            
            result = await self.db.execute(
                select(func.count(UserWord.id)).where(
                    and_(
                        UserWord.user_id == user_id,
                        UserWord.next_repeat <= current_time,
                        UserWord.stage < 5
                    )
                )
            )
            
            return result.scalar() or 0
            
        except Exception as e:
            logger.error(f"Error getting words due for review count: {e}")
            return 0