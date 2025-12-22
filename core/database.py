"""
مدیریت دیتابیس با SQLAlchemy
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, 
    DateTime, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from core.config import config

# Base برای تمام مدل‌ها
Base = declarative_base()

# ساخت Engine
engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    connect_args={'check_same_thread': False} if 'sqlite' in config.DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# ==================== Models ====================

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    language = Column(String(5), default='fa')
    
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    genres = relationship("UserGenre", back_populates="user")
    sent_tracks = relationship("SentTrack", back_populates="user")


class UserSettings(Base):
    __tablename__ = 'user_settings'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    send_time = Column(String(5), default='09:00')
    send_to = Column(String(10), default='private')
    channel_id = Column(String(50), nullable=True)
    timezone = Column(String(50), default='Asia/Tehran')
    
    user = relationship("User", back_populates="settings")


class UserGenre(Base):
    __tablename__ = 'user_genres'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    genre = Column(String(50), primary_key=True)
    
    user = relationship("User", back_populates="genres")


class SentTrack(Base):
    __tablename__ = 'sent_tracks'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    track_id = Column(String(100))
    track_name = Column(String(200))
    artist = Column(String(200))
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sent_tracks")


class TrackCache(Base):
    """کش اطلاعات آهنگ‌ها (برای lyrics و...)"""
    __tablename__ = 'track_cache'
    
    track_id = Column(String(100), primary_key=True)  # Spotify ID
    track_data = Column(Text, nullable=True)  # JSON اطلاعات آهنگ
    lyrics = Column(Text, nullable=True)  # متن آهنگ
    cached_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Functions ====================

def init_db():
    """ساخت تمام جداول"""
    Base.metadata.create_all(bind=engine)
    print("✅ دیتابیس با موفقیت ساخته شد")


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
                first_name=first_name
            )
            db.add(user)
            
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            
            db.commit()
            print(f"✅ کاربر جدید ساخته شد: {user_id}")
        else:
            # به‌روزرسانی اطلاعات
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            db.commit()
        
        return user
    finally:
        db.close()


def get_user_genres(user_id: int) -> list:
    """دریافت ژانرهای کاربر"""
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        return [g.genre for g in genres]
    finally:
        db.close()


def save_user_genre(user_id: int, genre: str):
    """ذخیره ژانر کاربر (تک‌تایی)"""
    db = SessionLocal()
    try:
        # حذف ژانرهای قبلی
        db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
        
        # اضافه کردن ژانر جدید
        user_genre = UserGenre(user_id=user_id, genre=genre)
        db.add(user_genre)
        db.commit()
        print(f"✅ ژانر {genre} برای کاربر {user_id} ذخیره شد")
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
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("✅ تمام جداول ساخته شدند")