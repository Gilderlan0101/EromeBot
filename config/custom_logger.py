"""
Sistema de Logging do Erome Bot
Módulo logging padrão do Python com formatação colorida e níveis detalhados
"""

import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
import colorama
from colorama import Fore, Style

# Inicializar colorama
colorama.init()

# Configurar formatos
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
LOG_FORMAT_COLORED = (
    f'{Fore.GREEN}%(asctime)s{Style.RESET_ALL} | '
    f'%(levelname_colored)-8s | '
    f'{Fore.CYAN}%(name)s{Style.RESET_ALL}:'
    f'{Fore.CYAN}%(funcName)s{Style.RESET_ALL}:'
    f'{Fore.CYAN}%(lineno)d{Style.RESET_ALL} | '
    f'%(message_colored)s'
)

LEVEL_COLORS = {
    'DEBUG': Fore.CYAN,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED + Style.BRIGHT,
}


class ColoredFormatter(logging.Formatter):
    """Formatter personalizado para adicionar cores aos logs"""

    def __init__(self):
        super().__init__()
        # Garantir que o asctime seja formatado
        self.default_time_format = '%Y-%m-%d %H:%M:%S'
        self.default_msec_format = '%s.%03d'

    def format(self, record):
        # Criar cópia do record para não modificar o original
        record = logging.makeLogRecord(record.__dict__)

        # Garantir que asctime existe
        if not hasattr(record, 'asctime'):
            record.asctime = self.formatTime(record, self.datefmt)

        # Adicionar cor ao nível
        levelname = record.levelname
        if levelname in LEVEL_COLORS:
            record.levelname_colored = (
                f'{LEVEL_COLORS[levelname]}{levelname}{Style.RESET_ALL}'
            )
        else:
            record.levelname_colored = levelname

        # Adicionar cor à mensagem
        if levelname in LEVEL_COLORS:
            record.message_colored = f'{LEVEL_COLORS[levelname]}{record.getMessage()}{Style.RESET_ALL}'
        else:
            record.message_colored = record.getMessage()

        # Formatar a mensagem
        return LOG_FORMAT_COLORED % record.__dict__


# Logger principal
_logger = None

# Loggers especializados (serão inicializados depois)
payment_logger = None
scraping_logger = None
video_logger = None
bot_logger = None
db_logger = None


def setup_logger(
    log_dir: str = 'logs', rotation: str = '500 MB', retention: str = '30 days'
):
    """
    Configura o logger com saída para console e arquivo
    """
    global _logger, payment_logger, scraping_logger, video_logger, bot_logger, db_logger

    # Criar logger
    _logger = logging.getLogger('erome_bot')
    _logger.setLevel(logging.DEBUG)

    # Remover handlers existentes
    _logger.handlers.clear()

    # Criar diretório de logs
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Handler para console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColoredFormatter())
    _logger.addHandler(console_handler)

    # Handler para stderr (erros)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(ColoredFormatter())
    _logger.addHandler(stderr_handler)

    # Função para converter tamanho
    def parse_size(size_str):
        size_str = size_str.upper()
        if size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        else:
            return int(size_str)

    # Handler para arquivo geral
    general_handler = RotatingFileHandler(
        log_path / 'erome_bot.log',
        maxBytes=parse_size(rotation),
        backupCount=30,
    )
    general_handler.setLevel(logging.DEBUG)
    general_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    _logger.addHandler(general_handler)

    # Handler para erros
    errors_handler = RotatingFileHandler(
        log_path / 'errors.log', maxBytes=parse_size('100 MB'), backupCount=90
    )
    errors_handler.setLevel(logging.ERROR)
    errors_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    _logger.addHandler(errors_handler)

    # Handler para pagamentos
    payments_handler = RotatingFileHandler(
        log_path / 'payments.log',
        maxBytes=parse_size('50 MB'),
        backupCount=365,
    )
    payments_handler.setLevel(logging.INFO)
    payments_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    payments_handler.addFilter(
        lambda record: hasattr(record, 'category')
        and record.category == 'payment'
    )
    _logger.addHandler(payments_handler)

    # Handler para scraping
    scraping_handler = RotatingFileHandler(
        log_path / 'scraping.log',
        maxBytes=parse_size('100 MB'),
        backupCount=30,
    )
    scraping_handler.setLevel(logging.DEBUG)
    scraping_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    scraping_handler.addFilter(
        lambda record: hasattr(record, 'category')
        and record.category == 'scraping'
    )
    _logger.addHandler(scraping_handler)

    # Handler para vídeos
    videos_handler = RotatingFileHandler(
        log_path / 'videos.log', maxBytes=parse_size('100 MB'), backupCount=30
    )
    videos_handler.setLevel(logging.DEBUG)
    videos_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    videos_handler.addFilter(
        lambda record: hasattr(record, 'category')
        and record.category == 'video'
    )
    _logger.addHandler(videos_handler)

    # Inicializar loggers especializados
    payment_logger = logging.LoggerAdapter(_logger, {'category': 'payment'})
    scraping_logger = logging.LoggerAdapter(_logger, {'category': 'scraping'})
    video_logger = logging.LoggerAdapter(_logger, {'category': 'video'})
    bot_logger = logging.LoggerAdapter(_logger, {'category': 'bot'})
    db_logger = logging.LoggerAdapter(_logger, {'category': 'database'})

    # Banner
    banner = [
        '╔════════════════════════════════════════╗',
        '║     🤖 EROME BOT INICIADO             ║',
        '║     📊 Logs configurados com sucesso  ║',
        '╚════════════════════════════════════════╝',
    ]

    for line in banner:
        _logger.info(
            f'{Fore.GREEN}{line}{Style.RESET_ALL}',
            extra={'category': 'system'},
        )

    _logger.debug(
        f'{Fore.GREEN}✅ Loggers especializados inicializados{Style.RESET_ALL}',
        extra={'category': 'system'},
    )

    return _logger


def get_category_logger(category: str):
    """Retorna um logger com categoria específica"""
    if _logger is None:
        # Criar logger temporário
        temp_logger = logging.getLogger(f'temp_{category}')
        temp_logger.setLevel(logging.DEBUG)
        return logging.LoggerAdapter(temp_logger, {'category': category})
    return logging.LoggerAdapter(_logger, {'category': category})


# Exportar tudo
__all__ = [
    'setup_logger',
    'get_category_logger',
    'payment_logger',
    'scraping_logger',
    'video_logger',
    'bot_logger',
    'db_logger',
]
