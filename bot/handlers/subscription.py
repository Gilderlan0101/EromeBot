#!/usr/bin/env python3
"""
Handlers para assinaturas e pagamentos
"""

import base64
from io import BytesIO
from datetime import datetime
import asyncio
import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes

from config.custom_logger import payment_logger, bot_logger
from config.settings import settings
from payments.plans import get_plans, get_plan
from payments.pix import PaymentGateway
from database.models import init_db


async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra os planos disponíveis"""
    try:
        user = update.effective_user
        bot_logger.info(f"Usuário {user.id} solicitou planos")

        # Verificar se é callback ou mensagem
        is_callback = update.callback_query is not None

        plans = get_plans()
        bot_logger.info(f"Planos encontrados: {len(plans) if plans else 0}")

        if not plans:
            msg = "❌ Nenhum plano disponível no momento.\n\nEntre em contato com @lunaSafe_bot"

            if is_callback:
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
            return

        # Mensagem com os planos
        msg = "💎 *PLANOS DE ASSINATURA*\n\n"
        msg += "Escolha o plano que melhor se encaixa:\n\n"

        keyboard = []

        for plan in plans:
            # Emoji diferente para vitalício
            if plan.days == 9999:
                emoji = "👑"
                duracao = "VITALÍCIO"
            else:
                emoji = "🔥"
                duracao = f"{plan.days} dias"

            msg += f"{emoji} *{plan.name}*\n"
            msg += f"💰 Preço: {plan.formatted_price}\n"
            msg += f"⏱️ Duração: {duracao}\n"
            msg += f"📝 {plan.description}\n\n"

            # Botão para este plano
            callback_data = f"plan_select_{plan.id}"
            bot_logger.info(f"Criando botão com callback: {callback_data}")

            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {plan.name} - {plan.formatted_price}",
                    callback_data=callback_data
                )
            ])

        # Botão voltar
        keyboard.append([InlineKeyboardButton("🔙 Voltar", callback_data="sub_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_callback:
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
        bot_logger.error(f"Erro em show_plans: {e}")
        traceback.print_exc()
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Erro: {str(e)}")
        else:
            await update.message.reply_text(f"❌ Erro: {str(e)}")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica status da assinatura"""
    try:
        user = update.effective_user

        # Verificar se é callback ou mensagem
        is_callback = update.callback_query is not None

        gateway = PaymentGateway()
        sub = gateway.get_user_subscription(user.id)
        gateway.close()

        msg = "📊 *STATUS DA ASSINATURA*\n\n"
        msg += f"Status: {sub['status_text']}\n"

        if sub['is_active']:
            if sub.get('plan_name'):
                msg += f"Plano: {sub['plan_name']}\n"

            if sub.get('expires_at') and sub['expires_at'].year < 2099:
                msg += f"Expira em: {sub['expires_at'].strftime('%d/%m/%Y')}\n"

        if not sub['is_active']:
            msg += "\n💡 Quer assinar? Clique no botão abaixo para ver os planos!"

        # Botão para ver planos
        keyboard = [[InlineKeyboardButton("💎 Ver Planos", callback_data="sub_show_plans")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_callback:
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
        bot_logger.error(f"Erro em check_status: {e}")
        traceback.print_exc()
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Erro: {str(e)}")
        else:
            await update.message.reply_text(f"❌ Erro: {str(e)}")


async def handle_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula callbacks de assinatura"""
    try:
        query = update.callback_query
        await query.answer()

        data = query.data
        user = update.effective_user

        bot_logger.info(f"🔍 CALLBACK RECEBIDO: '{data}' do usuário {user.id}")

        # ===== DEBUG =====
        # Mostrar todos os dados do callback
        bot_logger.info(f"Tipo do data: {type(data)}")
        bot_logger.info(f"Data começa com plan_select_: {data.startswith('plan_select_')}")
        if data.startswith('plan_select_'):
            partes = data.split('_')
            bot_logger.info(f"Partes: {partes}")
            if len(partes) >= 3:
                bot_logger.info(f"Plan ID: {partes[2]}")

        # Mostrar planos
        if data == 'sub_show_plans':
            bot_logger.info("Executando sub_show_plans")
            await show_plans(update, context)

        # Verificar status
        elif data == 'sub_check_status':
            bot_logger.info("Executando sub_check_status")
            await check_status(update, context)

        # Voltar ao menu principal
        elif data == 'sub_back':
            bot_logger.info("Executando sub_back")
            # Criar teclado do menu principal
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

            welcome_text = f"""
🎉 *BEM-VINDO AO EROME BOT!* 🎉

👋 Olá {user.first_name}!

🤖 *O que eu posso fazer por você:*
• 📹 Postar vídeos automaticamente no grupo
• 💰 Gerenciar assinaturas via PIX
• 🔄 Atualizações diárias de conteúdo

👇 *Escolha uma opção abaixo:*
            """

            await query.edit_message_text(
                welcome_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        # ===== SELEÇÃO DE PLANO =====
        elif data.startswith('plan_select_'):
            bot_logger.info("✅ Executando plan_select_")

            try:
                plan_id = int(data.split('_')[2])
                bot_logger.info(f"Plan ID extraído: {plan_id}")

                plan = get_plan(plan_id)
                bot_logger.info(f"Plano encontrado: {plan}")

                if not plan:
                    await query.edit_message_text("❌ Plano não encontrado.")
                    return

                # Duração para exibição
                if plan.days == 9999:
                    duracao = "VITALÍCIO"
                    emoji = "👑"
                else:
                    duracao = f"{plan.days} dias"
                    emoji = "🔥"

                msg = f"{emoji} *{plan.name}*\n\n"
                msg += f"💰 Valor: {plan.formatted_price}\n"
                msg += f"⏱️ Duração: {duracao}\n"
                msg += f"📝 {plan.description}\n\n"
                msg += "Deseja confirmar a assinatura?"

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Confirmar", callback_data=f"plan_confirm_{plan_id}"),
                        InlineKeyboardButton("❌ Cancelar", callback_data="sub_show_plans")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=reply_markup)

            except Exception as e:
                bot_logger.error(f"Erro ao processar plan_select: {e}")
                traceback.print_exc()
                await query.edit_message_text(f"❌ Erro ao processar seleção: {str(e)}")

        # Confirmação do plano
        elif data.startswith('plan_confirm_'):
            bot_logger.info("✅ Executando plan_confirm_")

            try:
                plan_id = int(data.split('_')[2])
                bot_logger.info(f"Confirmando plano ID: {plan_id}")

                # Mostrar mensagem de processamento
                await query.edit_message_text("⏳ *Gerando pagamento...*\n\nAguarde um momento enquanto preparamos seu PIX.", parse_mode='Markdown')

                # Pequena pausa para dar feedback visual
                await asyncio.sleep(1)

                # Criar pagamento
                gateway = PaymentGateway()
                payment_data = gateway.create_payment(
                    user_id=user.id,
                    plan_id=plan_id,
                    username=user.username,
                    first_name=user.first_name
                )
                gateway.close()

                if not payment_data:
                    await query.edit_message_text("❌ Erro ao criar pagamento. Tente novamente.")
                    return

                bot_logger.info(f"Pagamento criado: {payment_data['transaction_id']}")

                # Salvar transaction_id no context
                context.user_data['current_payment'] = payment_data['transaction_id']

                # Duração para exibição
                if payment_data['plan']['days'] == 9999:
                    duracao = "VITALÍCIO"
                    emoji = "👑"
                else:
                    duracao = f"{payment_data['plan']['days']} dias"
                    emoji = "🔥"

                # Mensagem principal
                msg = f"{emoji} *PAGAMENTO PIX GERADO!*\n\n"
                msg += f"💎 Plano: {payment_data['plan']['name']}\n"
                msg += f"💰 Valor: R$ {payment_data['amount']:.2f}\n"
                msg += f"⏱️ Duração: {duracao}\n"
                msg += f"⏰ Expira em: {payment_data['expires_at'].strftime('%H:%M')}\n\n"
                msg += "👇 *CÓDIGO PIX (Clique para copiar):*\n"
                msg += f"`{payment_data['pix_code']}`\n\n"
                msg += "👉 *Instruções:*\n"
                msg += "1️⃣ Copie o código PIX acima\n"
                msg += "2️⃣ Abra o app do seu banco\n"
                msg += "3️⃣ Escolha a opção PIX Copia e Cola\n"
                msg += "4️⃣ Cole o código e finalize o pagamento\n\n"
                msg += "Ou escaneie o QR Code abaixo:"

                # Atualizar a mensagem com o código PIX
                await query.edit_message_text(msg, parse_mode='Markdown')

                # Enviar QR Code como mensagem separada
                if payment_data['pix_qr_code']:
                    try:
                        # Decodificar QR Code
                        qr_bytes = base64.b64decode(payment_data['pix_qr_code'])
                        qr_io = BytesIO(qr_bytes)
                        qr_io.seek(0)

                        # Enviar QR Code como foto
                        await context.bot.send_photo(
                            chat_id=user.id,
                            photo=InputFile(qr_io, filename="pix_qr.png"),
                            caption="📱 *Escaneie este QR Code com seu app do banco*",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        bot_logger.error(f"Erro ao enviar QR Code: {e}")

                # Botões de ação após o pagamento
                keyboard = [
                    [InlineKeyboardButton("✅ JÁ PAGUEI", callback_data=f"check_payment_{payment_data['transaction_id']}")],
                    [InlineKeyboardButton("🔙 VOLTAR AOS PLANOS", callback_data="sub_show_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Enviar mensagem com os botões
                await context.bot.send_message(
                    chat_id=user.id,
                    text="✅ *Pagamento gerado com sucesso!*\n\nApós realizar o pagamento, clique em JÁ PAGUEI para confirmar.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

            except Exception as e:
                bot_logger.error(f"Erro ao processar plan_confirm: {e}")
                traceback.print_exc()
                await query.edit_message_text(f"❌ Erro ao gerar pagamento: {str(e)}")

        # Mostrar QR Code (caso o usuário queira ver novamente)
        elif data.startswith('show_qr_'):
            bot_logger.info("Executando show_qr_")
            transaction_id = data.split('_')[2]

            # Buscar pagamento
            gateway = PaymentGateway()
            session = init_db()
            from payments.models import PixPayment
            payment = session.query(PixPayment).filter_by(transaction_id=transaction_id).first()

            if not payment or not payment.pix_qr_code:
                await query.answer("❌ QR Code não encontrado!", show_alert=True)
                session.close()
                return

            # Decodificar QR Code
            qr_bytes = base64.b64decode(payment.pix_qr_code)
            qr_io = BytesIO(qr_bytes)
            qr_io.seek(0)

            # Enviar QR Code como foto
            await context.bot.send_photo(
                chat_id=user.id,
                photo=InputFile(qr_io, filename="pix_qr.png"),
                caption="📱 *Escaneie este QR Code com seu app do banco*",
                parse_mode='Markdown'
            )

            session.close()
            await query.answer("✅ QR Code enviado!")

        # Verificar pagamento
        elif data.startswith('check_payment_'):
            bot_logger.info("Executando check_payment_")
            transaction_id = data.split('_')[2]

            await query.edit_message_text("⏳ *Verificando pagamento...*\n\nAguarde um momento enquanto confirmamos seu pagamento.", parse_mode='Markdown')

            gateway = PaymentGateway()
            is_paid = await gateway.check_payment(transaction_id)
            gateway.close()

            if is_paid:
                msg = (
                    "✅ *PAGAMENTO CONFIRMADO!* 🎉\n\n"
                    "Sua assinatura foi ativada com sucesso!\n"
                    "Agora você tem acesso a todo conteúdo exclusivo.\n\n"
                    "Use /status para ver os detalhes da sua assinatura."
                )
                await query.edit_message_text(msg, parse_mode='Markdown')
            else:
                # Ainda não pago
                keyboard = [
                    [InlineKeyboardButton("🔄 VERIFICAR NOVAMENTE", callback_data=f"check_payment_{transaction_id}")],
                    [InlineKeyboardButton("📱 VER QR CODE", callback_data=f"show_qr_{transaction_id}")],
                    [InlineKeyboardButton("🔙 VOLTAR AOS PLANOS", callback_data="sub_show_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    "⏳ *Pagamento ainda não confirmado*\n\n"
                    "O pagamento pode levar alguns minutos para ser processado pelo banco.\n"
                    "Se já realizou o PIX, clique em VERIFICAR NOVAMENTE.\n\n"
                    "Precisa do QR Code novamente? Clique em VER QR CODE.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

        # Qualquer outro callback não reconhecido
        else:
            bot_logger.warning(f"⚠️ Callback não reconhecido: '{data}'")
            await query.edit_message_text(f"❌ Comando não reconhecido: '{data}'")

    except Exception as e:
        bot_logger.error(f"❌ Erro em handle_subscription: {e}")
        traceback.print_exc()
        try:
            await update.callback_query.edit_message_text(f"❌ Erro: {str(e)}")
        except:
            pass
