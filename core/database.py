"""
مدیریت دیتابیس با SQLAlchemy
"""
from datetime import datetime
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
    echo=False,  # اگه True باشه، تمام SQL queries رو چاپ می‌کنه
    connect_args={'check_same_thread': False} if 'sqlite' in config.DATABASE_URL else {}
)

# Session factory
SessionLocal = sessionmaker(bind=engine)


# ==================== Models ====================

class User(Base):
    """مدل کاربران"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    language = Column(String(5), default='fa')
    
    # روابط
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    genres = relationship("UserGenre", back_populates="user")
    sent_tracks = relationship("SentTrack", back_populates="user")
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


class UserSettings(Base):
    """تنظیمات هر کاربر"""
    __tablename__ = 'user_settings'
    
    user_id = Column(Integer, ForeignKey('users.user_id'), primary_key=True)
    send_time = Column(String(5), default='09:00')  # فرمت HH:MM
    send_to = Column(String(10), default='private')  # private / channel
    channel_id = Column(String(100), nullable=True)
    timezone = Column(String(50), default='Asia/Tehran')
    
    # رابطه
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, send_time={self.send_time})>"


class UserGenre(Base):
    """ژانرهای انتخابی هر کاربر"""
    __tablename__ = 'user_genres'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    genre = Column(String(50))
    priority = Column(Integer, default=1)
    
    # رابطه
    user = relationship("User", back_populates="genres")
    
    def __repr__(self):
        return f"<UserGenre(user_id={self.user_id}, genre={self.genre})>"


class SentTrack(Base):
    """تاریخچه آهنگ‌های ارسال شده"""
    __tablename__ = 'sent_tracks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    track_id = Column(String(100))  # Spotify ID
    track_name = Column(String(200))
    artist = Column(String(200))
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # رابطه
    user = relationship("User", back_populates="sent_tracks")
    
    def __repr__(self):
        return f"<SentTrack(track_name={self.track_name}, artist={self.artist})>"


class TrackCache(Base):
    """کش موقت برای اطلاعات موزیک"""
    __tablename__ = 'track_cache'
    
    track_id = Column(String(100), primary_key=True)
    track_data = Column(Text)  # JSON string
    lyrics = Column(Text, nullable=True)
    cached_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrackCache(track_id={self.track_id})>"


# ==================== Helper Functions ====================

def init_db():
    """ساخت تمام جداول"""
    Base.metadata.create_all(bind=engine)
    print("✅ دیتابیس با موفقیت ساخته شد")


def get_db():
    """دریافت یک session برای کار با دیتابیس"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_user(user_id: int, username: str = None, first_name: str = None):
    """یافتن یا ساخت کاربر جدید"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user:
            # ساخت کاربر جدید
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            db.add(user)
            
            # ساخت تنظیمات پیش‌فرض
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            
            db.commit()
            print(f"✅ کاربر جدید ساخته شد: {user_id}")
        else:
            # به‌روزرسانی اطلاعات
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            db.commit()
        
        return user
    finally:
        db.close()


def get_user_genres(user_id: int) -> list:
    """گرفتن ژانرهای کاربر"""
    db = SessionLocal()
    try:
        genres = db.query(UserGenre).filter(UserGenre.user_id == user_id).all()
        return [g.genre for g in genres]
    finally:
        db.close()


def save_user_genre(user_id: int, genre: str):
    """ذخیره ژانر انتخابی کاربر"""
    db = SessionLocal()
    try:
        # حذف ژانرهای قبلی (فرض می‌کنیم فقط یک ژانر)
        db.query(UserGenre).filter(UserGenre.user_id == user_id).delete()
        
        # ذخیره ژانر جدید
        user_genre = UserGenre(user_id=user_id, genre=genre)
        db.add(user_genre)
        db.commit()
        print(f"✅ ژانر {genre} برای کاربر {user_id} ذخیره شد")
    finally:
        db.close()


if __name__ == "__main__":
    # تست: ساخت دیتابیس
    init_db()
    print("✅ تمام جداول ساخته شدند")