from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from services.user_service import UserService
from services.word_service import WordService
from utils.database import get_db_session
from utils.helpers import get_user_level_info, get_next_level, format_progress_bar, format_time_spent
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "progress")
async def show_progress(callback: CallbackQuery):
    """Показ статистики прогресса"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            word_service = WordService(db_session)
            
            user = await user_service.get_user(callback.from_user.id)
            if not user:
                await callback.answer("❌ Пользователь не найден")
                return
            
            # Получаем статистику за последние 7 дней
            stats = await user_service.get_user_statistics(user, days=7)
            
            # Информация об уровне
            level_info = get_user_level_info(user.level)
            next_level = get_next_level(user.level)
            
            # Прогресс до следующего уровня
            level_points = {
                "A1": 0, "A2": 500, "B1": 1000, 
                "B2": 2000, "C1": 3000, "C2": 5000
            }
            
            current_threshold = level_points.get(user.level, 0)
            next_threshold = level_points.get(next_level, 5000) if next_level else 5000
            
            progress_to_next = 0
            if next_level:
                progress_to_next = min(100, 
                    ((user.total_points - current_threshold) / (next_threshold - current_threshold)) * 100
                )
            
            # Статус бесплатного месяца
            days_to_free_month = max(0, 30 - user.streak_days) if not user.free_month_used else 0
            free_month_status = "✅ Получен!" if user.free_month_used else f"{days_to_free_month} дней"
            
            # Слова готовые для повторения
            words_due = await word_service.get_words_due_for_review_count(user.id)
            
            text = f"""
📊 <b>Ваша статистика</b>

👤 <b>Общий прогресс:</b>
🎯 Уровень: {level_info['color']} {user.level} ({level_info['name']})
⭐ Очки: {user.total_points:,}
📚 Слов изучено: {user.words_learned}
🔥 Серия дней: {user.streak_days}

📈 <b>За последнюю неделю:</b>
📅 Активных дней: {stats.get('total_days_active', 0)}/7
📖 Слов изучено: {stats.get('total_words_studied', 0)}
🎯 Квизов пройдено: {stats.get('total_quizzes_passed', 0)}
⭐ Очков получено: {stats.get('total_points_earned', 0)}
🎯 Точность: {stats.get('average_accuracy', 0)}%
⏱️ Время обучения: {format_time_spent(stats.get('total_time_spent', 0))}

🆙 <b>Прогресс до {next_level or 'максимума'}:</b>
{format_progress_bar(int(progress_to_next), 100)} {progress_to_next:.1f}%

