from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload
from models.database import User, UserProgress, UserAchievement, Achievement
from utils.helpers import calculate_streak_bonus, is_premium_feature_available
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> User:
        """Создание нового пользователя"""
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                subscription_end=datetime.utcnow() + timedelta(days=3),  # 3 дня бесплатно
                is_premium=True  # Бесплатный период
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Created new user: {telegram_id}")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user {telegram_id}: {e}")
            raise
    
    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        try:
            result = await self.db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None
    
    async def get_user_with_relations(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя со связанными данными"""
        try:
            result = await self.db.execute(
                select(User)
                .options(
                    selectinload(User.user_words),
                    selectinload(User.progress_records),
                    selectinload(User.achievements)
                )
                .where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user with relations {telegram_id}: {e}")
            return None
    
    async def update_user_activity(self, user: User) -> None:
        """Обновление времени последней активности"""
        try:
            user.last_activity = datetime.utcnow()
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user activity {user.telegram_id}: {e}")
    
    async def update_streak(self, user: User) -> dict:
        """Обновление серии дней и возврат информации об изменениях"""
        try:
            today = datetime.utcnow().date()
            last_activity_date = user.last_activity.date() if user.last_activity else None
            
            old_streak = user.streak_days
            streak_broken = False
            
            if last_activity_date == today:
                # Уже засчитан сегодня
                return {"streak_continued": False, "streak_broken": False, "new_streak": user.streak_days}
            elif last_activity_date == today - timedelta(days=1):
                # Продолжаем серию
                user.streak_days += 1
            else:
                # Серия прервалась
                if user.streak_days > 0:
                    streak_broken = True
                user.streak_days = 1
            
            user.last_activity = datetime.utcnow()
            
            # Проверяем достижение 30 дней для бесплатного месяца
            free_month_granted = False
            if user.streak_days == 30 and not user.free_month_used:
                await self.grant_free_month(user)
                free_month_granted = True
            
            await self.db.commit()
            
            return {
                "streak_continued": True,
                "streak_broken": streak_broken,
                "old_streak": old_streak,
                "new_streak": user.streak_days,
                "free_month_granted": free_month_granted
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating streak for user {user.telegram_id}: {e}")
            return {"streak_continued": False, "streak_broken": False, "new_streak": user.streak_days}
    
    async def grant_free_month(self, user: User) -> None:
        """Предоставление бесплатного месяца"""
        try:
            user.free_month_used = True
            
            if user.subscription_end and user.subscription_end > datetime.utcnow():
                user.subscription_end += timedelta(days=30)
            else:
                user.subscription_end = datetime.utcnow() + timedelta(days=30)
            
            user.is_premium = True
            await self.db.commit()
            
            logger.info(f"Granted free month to user {user.telegram_id}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error granting free month to user {user.telegram_id}: {e}")
    
    async def add_points(self, user: User, base_points: int) -> int:
        """Добавление очков с учетом бонусов"""
        try:
            # Применяем бонус за серию дней
            multiplier = calculate_streak_bonus(user.streak_days)
            actual_points = int(base_points * multiplier)
            
            user.total_points += actual_points
            await self.db.commit()
            
            logger.info(f"Added {actual_points} points to user {user.telegram_id} (base: {base_points}, multiplier: {multiplier})")
            return actual_points
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding points to user {user.telegram_id}: {e}")
            return 0
    
    async def update_subscription(self, user: User, months: int = 1) -> None:
        """Обновление подписки"""
        try:
            current_end = user.subscription_end or datetime.utcnow()
            
            if current_end > datetime.utcnow():
                # Продлеваем существующую подписку
                user.subscription_end = current_end + timedelta(days=30 * months)
            else:
                # Новая подписка
                user.subscription_end = datetime.utcnow() + timedelta(days=30 * months)
            
            user.is_premium = True
            await self.db.commit()
            
            logger.info(f"Updated subscription for user {user.telegram_id} for {months} months")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating subscription for user {user.telegram_id}: {e}")
    
    async def record_daily_progress(self, user: User, **progress_data) -> None:
        """Запись ежедневного прогресса"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Проверяем существует ли запись за сегодня
            result = await self.db.execute(
                select(UserProgress).where(
                    and_(
                        UserProgress.user_id == user.id,
                        UserProgress.date >= today,
                        UserProgress.date < today + timedelta(days=1)
                    )
                )
            )
            
            progress = result.scalar_one_or_none()
            
            if not progress:
                progress = UserProgress(user_id=user.id, date=today)
                self.db.add(progress)
            
            # Обновляем данные прогресса
            for key, value in progress_data.items():
                if hasattr(progress, key):
                    current_value = getattr(progress, key, 0)
                    setattr(progress, key, current_value + value)
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording daily progress for user {user.telegram_id}: {e}")
    
    async def get_user_statistics(self, user: User, days: int = 7) -> dict:
        """Получение статистики пользователя за период"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.db.execute(
                select(UserProgress).where(
                    and_(
                        UserProgress.user_id == user.id,
                        UserProgress.date >= start_date
                    )
                ).order_by(UserProgress.date.desc())
            )
            
            progress_records = result.scalars().all()
            
            stats = {
                "total_days_active": len(progress_records),
                "total_words_studied": sum(p.words_studied for p in progress_records),
                "total_quizzes_passed": sum(p.quizzes_passed for p in progress_records),
                "total_points_earned": sum(p.points_earned for p in progress_records),
                "total_time_spent": sum(p.time_spent for p in progress_records),
                "average_accuracy": 0,
                "daily_records": []
            }
            
            # Расчет средней точности
            total_correct = sum(p.correct_answers for p in progress_records)
            total_answers = sum(p.total_answers for p in progress_records)
            
            if total_answers > 0:
                stats["average_accuracy"] = round((total_correct / total_answers) * 100, 1)
            
            # Подготовка данных по дням
            for progress in progress_records:
                accuracy = 0
                if progress.total_answers > 0:
                    accuracy = round((progress.correct_answers / progress.total_answers) * 100, 1)
                
                stats["daily_records"].append({
                    "date": progress.date.strftime("%Y-%m-%d"),
                    "words_studied": progress.words_studied,
                    "quizzes_passed": progress.quizzes_passed,
                    "points_earned": progress.points_earned,
                    "accuracy": accuracy,
                    "time_spent": progress.time_spent
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user statistics {user.telegram_id}: {e}")
            return {}
    
    async def check_achievements(self, user: User) -> List[dict]:
        """Проверка и выдача новых достижений"""
        try:
            # Получаем уже полученные достижения
            result = await self.db.execute(
                select(UserAchievement.achievement_id).where(
                    UserAchievement.user_id == user.id
                )
            )
            earned_achievement_ids = {row[0] for row in result.fetchall()}
            
            # Получаем все доступные достижения
            result = await self.db.execute(select(Achievement))
            all_achievements = result.scalars().all()
            
            new_achievements = []
            
            for achievement in all_achievements:
                if achievement.id in earned_achievement_ids:
                    continue
                
                # Проверяем условия достижения
                earned = False
                
                if achievement.condition_type == "streak" and user.streak_days >= achievement.condition_value:
                    earned = True
                elif achievement.condition_type == "points" and user.total_points >= achievement.condition_value:
                    earned = True
                elif achievement.condition_type == "words" and user.words_learned >= achievement.condition_value:
                    earned = True
                
                if earned:
                    # Выдаем достижение
                    user_achievement = UserAchievement(
                        user_id=user.id,
                        achievement_id=achievement.id
                    )
                    self.db.add(user_achievement)
                    
                    new_achievements.append({
                        "name": achievement.name,
                        "description": achievement.description,
                        "icon": achievement.icon
                    })
            
            if new_achievements:
                await self.db.commit()
                logger.info(f"Granted {len(new_achievements)} new achievements to user {user.telegram_id}")
            
            return new_achievements
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error checking achievements for user {user.telegram_id}: {e}")
            return []
    
    async def get_premium_users_for_notifications(self, time_str: str) -> List[User]:
        """Получение премиум пользователей для уведомлений в определенное время"""
        try:
            current_time = datetime.utcnow()
            
            result = await self.db.execute(
                select(User).where(
                    and_(
                        User.notifications_enabled == True,
                        User.is_premium == True,
                        User.subscription_end > current_time,
                        (User.morning_time == time_str) | (User.evening_time == time_str)
                    )
                )
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting premium users for notifications: {e}")
            return []