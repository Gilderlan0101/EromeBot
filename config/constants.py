"""Constantes do projeto"""

# Mensagens do bot
START_MESSAGE = """
🎬 *Bem-vindo ao Canal Premium de Vídeos!*

Aqui você encontra os melhores conteúdos diariamente!

🔹 *10 vídeos novos todo dia*
🔹 *Conteúdo exclusivo*
🔹 *Qualidade HD*

Escolha seu plano:

💰 *Semanal* - R$ 11,00
💰 *Mensal* - R$ 25,00

Clique no botão abaixo para assinar!
"""

SUBSCRIPTION_SUCCESS = """
✅ *Assinatura confirmada!*

Você agora tem acesso ao canal premium por {period}.

🔗 *Link do canal:* {channel_link}

Seu acesso será liberado em instantes!
"""

VIDEO_CAPTION = """
🎥 *{title}*

⏱️ Duração: {duration}
👤 Fonte: {source}
📅 Postado: {date}

🔞 *Conteúdo exclusivo para assinantes*

👉 Assine para ver o vídeo completo!
"""

PAYMENT_MESSAGE = """
💳 *Pagamento via PIX*

Valor: R$ {amount}
Período: {period}

📱 *Escaneie o QR Code ou copie o código PIX abaixo:*

`{pix_code}`

⏳ O acesso será liberado automaticamente após a confirmação.
"""

# Teclados inline
SUBSCRIBE_BUTTON = '🔓 Assinar Agora'
WEEKLY_BUTTON = '📅 Semanal - R$ 11,00'
MONTHLY_BUTTON = '📆 Mensal - R$ 25,00'
CONFIRM_PAYMENT = '✅ Confirmar Pagamento'
CANCEL_BUTTON = '❌ Cancelar'

# Scraping selectors
EROME_SELECTORS = {
    'album_link': 'a.album-link',
    'video_container': '.media-container',
    'video_title': 'h1.album-title',
    'video_source': 'video source[src*=".mp4"]',
    'video_direct': 'video[src*=".mp4"]',
    'username': '.album-user',
    'views': '.album-bottom-views',
}
