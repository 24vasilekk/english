import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy import select, and_
from config import config
from models.database import User
from services.user_service import UserService
from services.word_service import WordService
from utils.database import get_db_session
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

class DailyScheduler:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
    
    async def send_morning_notifications(self):
        """Утренняя рассылка - слово дня"""
        logger.info("Starting morning notifications")
        
        async for db_session in get_db_session():
            try:
                user_service = UserService(db_session)
                word_service = WordService(db_session)
                
                # Получаем пользователей для утренних уведомлений
                users = await user_service.get_premium_users_for_notifications("09:00")
                
                for user in users:
                    try:
                        word = await word_service.get_word_of_day(user)
                        
                        if not word:
                            continue
                        
                        text = f"""
🌅 <b>Доброе утро! Слово дня:</b>

🔤 <b>{word.word}</b> [{word.transcription}]
🇷🇺 {word.translation}

📝 <i>{word.definition}</i>

💬 <b>Пример:</b>
<i>{word.example}</i>

🎯 Не забудьте пройти квиз сегодня!
🔥 Серия дней: {user.streak_days}
                        """
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🎯 Пройти квиз", callback_data="take_quiz")],
                            [InlineKeyboardButton(text="📖 Еще слова", callback_data="word_of_day")]
                        ])
                        
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        
                        # Задержка между отправками
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error sending morning notification to {user.telegram_id}: {e}")
                
                logger.info(f"Sent morning notifications to {len(users)} users")
                
            except Exception as e:
                logger.error(f"Error in morning notifications: {e}")
    
    async def send_evening_notifications(self):
        """Вечерняя рассылка - напоминание о занятиях"""
        logger.info("Starting evening notifications")
        
        async for db_session in get_db_session():
            try:
                user_service = UserService(db_session)
                
                # Получаем пользователей для вечерних уведомлений
                users = await user_service.get_premium_users_for_notifications("19:00")
                
                for user in users:
                    try:
                        # Проверяем, занимался ли сегодня
                        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        result = await db_session.execute(
                            select(UserProgress).where(
                                and_(
                                    UserProgress.user_id == user.id,
                                    UserProgress.date >= today
                                )
                            )
                        )
                        
                        today_progress = result.scalar_one_or_none()
                        
                        if not today_progress or (today_progress.words_studied == 0 and today_progress.quizzes_passed == 0):
                            # Не занимался сегодня
                            days_to_free_month = max(0, 30 - user.streak_days)
                            
                            text = f"""
🌆 <b>Вечернее напоминание</b>

⚠️ Вы еще не занимались сегодня!
🔥 Серия дней: {user.streak_days}

⏰ Всего 5 минут в день помогут:
- Сохранить серию дней
- Получить бонусные очки
- Приблизиться к бесплатному месяцу ({days_to_free_month} дней осталось)

🎯 Пройдите хотя бы один квиз!
                            """
                            
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🎯 Быстрый квиз", callback_data="take_quiz")],
                                [InlineKeyboardButton(text="📖 Слово дня", callback_data="word_of_day")]
                            ])
                            
                            await self.bot.send_message(
                                chat_id=user.telegram_id,
                                text=text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )
                        
                        # Задержка между отправками
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error sending evening notification to {user.telegram_id}: {e}")
                
                logger.info(f"Processed evening notifications for {len(users)} users")
                
            except Exception as e:
                logger.error(f"Error in evening notifications: {e}")
    
    async def check_subscription_expiry(self):
        """Проверка истекающих подписок"""
        logger.info("Checking subscription expiry")
        
        async for db_session in get_db_session():
            try:
                # Подписки истекают завтра
                tomorrow = datetime.utcnow() + timedelta(days=1)
                
                result = await db_session.execute(
                    select(User).where(
                        and_(
                            User.is_premium == True,
                            User.subscription_end <= tomorrow,
                            User.subscription_end > datetime.utcnow()
                        )
                    )
                )
                
                expiring_users = result.scalars().all()
                
                for user in expiring_users:
                    try:
                        days_left = (user.subscription_end - datetime.utcnow()).days
                        
                        text = f"""
⚠️ <b>Подписка истекает</b>

Ваша Premium подписка истекает через {days_left} дн.

🚀 Продлите подписку, чтобы не потерять:
- Неограниченные квизы
- Аудио произношение
- Детальную статистику
- Персональные планы

💰 Всего 99₽ в месяц
                        """
                        
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="subscription")]
                        ])
                        
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                        
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error sending expiry notification to {user.telegram_id}: {e}")
                
                logger.info(f"Sent expiry notifications to {len(expiring_users)} users")
                
            except Exception as e:
                logger.error(f"Error checking subscription expiry: {e}")
    
    async def update_expired_subscriptions(self):
        """Обновление истёкших подписок"""
        logger.info("Updating expired subscriptions")
        
        async for db_session in get_db_session():
            try:
                current_time = datetime.utcnow()
                
                result = await db_session.execute(
                    select(User).where(
                        and_(
                            User.is_premium == True,
                            User.subscription_end <= current_time
                        )
                    )
                )
                
                expired_users = result.scalars().all()
                
                for user in expired_users:
                    user.is_premium = False
                
                if expired_users:
                    await db_session.commit()
                    logger.info(f"Updated {len(expired_users)} expired subscriptions")
                
            except Exception as e:
                await db_session.rollback()
                logger.error(f"Error updating expired subscriptions: {e}")
    
    def setup_schedule(self):
        """Настройка расписания задач"""
        # Утренние уведомления
        schedule.every().day.at("09:00").do(
            lambda: asyncio.create_task(self.send_morning_notifications())
        )
        
        # Вечерние уведомления
        schedule.every().day.at("19:00").do(
            lambda: asyncio.create_task(self.send_evening_notifications())
        )
        
        # Проверка истекающих подписок (каждый день в 12:00)
        schedule.every().day.at("12:00").do(
            lambda: asyncio.create_task(self.check_subscription_expiry())
        )
        
        # Обновление истёкших подписок (каждый час)
        schedule.every().hour.do(
            lambda: asyncio.create_task(self.update_expired_subscriptions())
        )
        
        logger.info("Scheduler setup completed")
    
    async def run_scheduler(self):
        """Запуск планировщика"""
        self.setup_schedule()
        
        logger.info("Scheduler started")
        
        while True:
            try:
                schedule.run_pending()
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)

async def main():
    """Главная функция для запуска планировщика"""
    scheduler = DailyScheduler()
    await scheduler.run_scheduler()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")