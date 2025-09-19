import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import config
from models.database import Base
import logging

logger = logging.getLogger(__name__)

# Создание асинхронного движка
engine = create_async_engine(
    config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=config.DEBUG,
    future=True
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_database():
    """Инициализация базы данных"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

async def get_db_session():
    """Получение сессии базы данных"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_database():
    """Закрытие соединения с базой данных"""
    await engine.dispose()