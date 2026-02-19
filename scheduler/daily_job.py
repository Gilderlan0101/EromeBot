"""
Scheduler para tarefas automáticas do Erome Bot
"""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional
from pathlib import Path

from scrapers.erome_scraper import EromeScraper
from video_editor.editor import VideoEditor
from database.models import init_db
from database.models import Video, ScrapeLog, Payment
from config.settings import settings

# Configurar logger específico
from config.custom_logger import bot_logger, scraping_logger, video_logger


class DailyJobScheduler:
    """Gerenciador de tarefas automáticas"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper = None
        self.editor = VideoEditor()
        self.running = False
        bot_logger.info('🔄 Inicializando DailyJobScheduler')

    def setup_jobs(self):
        """Configura todos os jobs (separado do start)"""

        # Job diário às 08:00 (buscar e processar vídeos)
        self.scheduler.add_job(
            self.daily_video_job,
            CronTrigger(hour=8, minute=0),
            id='daily_videos',
            replace_existing=True,
            misfire_grace_time=3600,
        )
        bot_logger.info('⏰ Job diário agendado para 08:00')

        # Job de limpeza às 03:00
        self.scheduler.add_job(
            self.cleanup_job,
            CronTrigger(hour=3, minute=0),
            id='cleanup',
            replace_existing=True,
        )
        bot_logger.info('🧹 Job de limpeza agendado para 03:00')

        # Job de verificação de pagamentos a cada 30 minutos
        self.scheduler.add_job(
            self.check_pending_job,
            'interval',
            minutes=30,
            id='check_pending',
            replace_existing=True,
        )
        bot_logger.info('💰 Job de verificação de pagamentos agendado (30/30 min)')

        # Job de verificação de vídeos não postados a cada 2 horas
        self.scheduler.add_job(
            self.check_pending_videos,
            'interval',
            hours=2,
            id='check_videos',
            replace_existing=True,
        )
        bot_logger.info('🎬 Job de verificação de vídeos agendado (2/2 h)')

    def start(self):
        """Inicia o scheduler apenas se não estiver rodando"""
        if not self.running and not self.scheduler.running:
            # Configurar jobs antes de iniciar
            self.setup_jobs()

            self.scheduler.start()
            self.running = True
            bot_logger.info('✅ Scheduler iniciado com sucesso!')

            # Listar jobs ativos
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                bot_logger.debug(f'  • {job.id} - Próxima execução: {job.next_run_time}')
        else:
            bot_logger.warning('⚠️ Scheduler já está rodando')

    async def daily_video_job(self):
        """Job principal: buscar e processar até 10 vídeos novos"""
        job_start = datetime.now()
        scraping_logger.info('=' * 60)
        scraping_logger.info('🚀 INICIANDO JOB DIÁRIO DE VÍDEOS')
        scraping_logger.info('=' * 60)

        # Criar scraper apenas para o job
        self.scraper = EromeScraper(headless=True, timeout=30)

        try:
            # 1. Scraping
            scraping_logger.info('🔍 Buscando novos vídeos no Erome...')
            videos_data = await self.scraper.scrape_daily(limit=20)

            if not videos_data:
                scraping_logger.warning('⚠️ Nenhum vídeo novo encontrado')
                return

            scraping_logger.info(f'📊 Encontrados {len(videos_data)} vídeos novos')

            # 2. Processar vídeos (limitar a 10 por dia)
            processed = 0
            for video_data in videos_data[: settings.DAILY_VIDEO_LIMIT]:
                try:
                    scraping_logger.info(
                        f'📥 Processando vídeo {processed + 1}/{min(len(videos_data), settings.DAILY_VIDEO_LIMIT)}'
                    )

                    # Criar nome do arquivo
                    video_id = video_data['id']
                    video_path = settings.VIDEOS_DIR / f'{video_id}.mp4'

                    # Baixar vídeo
                    scraping_logger.info(f"⬇️ Baixando: {video_data['title'][:50]}...")
                    downloaded = await self.scraper.download_video(
                        video_data['url'], video_path
                    )

                    if not downloaded:
                        scraping_logger.error('❌ Falha no download')
                        continue

                    # Editar vídeo (adicionar watermark, cortar se necessário)
                    scraping_logger.info('✂️ Editando vídeo...')
                    edited_path = await self.editor.process_video(
                        video_path, video_data['title']
                    )

                    if not edited_path:
                        scraping_logger.error('❌ Falha na edição')
                        continue

                    # Obter duração
                    duration = self.editor.get_duration(edited_path)

                    # Salvar no banco
                    session = init_db()
                    try:
                        video = Video(
                            source_url=video_data['url'],
                            source_album=video_data['album_url'],
                            title=video_data['title'][:200],
                            duration=duration,
                            original_path=str(video_path),
                            edited_path=str(edited_path),
                            source='erome',
                            username=video_data['username'],
                            is_processed=True,
                        )

                        session.add(video)
                        session.commit()

                        processed += 1
                        scraping_logger.info(
                            f"✅ Vídeo {processed} processado: {video_data['title'][:50]}"
                        )

                    except Exception as e:
                        scraping_logger.error(f'Erro ao salvar no banco: {e}')
                        session.rollback()
                    finally:
                        session.close()

                    # Delay entre processamentos
                    await asyncio.sleep(5)

                except Exception as e:
                    scraping_logger.error(f'❌ Erro processando vídeo: {e}')
                    continue

            # 3. Publicar vídeos processados
            if processed > 0:
                scraping_logger.info(f'📤 Publicando {processed} vídeos no canal...')
                await self.post_videos(processed)
            else:
                scraping_logger.warning('⚠️ Nenhum vídeo foi processado com sucesso')

            job_end = datetime.now()
            duration = (job_end - job_start).total_seconds()

            scraping_logger.info(f'✅ Job diário concluído em {duration:.2f}s')
            scraping_logger.info(f'📊 Processados: {processed} vídeos')

        except Exception as e:
            scraping_logger.error(f'❌ Erro no job diário: {e}')
            scraping_logger.exception('Detalhes do erro:')

        finally:
            # Fechar scraper
            if self.scraper:
                self.scraper.close()

    async def post_videos(self, limit: int):
        """
        Publica vídeos no canal Telegram

        Args:
            limit: Número máximo de vídeos para publicar
        """
        from bot.handlers.videos import post_video_to_channel

        session = init_db()
        try:
            # Buscar vídeos não postados
            videos = (
                session.query(Video)
                .filter_by(is_posted=False, is_processed=True)
                .limit(limit)
                .all()
            )

            if not videos:
                video_logger.info('📭 Nenhum vídeo pendente para publicação')
                return

            video_logger.info(f'📤 Publicando {len(videos)} vídeos...')

            for i, video in enumerate(videos, 1):
                try:
                    video_logger.info(
                        f'Publicando {i}/{len(videos)}: {video.title[:50]}'
                    )

                    # Publicar no canal
                    success = await post_video_to_channel(video)

                    if success:
                        video.is_posted = True
                        video.posted_at = datetime.now()
                        session.commit()

                        video_logger.info(f'✅ Vídeo {i} publicado com sucesso')

                        # Delay entre postagens (30 segundos)
                        await asyncio.sleep(30)
                    else:
                        video.error_count += 1
                        session.commit()
                        video_logger.error(f'❌ Falha ao publicar vídeo {i}')

                except Exception as e:
                    video_logger.error(f'Erro publicando vídeo {video.id}: {e}')
                    video.error_count += 1
                    session.commit()

        except Exception as e:
            video_logger.error(f'Erro no banco: {e}')
        finally:
            session.close()

    async def cleanup_job(self):
        """Job de limpeza de arquivos temporários"""
        bot_logger.info('🧹 Iniciando limpeza de arquivos...')

        try:
            # Limpar pasta temp
            temp_dir = settings.TEMP_DIR
            if temp_dir.exists():
                files_removed = 0
                for file in temp_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
                        files_removed += 1
                bot_logger.info(
                    f'📁 Removidos {files_removed} arquivos temporários'
                )

            # Limpar logs antigos (mais de 30 dias)
            log_dir = settings.LOGS_DIR
            if log_dir.exists():
                logs_removed = 0
                for log in log_dir.glob('*.log'):
                    # Manter logs dos últimos 30 dias
                    if log.stat().st_mtime < (
                        datetime.now().timestamp() - 30 * 24 * 3600
                    ):
                        log.unlink()
                        logs_removed += 1
                bot_logger.info(f'📊 Removidos {logs_removed} logs antigos')

            # Limpar vídeos não utilizados (opcional)
            # Por exemplo, vídeos com mais de 7 dias e não postados
            videos_dir = settings.VIDEOS_DIR
            if videos_dir.exists():
                session = init_db()
                try:
                    for video_file in videos_dir.glob('*.mp4'):
                        # Verificar se o vídeo está no banco
                        video_id = video_file.stem
                        video = (
                            session.query(Video)
                            .filter_by(original_path=str(video_file))
                            .first()
                        )

                        # Se não estiver no banco ou for muito antigo
                        if not video:
                            video_file.unlink()
                            bot_logger.debug(
                                f'Removido arquivo órfão: {video_file.name}'
                            )
                finally:
                    session.close()

            bot_logger.info('✅ Limpeza concluída!')

        except Exception as e:
            bot_logger.error(f'❌ Erro na limpeza: {e}')

    async def check_pending_job(self):
        """Verifica pagamentos pendentes e expirados"""
        payment_logger.debug('💰 Verificando pagamentos pendentes...')

        session = init_db()
        try:
            now = datetime.now()

            # Buscar pagamentos pendentes
            pending = session.query(Payment).filter_by(status='pending').all()

            expired_count = 0
            for payment in pending:
                # Verificar se expirou
                if payment.expires_at and payment.expires_at < now:
                    payment.status = 'expired'
                    expired_count += 1

            if expired_count > 0:
                session.commit()
                payment_logger.info(f'⏰ {expired_count} pagamentos expirados')

            # Em produção: integrar com gateway de pagamento
            # Aqui simulamos confirmação manual via webhook

        except Exception as e:
            payment_logger.error(f'Erro verificando pagamentos: {e}')
        finally:
            session.close()

    async def check_pending_videos(self):
        """Verifica se há vídeos processados não postados"""
        video_logger.debug('🎬 Verificando vídeos pendentes...')

        session = init_db()
        try:
            # Contar vídeos não postados
            pending = (
                session.query(Video)
                .filter_by(is_posted=False, is_processed=True)
                .count()
            )

            if pending > 0:
                video_logger.info(f'📤 {pending} vídeos aguardando publicação')

                # Se tiver muitos vídeos pendentes, publicar alguns
                if pending >= 5:
                    await self.post_videos(min(pending, 5))
            else:
                video_logger.debug('Nenhum vídeo pendente')

        except Exception as e:
            video_logger.error(f'Erro verificando vídeos: {e}')
        finally:
            session.close()

    def shutdown(self):
        """Desliga o scheduler graciosamente"""
        bot_logger.info('🛑 Desligando scheduler...')
        if self.scheduler and self.running:
            self.scheduler.shutdown()
            self.running = False
            bot_logger.info('✅ Scheduler desligado')


# Instância global (não iniciada automaticamente)
_scheduler_instance = None


def get_scheduler():
    """Retorna a instância única do scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DailyJobScheduler()
    return _scheduler_instance


def start_scheduler():
    """
    Inicia o scheduler (função para ser chamada externamente)

    Returns:
        Instância do scheduler
    """
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler


def shutdown_scheduler():
    """Desliga o scheduler global"""
    global _scheduler_instance
    if _scheduler_instance and _scheduler_instance.running:
        _scheduler_instance.shutdown()
        _scheduler_instance = None
