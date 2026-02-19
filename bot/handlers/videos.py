#!/usr/bin/env python3
"""
Handlers para vídeos do Erome Bot
"""

import asyncio
from telegram import Update
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
            await update.message.reply_text("📭 Nenhum vídeo postado ainda.")
            return

        msg = "🎬 **Últimos vídeos:**\n\n"
        for i, video in enumerate(videos, 1):
            msg += f"{i}. {video.title[:50]}...\n"

        await update.message.reply_text(msg)

    except Exception as e:
        video_logger.error(f"Erro em last_videos: {e}")
        await update.message.reply_text("❌ Erro ao buscar vídeos.")


async def post_video_to_channel(video, bot=None):
    """
    Publica um vídeo no canal - com timeout

    Args:
        video: Objeto Video do banco de dados
        bot: Instância do bot

    Returns:
        bool: True se sucesso
    """
    try:
        # Se não recebeu bot, tenta pegar da aplicação global
        if bot is None:
            from bot.main import application
            bot = application.bot

        # Verificar se arquivo existe
        video_path = Path(video.edited_path)
        if not video_path.exists():
            video_logger.error(f"Arquivo não encontrado: {video_path}")
            return False

        size_mb = video_path.stat().st_size / (1024 * 1024)
        video_logger.info(f"Enviando vídeo: {video.title[:50]} - Tamanho: {size_mb:.2f}MB")

        # Abrir arquivo de vídeo
        with open(video_path, 'rb') as video_file:
            # Criar legenda simples
            caption = f"{video.title[:100]}"

            # Enviar vídeo com timeout
            try:
                # Usar asyncio.wait_for para adicionar timeout
                await asyncio.wait_for(
                    bot.send_video(
                        chat_id=settings.TELEGRAM_CHANNEL_ID,
                        video=video_file,
                        caption=caption
                    ),
                    timeout=60  # 60 segundos de timeout
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
