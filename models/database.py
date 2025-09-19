from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Уровень и прогресс
    level = Column(String(5), default="A1")  # A1, A2, B1, B2, C1, C2
    topics = Column(JSON, default=list)  # ["work", "travel", "food"]
    total_points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    words_learned = Column(Integer, default=0)
    
    # Подписка и платежи
    is_premium = Column(Boolean, default=False)
    subscription_end = Column(DateTime)
    free_month_used = Column(Boolean, default=False)
    total_paid = Column(Float, default=0.0)
    
    # Настройки уведомлений
    notifications_enabled = Column(Boolean, default=True)
    morning_time = Column(String(5), default="09:00")
    evening_time = Column(String(5), default="19:00")
    timezone = Column(String(50), default="UTC")
    
    # Метки времени
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    last_word_study = Column(DateTime)
    last_quiz = Column(DateTime)
    
    # Отношения
    user_words = relationship("UserWord", back_populates="user")
    progress_records = relationship("UserProgress", back_populates="user")
    quiz_results = relationship("UserQuizResult", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), nullable=False, index=True)
    transcription = Column(String(255))
    translation = Column(String(255), nullable=False)
    definition = Column(Text)
    example = Column(Text)
    level = Column(String(5), nullable=False, index=True)
    topic = Column(String(100), index=True)
    frequency_rank = Column(Integer)  # Частота использования
    audio_url = Column(String(500))
    image_url = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    user_words = relationship("UserWord", back_populates="word")

class UserWord(Base):
    __tablename__ = "user_words"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    
    # Система интервальных повторений
    stage = Column(Integer, default=0)  # 0,1,2,3,4,5 (этапы повторения)
    next_repeat = Column(DateTime, default=datetime.utcnow)
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    easiness_factor = Column(Float, default=2.5)  # Для алгоритма SM-2
    
    # Время изучения
    learned_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    total_reviews = Column(Integer, default=0)
    
    # Отношения
    user = relationship("User", back_populates="user_words")
    word = relationship("Word", back_populates="user_words")

class Quiz(Base):
    __tablename__ = "quizzes"
    
    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # ["option1", "option2", "option3", "option4"]
    correct_answer = Column(Integer, nullable=False)  # индекс правильного ответа
    explanation = Column(Text)  # Объяснение правильного ответа
    
    level = Column(String(5), nullable=False, index=True)
    topic = Column(String(100), index=True)
    quiz_type = Column(String(50), index=True)  # "vocabulary", "grammar", "listening"
    difficulty = Column(Integer, default=1)  # 1-5
    
    word_id = Column(Integer, ForeignKey("words.id"))  # Связь со словом
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    results = relationship("UserQuizResult", back_populates="quiz")

class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Дневная статистика
    words_studied = Column(Integer, default=0)
    new_words = Column(Integer, default=0)
    words_reviewed = Column(Integer, default=0)
    quizzes_passed = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    total_answers = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    time_spent = Column(Integer, default=0)  # в минутах
    
    # Отношения
    user = relationship("User", back_populates="progress_records")

class UserQuizResult(Base):
    __tablename__ = "user_quiz_results"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    
    is_correct = Column(Boolean, nullable=False)
    selected_answer = Column(Integer, nullable=False)
    time_taken = Column(Integer)  # в секундах
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="quiz_results")
    quiz = relationship("Quiz", back_populates="results")

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(100), nullable=False)
    
    # Условия получения
    condition_type = Column(String(50), nullable=False)  # "streak", "points", "words", etc.
    condition_value = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    user_achievements = relationship("UserAchievement", back_populates="achievement")

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")