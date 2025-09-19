from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.types import LabeledPrice, PreCheckoutQuery
from services.user_service import UserService
from utils.database import get_db_session
from config import config
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "subscription")
async def show_subscription_info(callback: CallbackQuery):
    """Показ информации о подписке"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return
            
            # Проверяем текущий статус подписки
            days_left = 0
            if user.subscription_end:
                days_left = max(0, (user.subscription_end - datetime.utcnow()).days)
            
            if user.is_premium and days_left > 0:
                # Пользователь уже имеет активную подписку
                text = f"""
💎 <b>Активная подписка</b>

✅ Premium активен до: {user.subscription_end.strftime("%d.%m.%Y")}
📅 Осталось дней: {days_left}

🌟 <b>Ваши преимущества:</b>
- Неограниченные квизы и тесты
- Аудио произношение слов
- Расширенная статистика прогресса
- Персональные планы обучения
- Приоритетная поддержка

🎁 <b>Не забывайте:</b> Занимайтесь 30 дней подряд и получите месяц бесплатно!
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="pay_subscription")],
                    [InlineKeyboardButton(text="ℹ️ Условия акции", callback_data="promotion_info")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
                ])
            else:
                # Предложение подписки
                days_to_free_month = max(0, 30 - user.streak_days) if not user.free_month_used else "недоступно"
                
                text = f"""
💳 <b>Подписка English Learning Bot</b>

🌟 <b>Premium возможности:</b>
- Неограниченные квизы и тесты
- Аудио произношение всех слов
- Расширенная статистика прогресса
- Персональные планы обучения
- Приоритетная поддержка
- Эксклюзивные материалы

💰 <b>Цена:</b> {config.SUBSCRIPTION_PRICE}₽ в месяц

🎁 <b>СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ:</b>
Занимайтесь 30 дней подряд и получите следующий месяц БЕСПЛАТНО!

🔥 <b>До бесплатного месяца:</b> {days_to_free_month} дней

⚡ <b>Первые 3 дня бесплатно</b> для всех новых пользователей
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"💳 Оплатить {config.SUBSCRIPTION_PRICE}₽", callback_data="pay_subscription")],
                    [InlineKeyboardButton(text="ℹ️ Условия акции", callback_data="promotion_info")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
                ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_subscription_info: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "promotion_info")
async def show_promotion_info(callback: CallbackQuery):
    """Показ условий акции"""
    text = """
🎁 <b>УСЛОВИЯ АКЦИИ "30 ДНЕЙ - МЕСЯЦ В ПОДАРОК"</b>

✅ <b>Как получить:</b>
1. Оформите подписку за 99₽
2. Занимайтесь каждый день в течение 30 дней подряд
3. Автоматически получите +30 дней бесплатно!

📋 <b>Что считается ежедневной активностью:</b>
- Прохождение хотя бы одного квиза
- Изучение слова дня
- Выполнение любого упражнения

⚠️ <b>Важно:</b>
- Акция действует только 1 раз для каждого пользователя
- При пропуске дня счетчик обнуляется
- Бесплатный месяц добавляется к действующей подписке

🔥 <b>Мотивация:</b> Система покажет ваш прогресс и напомнит о занятиях!

💡 <b>Секрет:</b> Большинство пользователей, которые занимаются 30 дней подряд, продолжают заниматься и дальше!
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="pay_subscription")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "pay_subscription")
async def process_payment(callback: CallbackQuery):
    """Обработка платежа"""
    if not config.PAYMENT_TOKEN:
        await callback.message.answer(
            "❌ <b>Платежи временно недоступны</b>\n\n"
            "Свяжитесь с поддержкой для активации Premium.",
            parse_mode="HTML"
        )
        return
    
    try:
        prices = [LabeledPrice(label="Подписка на месяц", amount=config.SUBSCRIPTION_PRICE * 100)]  # в копейках
        
        await callback.message.answer_invoice(
            title="English Learning Bot - Premium подписка",
            description=f"Premium подписка на 1 месяц за {config.SUBSCRIPTION_PRICE}₽. Получите доступ ко всем функциям: неограниченные квизы, аудио произношение, расширенная статистика и многое другое!",
            payload="subscription_monthly",
            provider_token=config.PAYMENT_TOKEN,
            currency="RUB",
            prices=prices,
            start_parameter="subscription",
            photo_url="https://via.placeholder.com/400x300/4CAF50/FFFFFF?text=Premium",
            photo_size=400,
            photo_width=400,
            photo_height=300
        )
        
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        await callback.message.answer(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            parse_mode="HTML"
        )

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительной проверки платежа"""
    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logger.error(f"Error in pre_checkout_query: {e}")
        await pre_checkout_query.answer(ok=False, error_message="Ошибка обработки платежа")

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    """Обработка успешного платежа"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(message.from_user.id)
            
            if not user:
                await message.answer("❌ Пользователь не найден")
                return
            
            # Активируем подписку
            await user_service.update_subscription(user, months=1)
            
            # Записываем платеж
            user.total_paid += config.SUBSCRIPTION_PRICE
            await db_session.commit()
            
            # Обновляем информацию о пользователе
            await db_session.refresh(user)
            
            days_left = (user.subscription_end - datetime.utcnow()).days
            days_to_free_month = max(0, 30 - user.streak_days) if not user.free_month_used else 0
            
            success_text = f"""
🎉 <b>Оплата успешно прошла!</b>

✅ Premium активирован до: {user.subscription_end.strftime("%d.%m.%Y")}
📅 Активна на: {days_left} дней

🎁 <b>Не забывайте:</b> занимайтесь {days_to_free_month} дней подряд и получите месяц бесплатно!

🚀 <b>Теперь вам доступны все функции:</b>
- 🎯 Безлимитные квизы
- 🔊 Аудио произношение 
- 📊 Детальная статистика
- 🎨 Персональные планы
- 🔔 Умные уведомления
- ⚡ Приоритетная поддержка

<b>Начните изучение прямо сейчас!</b>
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Начать изучение", callback_data="take_quiz")],
                [InlineKeyboardButton(text="📖 Слово дня", callback_data="word_of_day")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await message.answer(success_text, reply_markup=keyboard, parse_mode="HTML")
            
            # Отправляем уведомление через некоторое время с советами
            await asyncio.sleep(2)
            tips_text = """
💡 <b>Советы для эффективного обучения:</b>

🌅 <b>Утром:</b> Изучайте новые слова - мозг лучше запоминает
🌆 <b>Вечером:</b> Повторяйте изученное - закрепляйте материал
🎯 <b>Ежедневно:</b> Проходите хотя бы один квиз для серии дней
🔔 <b>Уведомления:</b> Не отключайте - они помогают не забывать

Удачи в изучении английского! 🚀
            """
            
            await message.answer(tips_text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in successful_payment: {e}")
            await message.answer("❌ Ошибка при активации подписки. Обратитесь в поддержку.")