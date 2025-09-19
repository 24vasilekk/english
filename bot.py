import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from utils.database import init_database
from handlers import (
    start_handler,
    quiz_handler,
    subscription_handler,
    progress_handler,
    settings_handler,
    word_handler
)

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Создание бота и диспетчера
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация базы данных
        await init_database()
        logger.info("Database initialized successfully")
        
        # Регистрация роутеров
        dp.include_router(start_handler.router)
        dp.include_router(quiz_handler.router)
        dp.include_router(subscription_handler.router)
        dp.include_router(progress_handler.router)
        dp.include_router(settings_handler.router)
        dp.include_router(word_handler.router)
        
        logger.info("All routers registered")
        
        # Запуск бота
        if config.WEBHOOK_URL:
            # Webhook режим
            from aiohttp import web
            from aiohttp.web_request import Request
            
            app = web.Application()
            
            async def webhook(request: Request):
                update = await request.json()
                await dp.feed_update(bot, update)
                return web.Response()
            
            app.router.add_post(config.WEBHOOK_PATH, webhook)
            
            await bot.set_webhook(
                url=config.WEBHOOK_URL + config.WEBHOOK_PATH,
                drop_pending_updates=True
            )
            
            logger.info(f"Webhook set to {config.WEBHOOK_URL + config.WEBHOOK_PATH}")
            
            web.run_app(app, host="0.0.0.0", port=8080)
        else:
            # Polling режим
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Starting bot in polling mode")
            await dp.start_polling(bot)
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)