from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.user_service import UserService
from utils.database import get_db_session
from utils.helpers import validate_time_format, get_user_level_info
import logging

logger = logging.getLogger(__name__)
router = Router()

class SettingsState(StatesGroup):
    setting_morning_time = State()
    setting_evening_time = State()
    selecting_topics = State()
    changing_level = State()

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показ настроек"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return
            
            notifications_status = "✅ Включены" if user.notifications_enabled else "❌ Отключены"
            level_info = get_user_level_info(user.level)
            topics_text = ", ".join(user.topics) if user.topics else "Не выбраны"
            
            # Показываем статус подписки
            subscription_status = "🔓 Premium" if user.is_premium else "🔒 Базовая"
            
            text = f"""
⚙️ <b>Настройки</b>

🔔 <b>Уведомления:</b> {notifications_status}
🌅 <b>Утреннее время:</b> {user.morning_time}
🌆 <b>Вечернее время:</b> {user.evening_time}
🎯 <b>Уровень:</b> {level_info['color']} {user.level} ({level_info['name']})
📚 <b>Темы:</b> {topics_text}
🎮 <b>Подписка:</b> {subscription_status}

💡 <b>Совет:</b> Настройте уведомления для лучших результатов!
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔔 Переключить уведомления", callback_data="toggle_notifications")],
                [InlineKeyboardButton(text="🌅 Изменить утреннее время", callback_data="set_morning_time")],
                [InlineKeyboardButton(text="🌆 Изменить вечернее время", callback_data="set_evening_time")],
                [InlineKeyboardButton(text="🎯 Изменить уровень", callback_data="change_level")],
                [InlineKeyboardButton(text="📚 Выбрать темы", callback_data="select_topics")],
                [InlineKeyboardButton(text="🗑️ Сбросить прогресс", callback_data="reset_progress")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_settings: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "toggle_notifications")
async def toggle_notifications(callback: CallbackQuery):
    """Переключение уведомлений"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            user.notifications_enabled = not user.notifications_enabled
            await db_session.commit()
            
            status = "включены" if user.notifications_enabled else "отключены"
            emoji = "🔔" if user.notifications_enabled else "🔕"
            
            await callback.answer(f"{emoji} Уведомления {status}!", show_alert=True)
            
            # Обновляем меню настроек
            await show_settings(callback)
            
        except Exception as e:
            logger.error(f"Error toggling notifications: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "set_morning_time")
async def set_morning_time(callback: CallbackQuery, state: FSMContext):
    """Установка утреннего времени"""
    await state.set_state(SettingsState.setting_morning_time)
    
    text = """
🌅 <b>Настройка утреннего времени</b>

Введите время в формате <b>ЧЧ:ММ</b> (например: 09:00)

В это время вы будете получать:
- Слово дня с переводом и примером
- Аудио произношение
- Мотивационные сообщения

⏰ <b>Рекомендуемое время:</b> 08:00 - 10:00
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="settings")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(SettingsState.setting_morning_time)
async def process_morning_time(message: Message, state: FSMContext):
    """Обработка ввода утреннего времени"""
    time_str = message.text.strip()
    
    if not validate_time_format(time_str):
        await message.answer(
            "❌ Неверный формат времени! Используйте формат ЧЧ:ММ (например: 09:00)"
        )
        return
    
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(message.from_user.id)
            
            user.morning_time = time_str
            await db_session.commit()
            
            await state.clear()
            
            await message.answer(
                f"✅ Утреннее время установлено на {time_str}!\n\n"
                f"Теперь вы будете получать слово дня в {time_str} каждый день.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error setting morning time: {e}")
            await message.answer("❌ Произошла ошибка при сохранении времени")

@router.callback_query(F.data == "set_evening_time")
async def set_evening_time(callback: CallbackQuery, state: FSMContext):
    """Установка вечернего времени"""
    await state.set_state(SettingsState.setting_evening_time)
    
    text = """
🌆 <b>Настройка вечернего времени</b>

Введите время в формате <b>ЧЧ:ММ</b> (например: 19:00)

В это время вы будете получать:
- Напоминания о занятиях (если не занимались)
- Информацию о серии дней
- Мотивационные сообщения

⏰ <b>Рекомендуемое время:</b> 18:00 - 21:00
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="settings")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(SettingsState.setting_evening_time)
async def process_evening_time(message: Message, state: FSMContext):
    """Обработка ввода вечернего времени"""
    time_str = message.text.strip()
    
    if not validate_time_format(time_str):
        await message.answer(
            "❌ Неверный формат времени! Используйте формат ЧЧ:ММ (например: 19:00)"
        )
        return
    
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(message.from_user.id)
            
            user.evening_time = time_str
            await db_session.commit()
            
            await state.clear()
            
            await message.answer(
                f"✅ Вечернее время установлено на {time_str}!\n\n"
                f"Теперь вы будете получать напоминания в {time_str} каждый день.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error setting evening time: {e}")
            await message.answer("❌ Произошла ошибка при сохранении времени")

