"""
مدیریت دیتابیس با SQLAlchemy - پشتیبانی PostgreSQL + SQLite
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, 
    DateTime, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path
from core.config import config

# Base برای تمام مدل‌ها
Base = declarative_base()


def get_database_url():
    """تعیین URL دیتابیس بر اساس محیط"""
    db_url = config.DATABASE_URL
    
    # اگر SQLite باشه، مطمئن شو که path درست است
    if db_url.startswith('sqlite'):
        # برای Docker/Render از /app/data استفاده کن
        if os.path.exists('/app'):
            data_dir = Path('/app/data')
            data_dir.mkdir(exist_ok=True, parents=True)
            db_url = f'sqlite:///{data_dir}/music_bot.db'
        else:
            # برای local
            db_url = 'sqlite:///music_bot.db'
    
    return db_url


# ساخت Engine
DATABASE_URL = get_database_url()

# تنظیمات مخصوص SQLite
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={
            'check_same_thread': False,
            'timeout': 30  # افزایش timeout
        },
        poolclass=StaticPool  # مهم برای SQLite در Docker
    )
else:
    # PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,  # چک کردن connection قبل از استفاده
        pool_size=10,
        max_overflow=20
    )

# Session factory
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# ==================== Models ====================

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    language = Column(String(5), default='fa')
    
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    genres = relationship("UserGenre", back_populates="user", cascade="all, delete-orphan")
    sent_tracks = relationship("SentTrack", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = 'user_settings'
    
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    send_time = Column(String(5), default='09:00')
    send_to = Column(String(10), default='private')
    channel_id = Column(String(50), nullable=True)
    timezone = Column(String(50), default='Asia/Tehran')
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="settings")


class UserGenre(Base):
    __tablename__ = 'user_genres'
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # اضافه کردن ID
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'))
    genre = Column(String(50), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="genres")
    
    # Index برای بهبود performance
    __table_args__ = (
        {'sqlite_autoincrement': True}
    ,)


class SentTrack(Base):
    __tablename__ = 'sent_tracks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'))
    track_id = Column(String(100), nullable=False)
    track_name = Column(String(200))
    artist = Column(String(200))
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sent_tracks")


class LyricsCache(Base):
    __tablename__ = 'lyrics_cache'
    
    spotify_id = Column(String(100), primary_key=True)
    lyrics = Column(Text, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """ساخت تمام جداول"""
    try:
        Base.metadata.create_all(engine)
        print(f"✅ دیتابیس راه‌اندازی شد: {DATABASE_URL}")
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی دیتابیس: {e}")
        raise


def get_or_create_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None
) -> User:
    """یافتن یا ساخت کاربر جدید"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name,
                is_active=True
            )
            db.add(user)
            
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            
            db.commit()
            db.refresh(user)
            print(f"✅ کاربر جدید ساخته شد: {user_id}")
        else:
            # به‌روزرسانی اطلاعات
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            
            if updated:
                db.commit()
                db.refresh(user)
        
        return user
    except Exception as e:
        db.rollback()
        print(f"❌ خطا در get_or_create_user: {e}")
        raise
    finally:
        db.close()


def get_user_genres(user_id: int) -> list:
    """دریافت ژانرهای کاربر"""
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        return [g.genre for g in genres]
    except Exception as e:
        print(f"❌ خطا در get_user_genres: {e}")
        return []
    finally:
        db.close()


def save_user_genres(user_id: int, genres: list):
    """ذخیره چندین ژانر"""
    db = SessionLocal()
    try:
        # حذف ژانرهای قبلی
        db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
        
        # اضافه کردن ژانرهای جدید
        for genre in genres:
            db.add(UserGenre(user_id=user_id, genre=genre))
        
        db.commit()
        print(f"✅ {len(genres)} ژانر برای کاربر {user_id} ذخیره شد")
    except Exception as e:
        db.rollback()
        print(f"❌ خطا در save_user_genres: {e}")
        raise
    finally:
        db.close()


def check_database_health():
    """چک کردن سلامت دیتابیس"""
    try:
        db = SessionLocal()
        result = db.execute("SELECT 1").fetchone()
        db.close()
        print("✅ دیتابیس سالم است")
        return True
    except Exception as e:
        print(f"❌ مشکل در دیتابیس: {e}")
        return False


if __name__ == "__main__":
    print(f"🗄️ Database URL: {DATABASE_URL}")
    init_db()
    print("✅ تمام جداول ساخته شدند")
    check_database_health()