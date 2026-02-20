#!/usr/bin/env python3
"""
Script para processar vídeos existentes na pasta storage/videos/
Versão melhorada com tratamento de erros e Unique Constraint
"""

import asyncio
import uuid
from pathlib import Path
from datetime import datetime
import traceback

from config.custom_logger import setup_logger

# Configurar logger do projeto ANTES de outras importações
logger = setup_logger(log_dir='logs', rotation='500 MB', retention='30 days')

from config.settings import settings
from config.custom_logger import video_logger
from database.models import init_db, Video
from video_editor.editor import VideoEditor


async def process_existing_videos():
    """Processa todos os vídeos da pasta videos/ que não estão no banco"""

    editor = VideoEditor()
    session = init_db()

    try:
        # Listar todos os vídeos na pasta
        video_files = list(settings.VIDEOS_DIR.glob("*.mp4"))
        video_files = [f for f in video_files if not f.name.startswith("edited_")]
        video_logger.info(f"📁 Encontrados {len(video_files)} vídeos para processar")

        # Verificar vídeos já no banco
        existing_videos = session.query(Video.original_path).all()
        existing_paths = [str(path[0]) for path in existing_videos]

        processed = 0
        errors = 0
        skipped = 0

        for i, video_path in enumerate(video_files, 1):
            try:
                # Verificar se já está no banco
                if str(video_path) in existing_paths:
                    video_logger.info(f"⏭️  [{i}/{len(video_files)}] Vídeo já existe: {video_path.name}")
                    skipped += 1
                    continue

                video_logger.info(f"🎬 [{i}/{len(video_files)}] Processando: {video_path.name}")

                # Processar vídeo
                edited_path = await editor.process_video(video_path, video_path.stem)

                if not edited_path:
                    video_logger.error(f"❌ Falha ao processar: {video_path.name}")
                    errors += 1
                    continue

                # Verificar duplicata antes de salvar
                existing = session.query(Video).filter_by(
                    original_path=str(video_path)
                ).first()

                if existing:
                    video_logger.warning(f"⚠️  Vídeo já existe no banco (verificação dupla): {video_path.name}")
                    skipped += 1
                    continue

                # Obter duração
                duration = editor.get_duration(edited_path)

                # Gerar título mais descritivo
                title = f"Vídeo {i} - {video_path.stem[:30]}"

                # Salvar no banco
                video = Video(
                    source_url=f"manual_{uuid.uuid4().hex[:8]}",  # URL única para evitar constraint
                    source_album="manual",
                    title=title,
                    description="Processado automaticamente",
                    duration=duration,
                    original_path=str(video_path),
                    edited_path=str(edited_path),
                    source="manual",
                    username="system",
                    is_processed=True,
                    is_posted=False,
                    created_at=datetime.now()
                )

                session.add(video)
                session.commit()
                processed += 1
                video_logger.info(f"✅ [{i}/{len(video_files)}] Vídeo processado: {video_path.name}")

                # Pequena pausa para não sobrecarregar
                await asyncio.sleep(1)

            except Exception as e:
                session.rollback()
                video_logger.error(f"❌ Erro ao processar {video_path.name}: {e}")
                video_logger.debug(traceback.format_exc())
                errors += 1
                continue

        # Resumo final
        video_logger.info("=" * 50)
        video_logger.info("📊 RESUMO DO PROCESSAMENTO")
        video_logger.info("=" * 50)
        video_logger.info(f"✅ Processados: {processed} vídeos")
        video_logger.info(f"⏭️  Ignorados: {skipped} vídeos")
        video_logger.info(f"❌ Erros: {errors} vídeos")
        video_logger.info("=" * 50)

    except Exception as e:
        video_logger.error(f"❌ Erro fatal: {e}")
        video_logger.debug(traceback.format_exc())
    finally:
        session.close()


async def check_database():
    """Função auxiliar para verificar o banco de dados"""
    session = init_db()
    try:
        videos = session.query(Video).all()
        print("\n📊 VÍDEOS NO BANCO DE DADOS:")
        print("=" * 60)
        for v in videos:
            status = "✅ Postado" if v.is_posted else "⏳ Aguardando"
            print(f"ID: {v.id} | {status} | {v.title[:40]}")
        print("=" * 60)
        print(f"Total: {len(videos)} vídeos")
    finally:
        session.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        asyncio.run(check_database())
    else:
        asyncio.run(process_existing_videos())