@router.callback_query(F.data == "change_level")
async def change_level(callback: CallbackQuery):
    """Изменение уровня английского"""
    text = """
🎯 <b>Изменение уровня английского</b>

Выберите ваш текущий уровень:

🟢 <b>A1</b> - Начинающий (базовые фразы)
🔵 <b>A2</b> - Элементарный (простые темы)
🟡 <b>B1</b> - Средний (основные идеи)
🟠 <b>B2</b> - Продвинутый средний (сложные тексты)
🔴 <b>C1</b> - Продвинутый (свободное общение)
🟣 <b>C2</b> - Владение в совершенстве

⚠️ <b>Внимание:</b> При смене уровня контент будет адаптирован под новый уровень.
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 A1 - Начинающий", callback_data="level_A1")],
        [InlineKeyboardButton(text="🔵 A2 - Элементарный", callback_data="level_A2")],
        [InlineKeyboardButton(text="🟡 B1 - Средний", callback_data="level_B1")],
        [InlineKeyboardButton(text="🟠 B2 - Продвинутый средний", callback_data="level_B2")],
        [InlineKeyboardButton(text="🔴 C1 - Продвинутый", callback_data="level_C1")],
        [InlineKeyboardButton(text="🟣 C2 - Совершенство", callback_data="level_C2")],
        [InlineKeyboardButton(text="🎯 Пройти тест заново", callback_data="start_level_test")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="settings")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("level_"))
async def set_level(callback: CallbackQuery):
    """Установка нового уровня"""
    new_level = callback.data.split("_")[1]
    
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            old_level = user.level
            user.level = new_level
            await db_session.commit()
            
            level_info = get_user_level_info(new_level)
            
            await callback.answer(f"✅ Уровень изменен на {new_level}!", show_alert=True)
            
            text = f"""
🎯 <b>Уровень обновлен!</b>

📊 <b>Старый уровень:</b> {old_level}
🆕 <b>Новый уровень:</b> {level_info['color']} {new_level} ({level_info['name']})

📚 <b>Что изменится:</b>
- Слова будут подбираться под новый уровень
- Квизы адаптируются под сложность
- Рекомендации станут более точными

💡 <b>Совет:</b> Если новый уровень кажется слишком сложным или легким, вы всегда можете изменить его в настройках.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📖 Попробовать слово", callback_data="word_of_day")],
                [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error setting level: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "select_topics")
async def select_topics(callback: CallbackQuery, state: FSMContext):
    """Выбор тем для изучения"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            await state.set_state(SettingsState.selecting_topics)
            await state.update_data(selected_topics=user.topics.copy() if user.topics else [])
            
            topics = [
                ("💼", "work", "Работа и карьера"),
                ("✈️", "travel", "Путешествия"),
                ("🍕", "food", "Еда и рестораны"),
                ("💻", "technology", "Технологии"),
                ("🏥", "health", "Здоровье"),
                ("🎵", "entertainment", "Развлечения"),
                ("🎓", "education", "Образование"),
                ("🏠", "home", "Дом и семья"),
                ("🌿", "nature", "Природа"),
                ("💰", "business", "Бизнес"),
                ("🎨", "art", "Искусство"),
                ("⚽", "sport", "Спорт")
            ]
            
            keyboard_rows = []
            for emoji, topic, name in topics:
                # Проверяем, выбрана ли тема
                status = " ✅" if topic in user.topics else ""
                keyboard_rows.append([InlineKeyboardButton(
                    text=f"{emoji} {name}{status}", 
                    callback_data=f"topic_toggle_{topic}"
                )])
            
            keyboard_rows.extend([
                [InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="save_topics")],
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="settings")]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
            
            selected_count = len(user.topics) if user.topics else 0
            
            text = f"""
