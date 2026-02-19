import qrcode
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import hashlib

from config.settings import settings
from database.db import Session
from database.models import Payment, User



class PIXPayment:
    """Gerenciador de pagamentos PIX"""

    def __init__(self):
        self.key = settings.PIX_KEY
        self.name = settings.PIX_NAME
        self.city = settings.PIX_CITY

    def generate_pix_code(self, amount: float, description: str = '') -> str:
        """
        Gera código PIX estático

        Args:
            amount: Valor do pagamento
            description: Descrição (opcional)

        Returns:
            Código PIX copia-e-cola
        """
        # Formato PIX estático
        # Formato: 00020126360014BR.GOV.BCB.PIX0114+chavepix@email.com5204000053039865405XX.XX5802BR5912Nome Sobrenome6008Cidade62070503***6304XXXX

        # Montar payload
        payload = f'00020126360014BR.GOV.BCB.PIX0114{self.key}520400005303986'
        payload += f'5405{amount:.2f}5802BR5912{self.name}6008{self.city}'
        payload += '62070503***6304'

        # Calcular CRC16
        crc = self._calculate_crc16(payload)
        payload += crc

        return payload

    def _calculate_crc16(self, payload: str) -> str:
        """Calcula CRC16 do payload PIX"""
        crc = 0xFFFF
        for byte in payload.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return format(crc & 0xFFFF, '04X').upper()

    def generate_qr_code(self, pix_code: str, output_path: Path) -> Path:
        """
        Gera QR Code PIX

        Args:
            pix_code: Código PIX copia-e-cola
            output_path: Caminho para salvar QR Code

        Returns:
            Caminho do arquivo QR Code
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(pix_code)
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        img.save(output_path)

        return output_path

    async def create_payment(self, user_id: int, period: str) -> Dict:
        """
        Cria um novo pagamento

        Args:
            user_id: ID do usuário no Telegram
            period: 'weekly' ou 'monthly'

        Returns:
            Dicionário com informações do pagamento
        """
        amount = (
            settings.WEEKLY_PRICE
            if period == 'weekly'
            else settings.MONTHLY_PRICE
        )
        transaction_id = str(uuid.uuid4())

        # Gerar código PIX
        pix_code = self.generate_pix_code(amount, f'Assinatura {period}')

        # Gerar QR Code
        qr_path = settings.TEMP_DIR / f'pix_{transaction_id}.png'
        self.generate_qr_code(pix_code, qr_path)

        # Salvar no banco
        session = Session()
        try:
            db_user = (
                session.query(User).filter_by(telegram_id=user_id).first()
            )

            if not db_user:
                raise Exception('Usuário não encontrado')

            payment = Payment(
                user_id=db_user.id,
                transaction_id=transaction_id,
                pix_code=pix_code,
                qr_code_path=str(qr_path),
                amount=amount,
                period_type=period,
                expires_at=datetime.now() + timedelta(hours=24),
            )

            session.add(payment)
            session.commit()

            logger.info(
                f'Pagamento criado: {transaction_id} - R${amount} - {period}'
            )

            return {
                'transaction_id': transaction_id,
                'pix_code': pix_code,
                'qr_code_path': qr_path,
                'amount': amount,
                'period': period,
                'expires_at': payment.expires_at,
            }

        except Exception as e:
            session.rollback()
            logger.error(f'Erro ao criar pagamento: {e}')
            raise
        finally:
            session.close()

    async def check_payment(self, transaction_id: str) -> bool:
        """
        Verifica se pagamento foi confirmado

        Args:
            transaction_id: ID da transação

        Returns:
            True se pago, False caso contrário
        """
        # Em produção, integrar com gateway de pagamento
        # Aqui simulamos confirmação manual
        session = Session()
        try:
            payment = (
                session.query(Payment)
                .filter_by(transaction_id=transaction_id)
                .first()
            )

            if payment and payment.status == 'paid':
                return True

            return False

        finally:
            session.close()

    async def confirm_payment(self, transaction_id: str):
        """
        Confirma pagamento e ativa assinatura

        Args:
            transaction_id: ID da transação
        """
        session = Session()
        try:
            payment = (
                session.query(Payment)
                .filter_by(transaction_id=transaction_id)
                .first()
            )

            if not payment:
                raise Exception('Pagamento não encontrado')

            # Atualizar pagamento
            payment.status = 'paid'
            payment.paid_at = datetime.now()

            # Atualizar assinatura do usuário
            user = payment.user
            user.is_subscribed = True
            user.subscription_type = payment.period_type
            user.subscription_start = datetime.now()

            # Calcular data de expiração
            days = 7 if payment.period_type == 'weekly' else 30
            user.subscription_end = datetime.now() + timedelta(days=days)

            user.total_paid += payment.amount
            user.last_payment_date = datetime.now()

            session.commit()

            logger.info(
                f'✅ Pagamento confirmado: {transaction_id} - Usuário {user.telegram_id}'
            )

        except Exception as e:
            session.rollback()
            logger.error(f'Erro ao confirmar pagamento: {e}')
            raise
        finally:
            session.close()


pix_manager = PIXPayment()
