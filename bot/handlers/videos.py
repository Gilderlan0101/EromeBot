from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config.constants import START_MESSAGE
from database.models import init_db
from database.models import User
from bot.keyboards.inline import get_main_keyboard





async def last_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mensagens de texto não-comando"""
    text = update.message.text.lower()

    if text in ['planos', '💰 planos', 'assinatura']:
        from .subscription import show_plans

        await show_plans(update, context)
    elif text in ['status', '📊 status', 'minha conta']:
        from .subscription import check_status

        await check_status(update, context)
    elif text in ['últimos', '🎬 últimos', 'vídeos']:
        await last_videos(update, context)
    else:
        await update.message.reply_text(
            'Use /start para ver as opções disponíveis!'
        )