📚 <b>Выбор тем для изучения</b>

Выберите темы, которые вас интересуют. Это поможет подобрать релевантные слова и фразы.

📊 <b>Выбрано тем:</b> {selected_count}

💡 <b>Рекомендуется:</b> выбрать 3-5 тем для оптимального результата.
            """
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in select_topics: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data.startswith("topic_toggle_"))
async def toggle_topic(callback: CallbackQuery, state: FSMContext):
    """Переключение темы"""
    topic = callback.data.split("_")[2]
    data = await state.get_data()
    selected_topics = data.get("selected_topics", [])
    
    if topic in selected_topics:
        selected_topics.remove(topic)
        await callback.answer("❌ Тема убрана", show_alert=False)
    else:
        selected_topics.append(topic)
        await callback.answer("✅ Тема добавлена", show_alert=False)
    
    await state.update_data(selected_topics=selected_topics)
    
    # Обновляем сообщение с новыми галочками
    await select_topics(callback, state)

@router.callback_query(F.data == "save_topics")
async def save_topics(callback: CallbackQuery, state: FSMContext):
    """Сохранение выбранных тем"""
    data = await state.get_data()
    selected_topics = data.get("selected_topics", [])
    
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            user.topics = selected_topics
            await db_session.commit()
            
            await state.clear()
            
            topics_text = ", ".join(selected_topics) if selected_topics else "Все темы"
            
            await callback.answer("✅ Темы сохранены!", show_alert=True)
            
            text = f"""
📚 <b>Темы обновлены!</b>

✅ <b>Выбранные темы:</b> {topics_text}

📖 <b>Что изменится:</b>
- Слова дня будут из выбранных тем
- Квизы адаптируются под ваши интересы
- Рекомендации станут более персональными

🚀 Теперь обучение будет еще более эффективным!
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📖 Попробовать слово", callback_data="word_of_day")],
                [InlineKeyboardButton(text="⚙️ К настройкам", callback_data="settings")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error saving topics: {e}")
            await callback.answer("❌ Произошла ошибка при сохранении")

@router.callback_query(F.data == "reset_progress")
async def reset_progress_confirm(callback: CallbackQuery):
    """Подтверждение сброса прогресса"""
    text = """
⚠️ <b>ВНИМАНИЕ: Сброс прогресса</b>

Вы уверены, что хотите сбросить весь прогресс?

❌ <b>Будет удалено:</b>
- Все изученные слова
- История квизов
- Серия дней
- Достижения
- Статистика

✅ <b>Останется:</b>
- Подписка
- Настройки уведомлений
- Выбранные темы

⚠️ <b>Это действие необратимо!</b>
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Да, сбросить ВСЕ", callback_data="confirm_reset")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="settings")]
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "confirm_reset")
async def confirm_reset_progress(callback: CallbackQuery):
    """Подтверждение сброса прогресса"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            # Сбрасываем прогресс (сохраняем подписку и настройки)
            user.total_points = 0
            user.streak_days = 0
            user.words_learned = 0
            user.last_word_study = None
            user.last_quiz = None
            
            # Удаляем связанные данные
            from sqlalchemy import delete
            from models.database import UserWord, UserProgress, UserQuizResult, UserAchievement
            
            await db_session.execute(delete(UserWord).where(UserWord.user_id == user.id))
            await db_session.execute(delete(UserProgress).where(UserProgress.user_id == user.id))
            await db_session.execute(delete(UserQuizResult).where(UserQuizResult.user_id == user.id))
            await db_session.execute(delete(UserAchievement).where(UserAchievement.user_id == user.id))
            
            await db_session.commit()
            
            await callback.answer("✅ Прогресс сброшен!", show_alert=True)
            
            text = """
🔄 <b>Прогресс успешно сброшен!</b>

✅ Теперь вы можете начать обучение заново
🎯 Рекомендуем пройти тест на уровень
📚 Все настройки и подписка сохранены

🚀 <b>Готовы к новому старту?</b>
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Пройти тест на уровень", callback_data="start_level_test")],
                [InlineKeyboardButton(text="📖 Изучать слова", callback_data="word_of_day")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            await db_session.rollback()
            logger.error(f"Error resetting progress: {e}")
            await callback.answer("❌ Произошла ошибка при сбросе")