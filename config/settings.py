# config/settings_simple.py (renomeie para settings.py)
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
# Caminhos
VIDEOS_DIR = BASE_DIR / 'storage' / 'videos'
EDITED_DIR = BASE_DIR / 'storage' / 'edited'
TEMP_DIR = BASE_DIR / 'storage' / 'temp'
LOGS_DIR = BASE_DIR / 'logs'

# Limites
DAILY_VIDEO_LIMIT = 10  # Máx vídeos por dia


class Settings:
    """Configurações da aplicação - Versão simplificada"""

    def __init__(self):
        # Telegram
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')

        # Admin IDs - converte string JSON para lista
        admin_ids_str = os.getenv('ADMIN_IDS', '[]')
        try:
            self.ADMIN_IDS = json.loads(admin_ids_str)
        except:
            self.ADMIN_IDS = []

        # Database
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///erome_bot.db')
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

        # Payments
        self.PIX_KEY = os.getenv('PIX_KEY', '')
        self.PIX_NAME = os.getenv('PIX_NAME', '')
        self.PIX_CITY = os.getenv('PIX_CITY', '')
        self.MERCADO_PAGO_TOKEN = os.getenv('MERCADO_PAGO_TOKEN', None)

        # Video Settings
        self.VIDEO_CLIP_DURATION = int(os.getenv('VIDEO_CLIP_DURATION', '30'))
        self.MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', '600'))
        self.DAILY_VIDEO_LIMIT = int(os.getenv('DAILY_VIDEO_LIMIT', '10'))

        # Subscription Prices
        self.WEEKLY_PRICE = float(os.getenv('WEEKLY_PRICE', '11.00'))
        self.MONTHLY_PRICE = float(os.getenv('MONTHLY_PRICE', '25.00'))

        # Scraping
        self.SCRAPING_INTERVAL = int(os.getenv('SCRAPING_INTERVAL', '3600'))
        self.MAX_ALBUMS_PER_SCRAPE = int(
            os.getenv('MAX_ALBUMS_PER_SCRAPE', '20')
        )
        self.USER_AGENT = os.getenv(
            'USER_AGENT',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        )

        # Storage
        self.VIDEOS_DIR = Path(
            os.getenv('VIDEOS_DIR', BASE_DIR / 'storage' / 'videos')
        )
        self.EDITED_DIR = Path(
            os.getenv('EDITED_DIR', BASE_DIR / 'storage' / 'edited')
        )
        self.TEMP_DIR = Path(
            os.getenv('TEMP_DIR', BASE_DIR / 'storage' / 'temp')
        )
        self.LOGS_DIR = Path(os.getenv('LOGS_DIR', BASE_DIR / 'logs'))

        # Security
        self.SECRET_KEY = os.getenv('SECRET_KEY', '')
        self.ENCRYPTION_KEY = (
            os.getenv('ENCRYPTION_KEY', '').encode()
            if os.getenv('ENCRYPTION_KEY')
            else b''
        )

        # Environment
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'


# Instância global
settings = Settings()
