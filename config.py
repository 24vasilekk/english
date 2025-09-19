import os
from dotenv import load_dotenv
from typing import Optional, List

load_dotenv()

class Config:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL")
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://english_user:password123@localhost:5432/english_bot")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "english_bot")
    DB_USER: str = os.getenv("DB_USER", "english_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password123")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Payment
    PAYMENT_TOKEN: str = os.getenv("PAYMENT_TOKEN", "")
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "0"))  # Сделали 0 для бесплатного режима
    
    # Application
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Audio
    AUDIO_ENABLED: bool = os.getenv("AUDIO_ENABLED", "True").lower() == "true"
    TTS_LANGUAGE: str = os.getenv("TTS_LANGUAGE", "en")
    
    # Notifications
    MORNING_TIME: str = os.getenv("MORNING_TIME", "09:00")
    EVENING_TIME: str = os.getenv("EVENING_TIME", "19:00")
    
    # Free trial
    FREE_TRIAL_DAYS: int = 3
    FREE_MONTH_STREAK: int = 30
    
    # 🔧 АДМИН НАСТРОЙКИ
    # Ваш Telegram ID для админ доступа
    ADMIN_IDS: List[int] = [1240742785]  # Ваш ID добавлен!
    
    # 🎁 БЕСПЛАТНЫЙ РЕЖИМ (временно для тестирования)
    FREE_MODE: bool = True  # Все функции бесплатны
    
    # Дополнительные админ функции
    SUPER_ADMIN_ID: int = 1240742785  # Главный админ (вы)
    
    # Настройки для разработки
    DEVELOPMENT_MODE: bool = True
    SKIP_PAYMENTS: bool = True  # Пропускаем проверку платежей
    
    # Настройки контента
    MAX_DAILY_WORDS: int = 100  # Максимум слов в день для обычных пользователей
    MAX_DAILY_QUIZZES: int = 100  # Максимум квизов в день
    
    # Админ имеет безлимит
    ADMIN_UNLIMITED: bool = True

# Создаем объект конфигурации
config = Config()

# 🛡️ Функции проверки прав доступа
def is_admin(user_id: int) -> bool:
    """Проверка админских прав"""
    return user_id in config.ADMIN_IDS

def is_super_admin(user_id: int) -> bool:
    """Проверка супер-админских прав"""
    return user_id == config.SUPER_ADMIN_ID

def has_unlimited_access(user_id: int) -> bool:
    """Проверка безлимитного доступа"""
    return config.FREE_MODE or is_admin(user_id) or config.DEVELOPMENT_MODE

# 📊 Настройки для логирования админских действий
ADMIN_LOG_ENABLED: bool = True
ADMIN_COMMANDS = [
    "/admin",
    "/stats", 
    "/broadcast",
    "/add_words",
    "/user_info",
    "/reset_user",
    "/grant_premium"
]

# 🎯 Настройки геймификации
POINTS_CONFIG = {
    "correct_answer": 10,
    "word_learned": 5,
    "daily_bonus": 50,
    "streak_multipliers": {
        7: 1.5,   # 7 дней = x1.5
        14: 2.0,  # 14 дней = x2
        30: 3.0   # 30 дней = x3
    }
}

# 🏆 Настройки достижений  
ACHIEVEMENTS_CONFIG = {
    "first_word": {"type": "words", "value": 1, "points": 50},
    "week_streak": {"type": "streak", "value": 7, "points": 100},
    "month_streak": {"type": "streak", "value": 30, "points": 500},
    "word_master": {"type": "words", "value": 100, "points": 1000},
    "quiz_master": {"type": "quizzes", "value": 100, "points": 500}
}

# 🔔 Настройки уведомлений
NOTIFICATION_CONFIG = {
    "morning_enabled": True,
    "evening_enabled": True,
    "achievement_notifications": True,
    "streak_warnings": True,  # Предупреждения о потере серии
    "subscription_reminders": False  # Выключено в бесплатном режиме
}

# 🎨 Настройки интерфейса
UI_CONFIG = {
    "show_premium_features": False,  # Скрываем премиум в бесплатном режиме
    "show_subscription_menu": False,
    "enable_payment_buttons": False,
    "admin_debug_info": True  # Показывать отладочную информацию админам
}

# 📈 Лимиты для обычных пользователей (админы игнорируют)
USER_LIMITS = {
    "daily_words": 50,
    "daily_quizzes": 50,
    "daily_points": 1000
}

# 🔧 Режимы работы
OPERATION_MODES = {
    "free_for_all": config.FREE_MODE,
    "admin_only": False,
    "maintenance": False,
    "beta_testing": True
}

print(f"🚀 Config loaded successfully!")
print(f"📋 Admin IDs: {config.ADMIN_IDS}")
print(f"🎁 Free Mode: {config.FREE_MODE}")
print(f"🔧 Development Mode: {config.DEVELOPMENT_MODE}")
if config.DEBUG:
    print(f"🐛 Debug mode enabled")
    print(f"👑 Super Admin: {config.SUPER_ADMIN_ID}")