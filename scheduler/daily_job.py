"""
Scheduler para tarefas automáticas do Erome Bot
"""

import asyncio
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Configurar logger específico
from config.custom_logger import bot_logger, scraping_logger, video_logger
from config.settings import settings
from database.models import Payment, ScrapeLog, Video, init_db
from scrapers.erome_scraper import EromeScraper
from video_editor.editor import VideoEditor


class DailyJobScheduler:
    """Gerenciador de tarefas automáticas"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scraper = None
        self.editor = VideoEditor()
        self.running = False
        self.posting_lock = asyncio.Lock()  # Para evitar postagens simultâneas
        bot_logger.info('Inicializando DailyJobScheduler')

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
        bot_logger.info('Job diário agendado para 08:00')

        # Job de limpeza às 03:00
        self.scheduler.add_job(
            self.cleanup_job,
            CronTrigger(hour=3, minute=0),
            id='cleanup',
            replace_existing=True,
        )
        bot_logger.info('Job de limpeza agendado para 03:00')

        # Job de verificação de pagamentos a cada 30 minutos
        self.scheduler.add_job(
            self.check_pending_job,
            'interval',
            minutes=30,
            id='check_pending',
            replace_existing=True,
        )
        bot_logger.info('Job de verificação de pagamentos agendado (30/30 min)')

        # 🎯 Serviço de postagem automática
        # Para teste: a cada 4 segundos
        self.scheduler.add_job(
            self.auto_post_service,
            IntervalTrigger(seconds=4),  # Mude para minutes=5 depois do teste
            id='auto_post',
            replace_existing=True,
            misfire_grace_time=10,
        )
        bot_logger.info('📤 Serviço de postagem automática agendado (4 segundos para teste)')

        # Manter o job antigo por compatibilidade (opcional)
        self.scheduler.add_job(
            self.check_pending_videos,
            'interval',
            hours=2,
            id='check_videos_old',
            replace_existing=True,
        )
        bot_logger.info('Job de verificação de vídeos agendado (2/2 h)')


    async def auto_post_service(self):
        """
        Serviço de postagem automática que roda frequentemente
        Verifica e publica vídeos não postados, um por vez
        """
        # Usar lock para evitar execução simultânea
        if self.posting_lock.locked():
            video_logger.debug('Postagem já em andamento, ignorando...')
            return

        async with self.posting_lock:
            try:
                video_logger.debug('Verificando vídeos para postagem...')

                session = init_db()
                try:
                    # Buscar UM vídeo não postado
                    video = (
                        session.query(Video)
                        .filter_by(is_posted=False, is_processed=True)
                        .order_by(Video.created_at.asc())  # Mais antigos primeiro
                        .first()
                    )

                    if not video:
                        return

                    video_logger.info(f'📤 Encontrado vídeo para postar: {video.title[:50]}')

                    # Importar a função de postagem
                    from bot.handlers.videos import post_video_to_channel

                    # IMPORTANTE: Obter o bot da aplicação global
                    from bot.main import application

                    # Verificar se a aplicação está disponível
                    if application is None or application.bot is None:
                        video_logger.error('Aplicação do bot não disponível')
                        return

                    # Publicar passando o bot explicitamente
                    success = await post_video_to_channel(video, application.bot)

                    if success:
                        # Atualizar status no banco
                        video.is_posted = True
                        video.posted_at = datetime.now()
                        session.commit()

                        video_logger.info(f'✅ Vídeo postado com sucesso: {video.title[:50]}')

                        # Delay entre postagens (30 segundos)
                        await asyncio.sleep(30)
                    else:
                        video.error_count += 1
                        session.commit()
                        video_logger.error(f'❌ Falha ao postar vídeo {video.id}')

                        # Se falhou, esperar um pouco antes de tentar outro
                        await asyncio.sleep(10)

                except Exception as e:
                    video_logger.error(f'Erro no serviço de postagem: {e}')
                    if 'session' in locals():
                        session.rollback()
                finally:
                    if 'session' in locals():
                        session.close()

            except Exception as e:
                video_logger.error(f'Erro crítico no auto_post_service: {e}')

    def start(self):
        """Inicia o scheduler apenas se não estiver rodando"""
        if not self.running and not self.scheduler.running:
            self.setup_jobs()
            self.scheduler.start()
            self.running = True
            bot_logger.info('Scheduler iniciado com sucesso!')

            jobs = self.scheduler.get_jobs()
            for job in jobs:
                bot_logger.debug(
                    f'  • {job.id} - Próxima execução: {job.next_run_time}'
                )
        else:
            bot_logger.warning('Scheduler já está rodando')

    async def daily_video_job(self):
        """Job principal: buscar e processar até 10 vídeos novos"""
        job_start = datetime.now()
        scraping_logger.info('=' * 60)
        scraping_logger.info('INICIANDO JOB DIÁRIO DE VÍDEOS')
        scraping_logger.info('=' * 60)

        # Criar scraper apenas para o job
        self.scraper = EromeScraper(timeout=30)

        try:
            # 1. Scraping
            scraping_logger.info('Buscando novos vídeos no Erome...')
            videos_data = await self.scraper.scrape_daily(limit=20)

            if not videos_data:
                scraping_logger.warning('Nenhum vídeo novo encontrado')
                return

            scraping_logger.info(f'Encontrados {len(videos_data)} vídeos novos')

            # 2. Processar vídeos (limitar a 10 por dia)
            processed = 0
            for video_data in videos_data[: settings.DAILY_VIDEO_LIMIT]:
                try:
                    scraping_logger.info(
                        f'Processando vídeo {processed + 1}/{min(len(videos_data), settings.DAILY_VIDEO_LIMIT)}'
                    )

                    # Criar nome do arquivo
                    video_id = video_data['id']
                    video_path = settings.VIDEOS_DIR / f'{video_id}.mp4'

                    # Baixar vídeo
                    scraping_logger.info(f"Baixando: {video_data['title'][:50]}...")
                    downloaded = await self.scraper.download_video(
                        video_data['url'], video_path
                    )

                    if not downloaded:
                        scraping_logger.error('Falha no download')
                        continue

                    # Editar vídeo
                    video_logger.info('Editando vídeo...')
                    edited_path = await self.editor.process_video(
                        video_path, video_data['title']
                    )

                    if not edited_path:
                        video_logger.error('Falha na edição')
                        # Usar vídeo original se edição falhar
                        edited_path = video_path
                        video_logger.warning('Usando vídeo original sem edição')

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
                            original_path=str(video_path),  # Caminho original
                            edited_path=str(edited_path),    # Caminho do vídeo editado (CORRETO)
                            source='erome',
                            username=video_data['username'],
                            is_processed=True,
                        )

                        session.add(video)
                        session.commit()

                        processed += 1
                        scraping_logger.info(
                            f"Vídeo {processed} processado: {video_data['title'][:50]}"
                        )

                    except Exception as e:
                        scraping_logger.error(f'Erro ao salvar no banco: {e}')
                        session.rollback()
                    finally:
                        session.close()

                    # Delay entre processamentos
                    await asyncio.sleep(5)

                except Exception as e:
                    scraping_logger.error(f'Erro processando vídeo: {e}')
                    continue

            job_end = datetime.now()
            duration = (job_end - job_start).total_seconds()

            scraping_logger.info(f'Job diário concluído em {duration:.2f}s')
            scraping_logger.info(f'Processados: {processed} vídeos')

        except Exception as e:
            scraping_logger.error(f'Erro no job diário: {e}')
            import traceback
            traceback.print_exc()

        finally:
            # Fechar scraper
            if self.scraper:
                self.scraper.close()

    async def check_pending_job(self):
        """Verifica pagamentos pendentes e expirados"""
        payment_logger.debug('Verificando pagamentos pendentes...')

        session = init_db()
        try:
            now = datetime.now()
            pending = session.query(Payment).filter_by(status='pending').all()

            expired_count = 0
            for payment in pending:
                if payment.expires_at and payment.expires_at < now:
                    payment.status = 'expired'
                    expired_count += 1

            if expired_count > 0:
                session.commit()
                payment_logger.info(f'{expired_count} pagamentos expirados')

        except Exception as e:
            payment_logger.error(f'Erro verificando pagamentos: {e}')
        finally:
            session.close()

    async def check_pending_videos(self):
        """Versão antiga - mantida por compatibilidade"""
        # Agora o auto_post_service cuida disso
        video_logger.debug('Verificação legada executada')

    async def cleanup_job(self):
        """Job de limpeza de arquivos temporários"""
        bot_logger.info('Iniciando limpeza de arquivos...')

        try:
            # Limpar pasta temp
            temp_dir = settings.TEMP_DIR
            if temp_dir.exists():
                files_removed = 0
                for file in temp_dir.glob('*'):
                    if file.is_file():
                        file.unlink()
                        files_removed += 1
                bot_logger.info(f'Removidos {files_removed} arquivos temporários')

            # Limpar logs antigos (mais de 30 dias)
            log_dir = settings.LOGS_DIR
            if log_dir.exists():
                logs_removed = 0
                for log in log_dir.glob('*.log*'):
                    if log.stat().st_mtime < (datetime.now().timestamp() - 30 * 24 * 3600):
                        log.unlink()
                        logs_removed += 1
                bot_logger.info(f'Removidos {logs_removed} logs antigos')

            # Limpar vídeos não utilizados
            videos_dir = settings.VIDEOS_DIR
            if videos_dir.exists():
                session = init_db()
                try:
                    for video_file in videos_dir.glob('*.mp4'):
                        video = session.query(Video).filter_by(original_path=str(video_file)).first()
                        if not video:
                            video_file.unlink()
                            bot_logger.debug(f'Removido arquivo órfão: {video_file.name}')
                finally:
                    session.close()

            bot_logger.info('Limpeza concluída!')

        except Exception as e:
            bot_logger.error(f'Erro na limpeza: {e}')

    def shutdown(self):
        """Desliga o scheduler graciosamente"""
        bot_logger.info('Desligando scheduler...')
        if self.scheduler and self.running:
            self.scheduler.shutdown()
            self.running = False
            bot_logger.info('Scheduler desligado')


# Instância global
_scheduler_instance = None


def get_scheduler():
    """Retorna a instância única do scheduler"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = DailyJobScheduler()
    return _scheduler_instance


def start_scheduler():
    """Inicia o scheduler"""
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
