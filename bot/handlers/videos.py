#!/usr/bin/env python3
"""
Handlers para vídeos do Erome Bot
path: bot/handlers/videos.py
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from pathlib import Path

from config.settings import settings
from config.custom_logger import video_logger
from database.models import init_db, Video


async def last_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os últimos vídeos postados"""
    try:
        session = init_db()
        videos = session.query(Video).filter_by(is_posted=True).order_by(Video.posted_at.desc()).limit(5).all()
        session.close()

        if not videos:
            # Verificar se é callback ou mensagem
            if update.callback_query:
                await update.callback_query.edit_message_text("📭 Nenhum vídeo postado ainda.")
            else:
                await update.message.reply_text("📭 Nenhum vídeo postado ainda.")
            return

        msg = "🎬 **Últimos vídeos:**\n\n"
        for i, video in enumerate(videos, 1):
            msg += f"{i}. {video.title[:50]}...\n"

        # Adicionar botão de voltar
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data="sub_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Verificar se é callback ou mensagem
        if update.callback_query:
            await update.callback_query.edit_message_text(
                msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                msg,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    except Exception as e:
        video_logger.error(f"Erro em last_videos: {e}")
        error_msg = "❌ Erro ao buscar vídeos."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


async def last_videos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para mostrar últimos vídeos"""
    query = update.callback_query
    await query.answer()

    # Reutilizar a função existente
    await last_videos(update, context)


async def post_video_to_channel(video, bot=None):
    """
    Publica um vídeo no canal com título padrão e botões
    """
    try:
        # Se não recebeu bot, tenta pegar da aplicação global
        if bot is None:
            from bot.main import application
            bot = application.bot  # CORREÇÃO: usar application.bot, não application direto

        if not video.edited_path:
            video_logger.error(f"Vídeo {video.id} não tem caminho editado")
            return False

        # Verificar se arquivo existe
        video_path = Path(video.edited_path)
        if not video_path.exists():
            # Tentar encontrar em storage/edited/
            filename = Path(video.edited_path).name
            alternative_path = settings.EDITED_DIR / filename

            if alternative_path.exists():
                video_logger.info(f"Usando caminho alternativo: {alternative_path}")
                video_path = alternative_path
            else:
                video_logger.error(f"Arquivo não encontrado: {video_path} nem {alternative_path}")
                return False

        size_mb = video_path.stat().st_size / (1024 * 1024)
        video_logger.info(f"Enviando vídeo: {video.title[:50]} - Tamanho: {size_mb:.2f}MB")

        # Título padrão
        titulo = f"🔥 {video.title[:50]} 🔥"

        # Mensagem padrão
        mensagem = (
            f"{titulo}\n\n"
            f"📱 **Conteúdo completo no grupo VIP!** 🎬\n\n"
            f"👇 Clique nos botões abaixo para acessar:\n\n"
        )

        # Criar botões - CORREÇÃO das URLs
        keyboard = [
            [
                InlineKeyboardButton("🇧🇷 Grupo VIP Português", url="https://t.me/lunaSafe_bot")
            ],
            [
                InlineKeyboardButton("🇺🇸 VIP Group English", url="https://t.me/lunaSafe_bot")
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Abrir arquivo de vídeo
        with open(video_path, 'rb') as video_file:
            # Enviar vídeo com a mensagem e botões
            try:
                await asyncio.wait_for(
                    bot.send_video(
                        chat_id=settings.TELEGRAM_CHANNEL_ID,
                        video=video_file,
                        caption=mensagem,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    ),
                    timeout=60
                )

                video_logger.info(f"✅ Vídeo postado com sucesso: {video.title[:50]}")
                return True

            except asyncio.TimeoutError:
                video_logger.error(f"❌ Timeout ao enviar vídeo (60s): {video.title[:50]}")
                return False

    except Exception as e:
        video_logger.error(f"❌ Erro ao postar vídeo: {e}")
        return False


async def handle_video_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder para ações de vídeo"""
    query = update.callback_query
    await query.answer("🚧 Em desenvolvimento")