🔄 <b>Слов для повторения:</b> {words_due}
🎁 <b>До бесплатного месяца:</b> {free_month_status}
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 Детальная статистика", callback_data="detailed_stats")],
                [InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements")],
                [InlineKeyboardButton(text="📊 График активности", callback_data="activity_chart")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_progress: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "detailed_stats")
async def show_detailed_stats(callback: CallbackQuery):
    """Показ детальной статистики"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            # Статистика за разные периоды
            stats_7d = await user_service.get_user_statistics(user, days=7)
            stats_30d = await user_service.get_user_statistics(user, days=30)
            
            # Расчет среднего в день
            avg_words_day = stats_7d.get('total_words_studied', 0) / max(1, stats_7d.get('total_days_active', 1))
            avg_quizzes_day = stats_7d.get('total_quizzes_passed', 0) / max(1, stats_7d.get('total_days_active', 1))
            avg_time_day = stats_7d.get('total_time_spent', 0) / max(1, stats_7d.get('total_days_active', 1))
            
            # Тренд по сравнению с прошлым месяцем
            trend_accuracy = "📈" if stats_7d.get('average_accuracy', 0) >= stats_30d.get('average_accuracy', 0) else "📉"
            
            text = f"""
📈 <b>Детальная статистика</b>

📊 <b>За последнюю неделю:</b>
📖 Слов в день: {avg_words_day:.1f}
🎯 Квизов в день: {avg_quizzes_day:.1f}
⏱️ Времени в день: {format_time_spent(int(avg_time_day))}
🎯 Точность: {stats_7d.get('average_accuracy', 0)}% {trend_accuracy}

📊 <b>За последний месяц:</b>
📅 Активных дней: {stats_30d.get('total_days_active', 0)}/30
📖 Всего слов: {stats_30d.get('total_words_studied', 0)}
🎯 Всего квизов: {stats_30d.get('total_quizzes_passed', 0)}
⭐ Всего очков: {stats_30d.get('total_points_earned', 0)}
🎯 Средняя точность: {stats_30d.get('average_accuracy', 0)}%

📈 <b>Динамика по дням:</b>
            """
            
            # Добавляем данные по дням
            daily_records = stats_7d.get('daily_records', [])
            for i, record in enumerate(daily_records[-7:]):  # Последние 7 дней
                date = datetime.strptime(record['date'], "%Y-%m-%d")
                day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
                words = record['words_studied']
                quizzes = record['quizzes_passed'] 
                accuracy = record['accuracy']
                
                activity_icon = "✅" if words > 0 or quizzes > 0 else "⭕"
                text += f"\n{activity_icon} {day_name} {date.strftime('%d.%m')}: {words}слов, {quizzes}квизов, {accuracy}%"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements")],
                [InlineKeyboardButton(text="◀️ К статистике", callback_data="progress")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_detailed_stats: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "achievements")
async def show_achievements(callback: CallbackQuery):
    """Показ достижений"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            # Получаем новые достижения (проверяем)
            new_achievements = await user_service.check_achievements(user)
            
            # Список всех возможных достижений
            all_achievements = [
                {"icon": "🎯", "name": "Первые шаги", "desc": "Изучить первое слово", "condition": user.words_learned >= 1},
                {"icon": "🔥", "name": "Неделя подряд", "desc": "7 дней активности", "condition": user.streak_days >= 7},
                {"icon": "🏆", "name": "Месяц подряд", "desc": "30 дней активности", "condition": user.streak_days >= 30},
                {"icon": "📚", "name": "Знаток слов", "desc": "100 изученных слов", "condition": user.words_learned >= 100},
                {"icon": "🎓", "name": "Мастер слов", "desc": "500 изученных слов", "condition": user.words_learned >= 500},
                {"icon": "⭐", "name": "Первая тысяча", "desc": "1000 очков", "condition": user.total_points >= 1000},
                {"icon": "💎", "name": "Десять тысяч", "desc": "10000 очков", "condition": user.total_points >= 10000},
                {"icon": "🎁", "name": "Бесплатный месяц", "desc": "Получен за активность", "condition": user.free_month_used}
            ]
            
            # Разделяем на полученные и будущие
            earned = [a for a in all_achievements if a["condition"]]
            upcoming = [a for a in all_achievements if not a["condition"]]
            
            text = "🏆 <b>Достижения</b>\n\n"
            
            if earned:
                text += "✅ <b>Получено:</b>\n"
                for achievement in earned:
                    text += f"{achievement['icon']} {achievement['name']} - {achievement['desc']}\n"
                text += "\n"
            
            if upcoming:
                text += "⏳ <b>В процессе:</b>\n"
                for achievement in upcoming[:5]:  # Показываем только ближайшие 5
                    # Добавляем прогресс для некоторых достижений
                    progress = ""
                    if "слов" in achievement["desc"]:
                        target = 100 if "100" in achievement["desc"] else 500
                        progress = f" ({user.words_learned}/{target})"
                    elif "дней" in achievement["desc"]:
                        target = 7 if "7" in achievement["desc"] else 30
                        progress = f" ({user.streak_days}/{target})"
                    elif "очков" in achievement["desc"]:
                        target = 1000 if "1000" in achievement["desc"] else 10000
                        progress = f" ({user.total_points:,}/{target:,})"
                    
                    text += f"{achievement['icon']} {achievement['name']}{progress}\n"
            
            if new_achievements:
                text += f"\n🎉 <b>Новые достижения получены:</b> {len(new_achievements)}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 Статистика", callback_data="detailed_stats")],
                [InlineKeyboardButton(text="◀️ К прогрессу", callback_data="progress")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_achievements: {e}")
            await callback.answer("❌ Произошла ошибка")

@router.callback_query(F.data == "activity_chart")
async def show_activity_chart(callback: CallbackQuery):
    """Показ графика активности"""
    async for db_session in get_db_session():
        try:
            user_service = UserService(db_session)
            user = await user_service.get_user(callback.from_user.id)
            
            stats = await user_service.get_user_statistics(user, days=30)
            daily_records = stats.get('daily_records', [])
            
            # Создаем простой текстовый график активности
            text = "📊 <b>График активности (30 дней)</b>\n\n"
            
            # Группируем по неделям
            weeks = []
            current_week = []
            
            for record in daily_records[-30:]:
                current_week.append(record)
                if len(current_week) == 7:
                    weeks.append(current_week)
                    current_week = []
            
            if current_week:  # Добавляем неполную неделю
                weeks.append(current_week)
            
            week_names = ["1 неделя назад", "2 недели назад", "3 недели назад", "4 недели назад", "Эта неделя"]
            
            for i, week in enumerate(weeks[-5:]):  # Последние 5 недель
                week_name = week_names[min(i, len(week_names)-1)]
                text += f"📅 <b>{week_name}:</b>\n"
                
                for day in week:
                    date = datetime.strptime(day['date'], "%Y-%m-%d")
                    day_short = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date.weekday()]
                    
                    # Определяем уровень активности
                    activity_level = day['words_studied'] + day['quizzes_passed']
                    if activity_level >= 10:
                        activity_icon = "🟢"  # Высокая активность
                    elif activity_level >= 5:
                        activity_icon = "🟡"  # Средняя активность
                    elif activity_level > 0:
                        activity_icon = "🟠"  # Низкая активность
                    else:
                        activity_icon = "⚪"  # Нет активности
                    
                    text += f"{activity_icon} {day_short} "
                
                text += "\n\n"
            
            text += """
🟢 Высокая активность (10+ действий)
🟡 Средняя активность (5-9 действий)  
🟠 Низкая активность (1-4 действия)
⚪ Нет активности

💡 <b>Совет:</b> Старайтесь поддерживать зеленый и желтый уровни!
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements")],
                [InlineKeyboardButton(text="◀️ К прогрессу", callback_data="progress")]
            ])
            
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in show_activity_chart: {e}")
            await callback.answer("❌ Произошла ошибка")