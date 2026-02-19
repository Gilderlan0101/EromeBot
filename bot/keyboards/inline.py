from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_keyboard():
    """Teclado principal do bot"""
    keyboard = [
        [
            InlineKeyboardButton('💰 Planos', callback_data='sub_show_plans'),
            InlineKeyboardButton('📊 Status', callback_data='sub_check_status'),
        ],
        [
            InlineKeyboardButton(
                '🎬 Últimos Vídeos', callback_data='video_last'
            ),
            InlineKeyboardButton('❓ Ajuda', callback_data='help'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_subscription_keyboard():
    """Teclado de planos"""
    keyboard = [
        [
            InlineKeyboardButton(
                '📅 Semanal - R$11,00', callback_data='sub_weekly'
            ),
            InlineKeyboardButton(
                '📆 Mensal - R$25,00', callback_data='sub_monthly'
            ),
        ],
        [
            InlineKeyboardButton('🔙 Voltar', callback_data='sub_back'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_payment_keyboard(pix_code: str):
    """Teclado com informações PIX"""
    keyboard = [
        [
            InlineKeyboardButton(
                '📋 Copiar código PIX', callback_data=f'copy_{pix_code}'
            ),
        ],
        [
            InlineKeyboardButton(
                '✅ Já paguei', callback_data='payment_confirm'
            ),
            InlineKeyboardButton('❌ Cancelar', callback_data='payment_cancel'),
        ],
        [
            InlineKeyboardButton('🔙 Voltar', callback_data='sub_back'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_video_keyboard(video_id: int):
    """Teclado para interação com vídeo"""
    keyboard = [
        [
            InlineKeyboardButton(
                '🔓 Ver completo', callback_data=f'video_full_{video_id}'
            ),
            InlineKeyboardButton('💰 Assinar', callback_data='sub_show_plans'),
        ],
        [
            InlineKeyboardButton(
                '📢 Compartilhar', callback_data=f'video_share_{video_id}'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_keyboard():
    """Teclado do painel admin"""
    keyboard = [
        [
            InlineKeyboardButton(
                '📊 Estatísticas', callback_data='admin_stats'
            ),
            InlineKeyboardButton('👥 Usuários', callback_data='admin_users'),
        ],
        [
            InlineKeyboardButton(
                '🔄 Forçar Scraping', callback_data='admin_force_scrape'
            ),
            InlineKeyboardButton(
                '📤 Postar Agora', callback_data='admin_force_post'
            ),
        ],
        [
            InlineKeyboardButton(
                '💰 Pagamentos', callback_data='admin_payments'
            ),
            InlineKeyboardButton('🎬 Vídeos', callback_data='admin_videos'),
        ],
        [
            InlineKeyboardButton(
                '⚙️ Configurações', callback_data='admin_settings'
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
