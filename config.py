import os
from dotenv import load_dotenv
from typing import Optional

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
    SUBSCRIPTION_PRICE: int = int(os.getenv("SUBSCRIPTION_PRICE", "99"))
    
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

config = Config()