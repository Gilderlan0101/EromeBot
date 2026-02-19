#!/usr/bin/env python3
"""
Erome Bot - Sistema Automático de Vídeos
Autor: Seu Nome
Descrição: Bot Telegram que publica vídeos diários com edição automática
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.append(str(Path(__file__).parent.parent))

# Importar configuração de logging PRIMEIRO
from config.custom_logger import setup_logger

# Configurar logger do projeto ANTES de outras importações
logger = setup_logger(
    log_dir="logs", rotation='500 MB', retention='30 days'
)

# AGORA importar os loggers especializados (já estarão inicializados)
from config.custom_logger import (
    bot_logger, payment_logger, scraping_logger,
    video_logger, db_logger, get_category_logger
)

# Importações do Telegram
from telegram import Update, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Importações do projeto
from config.settings import settings
from config.constants import START_MESSAGE

# Importar handlers
from bot.handlers import start, subscription, videos, admin

# Importar banco de dados e scheduler
from database.models import init_db
from scheduler.daily_job import get_scheduler, shutdown_scheduler


class EromeBot:
    """Classe principal do bot"""

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.app = None
        self.scheduler = None
        self._running = False
        self.auto_message_task = None  # Para controlar a tarefa automática
        bot_logger.info('🤖 Instância do bot criada')

    async def auto_message_loop(self):
        """Loop de mensagens automáticas a cada 3 segundos"""
        message_count = 0
        bot_logger.info("🔄 Iniciando loop de mensagens automáticas (a cada 3 segundos)")

        while self._running:
            try:
                message_count += 1

                # Mensagem de teste
                test_message = f"""
🤖 **MENSAGEM AUTOMÁTICA #{message_count}**

📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
⏰ Hora: {datetime.now().strftime('%H:%M:%S')}
📢 Enviado por: @lunaSafe_bot

