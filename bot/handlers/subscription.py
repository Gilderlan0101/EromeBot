"""
Handlers de assinatura para o Erome Bot
Versão básica para testes
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config.custom_logger import *
from config.settings import settings
from database.models import User, init_db


async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mostra os planos de assinatura disponíveis
    """
    user = update.effective_user
    bot_logger.info(f'💰 Usuário {user.id} solicitou planos')

    # Criar teclado com planos
    keyboard = [
        [
            InlineKeyboardButton(
                '📅 Semanal - R$11,00', callback_data='sub_weekly'
            ),
        ],
        [
            InlineKeyboardButton(
                '📆 Mensal - R$25,00', callback_data='sub_monthly'
            ),
        ],
        [
            InlineKeyboardButton('🔙 Voltar', callback_data='sub_back'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mensagem com planos
    plans_text = """
💰 *Planos de Assinatura*

Escolha o plano que melhor se adequa a você:

📅 *Semanal* - R$ 11,00
• Acesso por 7 dias
• Todos os vídeos
• Suporte prioritário

📆 *Mensal* - R$ 25,00
• Acesso por 30 dias
• Todos os vídeos
• Suporte prioritário
• Melhor custo-benefício

👇 Clique no botão do plano desejado
    """

    # Verificar se é callback ou mensagem
    if update.callback_query:
        await update.callback_query.edit_message_text(
            plans_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            plans_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica o status da assinatura do usuário
    """
    user = update.effective_user
    bot_logger.info(f'📊 Usuário {user.id} verificou status')

    # Buscar usuário no banco
    session = init_db()
    try:
        db_user = session.query(User).filter_by(telegram_id=user.id).first()

        if not db_user:
            status_text = """
❌ *Usuário não encontrado!*

Use /start para se registrar primeiro.
            """
        elif db_user.is_subscribed:
            # Calcular dias restantes
            if db_user.subscription_end:
                days_left = (db_user.subscription_end - datetime.now()).days
                expiry = db_user.subscription_end.strftime('%d/%m/%Y')
            else:
                days_left = 0
                expiry = 'N/A'

            status_text = f"""
✅ *Assinatura Ativa!*

📅 *Plano:* {db_user.subscription_type}
📆 *Válido até:* {expiry}
⏳ *Dias restantes:* {days_left}

💰 *Total pago:* R$ {db_user.total_paid:.2f}
            """
        else:
            status_text = """
❌ *Você não possui assinatura ativa*

Clique em /planos para assinar!
            """

    except Exception as e:
        logger.error(f'Erro ao verificar status: {e}')
        status_text = '❌ Erro ao verificar status. Tente novamente mais tarde.'
    finally:
        session.close()

    # Criar teclado
    keyboard = [
        [
            InlineKeyboardButton(
                '💰 Ver Planos', callback_data='sub_show_plans'
            ),
            InlineKeyboardButton('🔙 Voltar', callback_data='sub_back'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar resposta
    if update.callback_query:
        await update.callback_query.edit_message_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            status_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
        )


async def handle_subscription(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """
    Handler para callbacks de assinatura
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    user = update.effective_user

    if data == 'sub_weekly':
        bot_logger.info(f'Usuário {user.id} escolheu plano semanal')
        await query.edit_message_text(
            '✅ Você escolheu o plano *Semanal* (R$11,00)\n\n'
            'Em breve implementaremos o pagamento via PIX!',
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == 'sub_monthly':
        bot_logger.info(f'Usuário {user.id} escolheu plano mensal')
        await query.edit_message_text(
            '✅ Você escolheu o plano *Mensal* (R$25,00)\n\n'
            'Em breve implementaremos o pagamento via PIX!',
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == 'sub_show_plans':
        await show_plans(update, context)

    elif data == 'sub_check_status':
        await check_status(update, context)

    elif data == 'sub_back':
        from bot.keyboards.inline import get_main_keyboard

        await query.edit_message_text(
            '🏠 *Menu Principal*\n\nEscolha uma opção abaixo:',
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(),
        )


# Importar datetime para uso no check_status
from datetime import datetime
