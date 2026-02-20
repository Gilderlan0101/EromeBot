#!/usr/bin/env python3
"""
Handlers para comandos de start e mensagens gerais
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config.custom_logger import bot_logger
from config.settings import settings
from database.models import User, init_db


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para comando /start
    Mostra menu principal com botões
    """
    user = update.effective_user
    bot_logger.info(f'✅ Usuário {user.id} iniciou o bot')

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
            bot_logger.info(f'📝 Novo usuário registrado: {user.id}')
    except Exception as e:
        bot_logger.error(f'Erro ao registrar usuário: {e}')
    finally:
        session.close()

    # Mensagem de boas-vindas
    welcome_text = f"""
🎉 *BEM-VINDO AO EROME BOT!* 🎉

👋 Olá {user.first_name}!

🤖 *O que eu posso fazer por você:*
• 📹 Postar vídeos automaticamente no grupo
• 💰 Gerenciar assinaturas via PIX
• 🔄 Atualizações diárias de conteúdo

👇 *Escolha uma opção abaixo:*
    """

    # Criar teclado com botões
    keyboard = [
        [
            InlineKeyboardButton("💎 VER PLANOS", callback_data="sub_show_plans"),
        ],
        [
            InlineKeyboardButton("❓ SUPORTE", url="https://t.me/lunaSafe_bot"),
        ],
        [
            InlineKeyboardButton("📊 MEU STATUS", callback_data="sub_check_status"),
            InlineKeyboardButton("🎬 ÚLTIMOS VÍDEOS", callback_data="last_videos"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para comando /help"""
    help_text = """
❓ *AJUDA - EROME BOT*

📌 *Comandos disponíveis:*
/start - Menu principal
/planos - Ver planos de assinatura
/status - Status da sua assinatura
/ultimos - Últimos vídeos postados
/ping - Testar conexão

💡 *Dúvidas?* Entre em contato com @lunaSafe_bot

🎯 *Grupo oficial:* @xnovinhashot
    """

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler para mensagens de texto que não são comandos
    """
    user = update.effective_user
    message = update.message.text

    bot_logger.info(f'Mensagem de {user.id}: {message[:50]}')

    # Resposta padrão para mensagens não reconhecidas
    response = """
🤔 *Não entendi seu comando.*

Use /start para ver o menu principal
ou /help para lista de comandos.
    """

    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