🔄 Esta é uma mensagem de teste automática
📊 Contador: {message_count} mensagens enviadas
                """

                # Enviar para o grupo
                if self.app and self.app.bot:
                    await self.app.bot.send_message(
                        chat_id=settings.TELEGRAM_CHANNEL_ID,
                        text=test_message
                    )

                    bot_logger.info(f"✅ Mensagem automática #{message_count} enviada")

                # Aguardar 3 segundos
                await asyncio.sleep(3)

            except Exception as e:
                bot_logger.error(f"❌ Erro no loop automático: {e}")
                await asyncio.sleep(3)  # Mesmo com erro, continua tentando

    async def start_auto_messages(self):
        """Inicia o envio automático de mensagens"""
        if not self.auto_message_task or self.auto_message_task.done():
            self.auto_message_task = asyncio.create_task(self.auto_message_loop())
            bot_logger.info("✅ Loop de mensagens automáticas iniciado")

    async def stop_auto_messages(self):
        """Para o envio automático de mensagens"""
        if self.auto_message_task and not self.auto_message_task.done():
            self.auto_message_task.cancel()
            try:
                await self.auto_message_task
            except asyncio.CancelledError:
                pass
            bot_logger.info("🛑 Loop de mensagens automáticas parado")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando start personalizado"""
        try:
            user = update.effective_user
            chat = update.effective_chat

            welcome_msg = f"""
🎉 BEM-VINDO AO EROME BOT! 🎉

👋 Olá {user.first_name}!

📌 Comandos disponíveis:
/ping - Testar conexão
/start_auto - Iniciar mensagens automáticas
/stop_auto - Parar mensagens automáticas
/status_auto - Status das mensagens
/help - Ajuda
/planos - Ver planos
/status - Status da assinatura

🎯 Status: Bot operacional!
            """

            await update.message.reply_text(welcome_msg)
            bot_logger.info(f"✅ Start executado para {user.first_name}")

        except Exception as e:
            bot_logger.error(f"Erro no start: {e}")

    async def start_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para iniciar mensagens automáticas"""
        try:
            # Verificar se é admin
            if update.effective_user.id not in settings.ADMIN_IDS:
                await update.message.reply_text("❌ Apenas administradores podem usar este comando.")
                return

            await self.start_auto_messages()
            await update.message.reply_text(
                f"✅ Mensagens automáticas iniciadas!\n"
                f"📢 Grupo: @Xnovinhas_18\n"
                f"⏰ Intervalo: 3 segundos"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {e}")

    async def stop_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para parar mensagens automáticas"""
        try:
            # Verificar se é admin
            if update.effective_user.id not in settings.ADMIN_IDS:
                await update.message.reply_text("❌ Apenas administradores podem usar este comando.")
                return

            await self.stop_auto_messages()
            await update.message.reply_text("🛑 Mensagens automáticas paradas!")

        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {e}")

    async def status_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando para ver status das mensagens automáticas"""
        try:
            if self.auto_message_task and not self.auto_message_task.done():
                status = "🟢 ATIVO"
            else:
                status = "🔴 INATIVO"

            await update.message.reply_text(
                f"📊 **Status das Mensagens Automáticas**\n\n"
                f"Status: {status}\n"
                f"Grupo: @Xnovinhas_18\n"
                f"Intervalo: 3 segundos\n"
                f"Bot: @lunaSafe_bot"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erro: {e}")

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando ping para testar o bot"""
        try:
            user = update.effective_user
            chat = update.effective_chat

            chat_type = "Grupo" if chat.type in ["group", "supergroup"] else "Privado"

            response = (
                f"🏓 PONG!\n\n"
                f"✅ Bot: @lunaSafe_bot\n"
                f"👤 Usuário: {user.first_name}\n"
                f"📌 Chat: {chat_type}\n"
                f"🆔 Chat ID: {chat.id}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            )

            await update.message.reply_text(response)
            bot_logger.info(f"✅ Ping respondido para {user.first_name} no {chat_type}")

        except Exception as e:
            bot_logger.error(f"Erro no ping: {e}")

    async def post_init(self, application: Application):
        """Executado após inicialização do bot"""
        try:
            # Comandos básicos
            await application.bot.set_my_commands(
                [
                    ('start', 'Iniciar bot'),
                    ('ping', 'Testar bot'),
                    ('help', 'Ajuda'),
                    ('planos', 'Ver planos'),
                    ('status', 'Status da assinatura'),
                ]
            )

            # Comandos admin
            if settings.ADMIN_IDS and len(settings.ADMIN_IDS) > 0:
                await application.bot.set_my_commands(
                    [
                        ('start_auto', 'Iniciar msgs automáticas'),
                        ('stop_auto', 'Parar msgs automáticas'),
                        ('status_auto', 'Status das msgs'),
                    ],
                    scope=BotCommandScopeChat(settings.ADMIN_IDS[0]),
                )

            bot_logger.info('✅ Bot inicializado com sucesso!')

        except Exception as e:
            bot_logger.error(f'Erro no post_init: {e}')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tratamento global de erros"""
        error_msg = f"❌ Erro: {context.error}"
        bot_logger.error(error_msg)

    def setup_handlers(self):
        """Configura todos os handlers do bot"""

        # Handlers de teste
        self.app.add_handler(CommandHandler('ping', self.ping_command))

        # Handlers de mensagens automáticas (só admin)
        if settings.ADMIN_IDS and len(settings.ADMIN_IDS) > 0:
            admin_filter = filters.User(user_id=settings.ADMIN_IDS)
            self.app.add_handler(CommandHandler('start_auto', self.start_auto_command, filters=admin_filter))
            self.app.add_handler(CommandHandler('stop_auto', self.stop_auto_command, filters=admin_filter))
            self.app.add_handler(CommandHandler('status_auto', self.status_auto_command, filters=admin_filter))

        # Handler de start
        self.app.add_handler(CommandHandler('start', self.start_command))

        # Handlers de comando existentes
        self.app.add_handler(CommandHandler('help', start.help_command))
        self.app.add_handler(CommandHandler('planos', subscription.show_plans))
        self.app.add_handler(CommandHandler('status', subscription.check_status))
        self.app.add_handler(CommandHandler('ultimos', videos.last_videos))

        # Handlers de callback
        self.app.add_handler(
            CallbackQueryHandler(subscription.handle_subscription, pattern='^sub_')
        )

        # Handler de mensagens de texto
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.safe_message_handler)
        )

        # Handler de erros
        self.app.add_error_handler(self.error_handler)

        bot_logger.info('✅ Handlers configurados')

    async def safe_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler seguro para mensagens de texto"""
        try:
            if update.message and update.message.text:
                await start.handle_message(update, context)
        except Exception as e:
            bot_logger.error(f"Erro no message handler: {e}")

    def setup_scheduler(self):
        """Configura o scheduler para tarefas automáticas"""
        try:
            self.scheduler = get_scheduler()
            bot_logger.info('✅ Scheduler configurado')
        except Exception as e:
            bot_logger.error(f'Erro ao configurar scheduler: {e}')

    async def run(self):
        """Executa o bot"""
        try:
            # Inicializar banco de dados
            bot_logger.info('🗄️ Conectando ao banco de dados...')
            init_db(settings.DATABASE_URL)
            bot_logger.info('✅ Banco de dados inicializado!')

            # Criar aplicação
            self.app = (
                Application.builder()
                .token(self.token)
                .post_init(self.post_init)
                .build()
            )

            # Configurar handlers
            self.setup_handlers()

            # Configurar scheduler
            self.setup_scheduler()

            # Marcar como rodando
            self._running = True

            # Iniciar bot
            bot_logger.info('🚀 Bot iniciando...')
            await self.app.initialize()
            await self.app.start()

            # Iniciar polling
            await self.app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            # Iniciar scheduler
            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                bot_logger.info('✅ Scheduler iniciado')
            else:
                bot_logger.info('✅ Scheduler já estava rodando')

            bot_logger.info('🤖 Bot está rodando! Pressione Ctrl+C para parar.')

            # Manter rodando
            while self._running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            bot_logger.info('🛑 Bot interrompido pelo usuário')
        except Exception as e:
            bot_logger.error(f'❌ Erro fatal: {e}')
            import traceback
            traceback.print_exc()
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Desliga o bot graciosamente"""
        bot_logger.info('🛑 Desligando bot...')

        self._running = False

        # Parar mensagens automáticas
        await self.stop_auto_messages()

        # Parar scheduler
        if self.scheduler and hasattr(self.scheduler, 'running') and self.scheduler.running:
            try:
                shutdown_scheduler()
                bot_logger.info('✅ Scheduler parado')
            except Exception as e:
                bot_logger.error(f'Erro ao parar scheduler: {e}')

        # Parar bot
        if self.app:
            try:
                if self.app.updater and self.app.updater.running:
                    await self.app.updater.stop()
                    bot_logger.info('✅ Updater parado')

                await self.app.stop()
                await self.app.shutdown()
                bot_logger.info('✅ Application parado')
            except Exception as e:
                bot_logger.error(f'Erro ao parar bot: {e}')

        bot_logger.info('✅ Bot desligado com sucesso!')


def main():
    """Função principal"""
    try:
        # Criar diretórios necessários
        for dir_path in [
            settings.VIDEOS_DIR,
            settings.EDITED_DIR,
            settings.TEMP_DIR,
            settings.LOGS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f'📁 Diretório verificado: {dir_path}')

        # Verificar loggers
        logger.info("=== INICIANDO EROME BOT ===")
        bot_logger.info("Logger do bot OK")
        db_logger.info("Logger do banco de dados OK")
        video_logger.info("Logger de vídeos OK")

        # Verificar grupo
        if hasattr(settings, 'TELEGRAM_CHANNEL_ID') and settings.TELEGRAM_CHANNEL_ID:
            logger.info(f"📢 Grupo configurado: {settings.TELEGRAM_CHANNEL_ID}")
        else:
            logger.warning("⚠️ TELEGRAM_CHANNEL_ID não configurado!")

        # Executar bot
        bot = EromeBot()
        asyncio.run(bot.run())

    except KeyboardInterrupt:
        logger.info('👋 Bot encerrado pelo usuário')
    except Exception as e:
        logger.error(f'💥 Erro não tratado: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
