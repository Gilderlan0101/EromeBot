import json
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

load_dotenv()
Base = declarative_base()


class User(Base):
    """Modelo de usuário"""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))

    # Assinatura
    is_subscribed = Column(Boolean, default=False)
    subscription_type = Column(String(20))  # 'weekly' or 'monthly'
    subscription_start = Column(DateTime)
    subscription_end = Column(DateTime)

    # Pagamentos
    total_paid = Column(Float, default=0)
    last_payment_date = Column(DateTime)

    # Status
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relacionamentos
    payments = relationship('Payment', back_populates='user')
    watched_videos = relationship('VideoWatch', back_populates='user')

    def __repr__(self):
        return f'<User {self.telegram_id} - {self.username}>'


class Video(Base):
    """Modelo de vídeo"""

    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    source_url = Column(String(500), unique=True)
    source_album = Column(String(500))
    title = Column(String(500))
    description = Column(Text)
    duration = Column(Integer)  # em segundos
    size_mb = Column(Float)
    resolution = Column(String(20))

    # Arquivos
    original_path = Column(String(500))
    edited_path = Column(String(500))
    thumbnail_path = Column(String(500))

    # Clipes (para vídeos longos)
    clip_count = Column(Integer, default=1)
    clip_durations = Column(String(100))  # JSON string com durações dos clipes

    # Metadados
    source = Column(String(50))  # 'erome', 'other'
    username = Column(String(100))
    views = Column(Integer, default=0)
    tags = Column(String(500))  # JSON string

    # Status
    is_processed = Column(Boolean, default=False)
    is_posted = Column(Boolean, default=False)
    posted_at = Column(DateTime)
    error_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    watches = relationship('VideoWatch', back_populates='video')

    @property
    def clip_list(self):
        """Retorna lista de durações dos clipes"""
        if self.clip_durations:
            return json.loads(self.clip_durations)
        return []

    def __repr__(self):
        return f'<Video {self.id} - {self.title[:30]}>'


class Payment(Base):
    """Modelo de pagamento"""

    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='payments')

    # Transação
    transaction_id = Column(String(100), unique=True)
    pix_code = Column(String(500))
    qr_code_path = Column(String(500))

    # Valores
    amount = Column(Float)
    period_type = Column(String(20))  # 'weekly' or 'monthly'

    # Status
    status = Column(
        String(20), default='pending'
    )  # pending, paid, expired, cancelled
    paid_at = Column(DateTime)
    expires_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Payment {self.transaction_id} - {self.status}>'


class VideoWatch(Base):
    """Registro de visualização de vídeo"""

    __tablename__ = 'video_watches'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    video_id = Column(Integer, ForeignKey('videos.id'))

    user = relationship('User', back_populates='watched_videos')
    video = relationship('Video', back_populates='watches')

    watched_at = Column(DateTime, default=datetime.utcnow)
    clip_index = Column(Integer, default=0)  # qual clipe foi assistido

    def __repr__(self):
        return f'<Watch User:{self.user_id} Video:{self.video_id}>'


class ScrapeLog(Base):
    """Log de scraping"""

    __tablename__ = 'scrape_logs'

    id = Column(Integer, primary_key=True)
    source = Column(String(50))
    albums_found = Column(Integer, default=0)
    videos_found = Column(Integer, default=0)
    videos_new = Column(Integer, default=0)
    errors = Column(Text)
    duration = Column(Float)  # segundos

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ScrapeLog {self.created_at} - {self.videos_new} novos>'


# Criar engine e sessão
def init_db(
    database_url: Optional[str] = os.getenv(
        'DATABASE_URL', 'sqlite:///erome_bot.db'
    )
):
    engine = create_engine(str(database_url))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
