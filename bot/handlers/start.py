import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot.keyboards.inline import get_main_keyboard
from config.constants import START_MESSAGE
from database.models import User, init_db


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do comando /start"""
    user = update.effective_user

    # Registrar/atualizar usuário no banco
    session = init_db()
    try:
        db_user = session.query(User).filter_by(telegram_id=user.id).first()

        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            session.add(db_user)
            session.commit()
            logging.info(f'Novo usuário: {user.id} - {user.first_name}')

    except Exception as e:
        logging.error(f'Erro ao registrar usuário: {e}')
    finally:
        session.close()

    # Mensagem de boas-vindas
    welcome_msg = f"""
🎬 *Bem-vindo, {user.first_name}!*

{START_MESSAGE}
    """

    # Teclado principal
    keyboard = get_main_keyboard()

    await update.message.reply_text(
        welcome_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do comando /help"""
    help_text = """
❓ *Ajuda - Erome Bot*

*Comandos disponíveis:*
/start - Iniciar o bot
/planos - Ver planos de assinatura
/status - Ver status da sua assinatura
/ultimos - Ver últimos vídeos postados
/help - Esta mensagem

*Como funciona:*
1️⃣ Escolha um plano (semanal ou mensal)
2️⃣ Pague via PIX
3️⃣ Receba acesso ao canal VIP
4️⃣ Vídeos novos todo dia!

*Dúvidas?* Entre em contato com @admin
    """

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mensagens de texto não-comando"""
    text = update.message.text.lower()

    if text in ['planos', '💰 planos', 'assinatura']:
        from .subscription import show_plans

        await show_plans(update, context)
    elif text in ['status', '📊 status', 'minha conta']:
        from .subscription import check_status

        await check_status(update, context)
    elif text in ['últimos vídeos', '🎬 vídeos', 'videos']:
        from .videos import last_videos

        await last_videos(update, context)
    else:
        await update.message.reply_text(
            'Use /start para ver as opções disponíveis!'
        )
