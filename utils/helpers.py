import re
from datetime import datetime, timedelta
from typing import List, Optional
import random
import string

def validate_time_format(time_str: str) -> bool:
    """Проверка формата времени HH:MM"""
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def calculate_next_review(stage: int, easiness_factor: float = 2.5) -> datetime:
    """Расчет следующего повторения по алгоритму интервальных повторений"""
    intervals = {
        0: 1,      # 1 день
        1: 3,      # 3 дня  
        2: 7,      # 1 неделя
        3: 21,     # 3 недели
        4: 60,     # 2 месяца
        5: 180     # 6 месяцев
    }
    
    base_interval = intervals.get(stage, 180)
    actual_interval = int(base_interval * easiness_factor)
    
    return datetime.utcnow() + timedelta(days=actual_interval)

def update_easiness_factor(current_factor: float, is_correct: bool, difficulty: int = 3) -> float:
    """Обновление коэффициента легкости для алгоритма SM-2"""
    if is_correct:
        new_factor = current_factor + (0.1 - (5 - difficulty) * (0.08 + (5 - difficulty) * 0.02))
    else:
        new_factor = current_factor - 0.2
    
    return max(1.3, new_factor)

def get_level_points_threshold(level: str) -> int:
    """Получение порога очков для уровня"""
    thresholds = {
        "A1": 0,
        "A2": 500,
        "B1": 1000,
        "B2": 2000,
        "C1": 3000,
        "C2": 5000
    }
    return thresholds.get(level, 0)

def get_next_level(current_level: str) -> Optional[str]:
    """Получение следующего уровня"""
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    try:
        current_index = levels.index(current_level)
        return levels[current_index + 1] if current_index < len(levels) - 1 else None
    except ValueError:
        return "A2"

def format_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """Создание прогресс-бара"""
    if maximum == 0:
        return "░" * length
    
    filled = int((current / maximum) * length)
    return "▓" * filled + "░" * (length - filled)

def generate_quiz_options(correct_answer: str, wrong_options: List[str], count: int = 4) -> tuple:
    """Генерация вариантов ответов для квиза"""
    if len(wrong_options) < count - 1:
        # Добавляем случайные варианты если не хватает
        additional_needed = count - 1 - len(wrong_options)
        for _ in range(additional_needed):
            wrong_options.append(f"Вариант {random.randint(1, 100)}")
    
    # Берем нужное количество неправильных ответов
    selected_wrong = random.sample(wrong_options, min(count - 1, len(wrong_options)))
    
    # Создаем список всех вариантов
    all_options = [correct_answer] + selected_wrong
    random.shuffle(all_options)
    
    # Находим индекс правильного ответа
    correct_index = all_options.index(correct_answer)
    
    return all_options, correct_index

def calculate_streak_bonus(streak_days: int) -> float:
    """Расчет бонусного множителя за серию дней"""
    if streak_days >= 30:
        return 3.0
    elif streak_days >= 14:
        return 2.0
    elif streak_days >= 7:
        return 1.5
    else:
        return 1.0

def format_time_spent(minutes: int) -> str:
    """Форматирование времени обучения"""
    if minutes < 60:
        return f"{minutes} мин"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} ч"
        else:
            return f"{hours} ч {remaining_minutes} мин"

def clean_text(text: str) -> str:
    """Очистка текста от лишних символов"""
    # Удаляем лишние пробелы и переводы строк
    text = re.sub(r'\s+', ' ', text.strip())
    # Удаляем потенциально опасные символы
    text = re.sub(r'[<>\"\'&]', '', text)
    return text

def generate_random_string(length: int = 8) -> str:
    """Генерация случайной строки"""
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def is_premium_feature_available(user) -> bool:
    """Проверка доступности премиум функций"""
    from config import config
    
    # Если включен бесплатный режим или пользователь админ
    if getattr(config, 'FREE_MODE', False):
        return True
        
    if user.telegram_id in getattr(config, 'ADMIN_IDS', []):
        return True
        
    if not user.subscription_end:
        return False
    return user.is_premium and user.subscription_end > datetime.utcnow()

def get_user_level_info(level: str) -> dict:
    """Получение информации об уровне пользователя"""
    level_info = {
        "A1": {
            "name": "Начинающий",
            "description": "Понимаете и используете знакомые фразы",
            "words_count": 500,
            "color": "🟢"
        },
        "A2": {
            "name": "Элементарный", 
            "description": "Можете говорить на простые темы",
            "words_count": 1000,
            "color": "🔵"
        },
        "B1": {
            "name": "Средний",
            "description": "Понимаете основные идеи текстов",
            "words_count": 2000,
            "color": "🟡"
        },
        "B2": {
            "name": "Продвинутый средний",
            "description": "Понимаете сложные тексты",
            "words_count": 3000,
            "color": "🟠"
        },
        "C1": {
            "name": "Продвинутый",
            "description": "Свободно выражаете мысли",
            "words_count": 5000,
            "color": "🔴"
        },
        "C2": {
            "name": "Владение в совершенстве",
            "description": "Владеете языком на уровне носителя",
            "words_count": 8000,
            "color": "🟣"
        }
    }
    return level_info.get(level, level_info["A1"])