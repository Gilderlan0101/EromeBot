import hashlib
import uuid
import base64
import qrcode
import re
from io import BytesIO
from datetime import datetime, timedelta
from typing import Dict, Optional

from config.settings import settings
from config.custom_logger import payment_logger
from database.models import init_db
from database.models import PixPayment, Plan, UserSubscription


class PaymentGateway:
    """Gateway de pagamentos PIX"""

    def __init__(self):
        # Dados do recebedor
        self.pix_key = settings.PIX_KEY  # dacruzgg01@gmail.com
        # Nome formatado (sem acentos, maiúsculas, max 25 caracteres)
        self.merchant_name = self._format_name("GILDERLAN SILVA DA CRUZ")
        self.merchant_city = "IBIRATAIA"  # Cidade em maiúsculas
        self.session = init_db()
        payment_logger.info('💰 Gateway de pagamentos inicializado')

    def _format_name(self, name: str) -> str:
        """
        Formata o nome para o padrão PIX:
        - Maiúsculas
        - Sem acentos
        - Máximo 25 caracteres
        - Sem caracteres especiais
        """
        # Converter para maiúsculas
        name = name.upper()

        # Remover acentos (substituir por caracteres simples)
        acentos = {
            'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
            'É': 'E', 'È': 'E', 'Ê': 'E',
            'Í': 'I', 'Ì': 'I', 'Î': 'I',
            'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O',
            'Ú': 'U', 'Ù': 'U', 'Û': 'U',
            'Ç': 'C'
        }
        for acento, sem_acento in acentos.items():
            name = name.replace(acento, sem_acento)

        # Remover caracteres não permitidos (manter letras, espaços e pontos)
        name = re.sub(r'[^A-Z\s\.]', '', name)

        # Limitar a 25 caracteres e remover espaços extras
        name = ' '.join(name.split())[:25]

        return name

    def _format_amount(self, amount: float) -> str:
        """
        Formata o valor para o padrão PIX:
        - Sem separador de milhar
        - Ponto como separador decimal
        - Exatamente 2 casas decimais
        """
        return f"{amount:.2f}"

    def generate_pix_code(self, amount: float, description: str = '') -> str:
        """
        Gera código PIX copia e cola seguindo o padrão oficial

        Args:
            amount: Valor do pagamento
            description: Descrição (opcional)

        Returns:
            str: Código PIX copia e cola
        """
        try:
            # Transaction ID único (até 25 caracteres alfanuméricos)
            txid = hashlib.sha256(f"{amount}{datetime.now()}{uuid.uuid4()}".encode()).hexdigest()[:25].upper()

            # Formatar valor
            amount_str = self._format_amount(amount)

            # Nome formatado
            merchant_name = self.merchant_name

            # Cidade formatada
            merchant_city = self.merchant_city[:15]

            # Montar payload PIX seguindo o padrão oficial
            # Formato: [ID do campo][tamanho][valor]

            # 00 - Payload Format Indicator (fixo)
            payload = "000201"

            # 26 - Merchant Account Information
            # 0014BR.GOV.BCB.PIX + 01 + tamanho da chave + chave
            pix_key_length = len(self.pix_key)
            merchant_account = f"0014BR.GOV.BCB.PIX01{pix_key_length:02d}{self.pix_key}"
            payload += f"26{len(merchant_account):02d}{merchant_account}"

            # 52 - Merchant Category Code (fixo)
            payload += "52040000"

            # 53 - Transaction Currency (986 = BRL)
            payload += "5303986"

            # 54 - Transaction Amount
            amount_field = f"{len(amount_str):02d}{amount_str}"
            payload += f"54{amount_field}"

            # 58 - Country Code (fixo)
            payload += "5802BR"

            # 59 - Merchant Name
            merchant_name_field = f"{len(merchant_name):02d}{merchant_name}"
            payload += f"59{merchant_name_field}"

            # 60 - Merchant City
            merchant_city_field = f"{len(merchant_city):02d}{merchant_city}"
            payload += f"60{merchant_city_field}"

            # 62 - Additional Data Field (TXID)
            # 05 - TXID
            txid_field = f"05{len(txid):02d}{txid}"
            additional_data = f"{len(txid_field):02d}{txid_field}"
            payload += f"62{additional_data}"

            # Adicionar CRC16 (será calculado depois)
            payload += "6304"

            # Calcular CRC16
            crc = self._calculate_crc16(payload)
            payload += crc

            payment_logger.info(f"✅ Payload PIX gerado para R${amount}")
            payment_logger.debug(f"Payload: {payload}")
            return payload

        except Exception as e:
            payment_logger.error(f"❌ Erro ao gerar payload PIX: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _calculate_crc16(self, payload: str) -> str:
        """Calcula CRC16 do payload PIX (padrão ISO/IEC 13239)"""
        crc = 0xFFFF
        for byte in payload.encode('utf-8'):
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return format(crc & 0xFFFF, '04X').upper()

    def generate_qr_code_base64(self, pix_code: str) -> str:
        """
        Gera QR Code em base64

        Args:
            pix_code: Código PIX

        Returns:
            str: Imagem QR Code em base64
        """
        try:
            # Criar QR Code com configurações otimizadas
            qr = qrcode.QRCode(
                version=2,  # Aumentar versão para payloads maiores
                box_size=10,
                border=2,   # Reduzir borda
                error_correction=qrcode.constants.ERROR_CORRECT_M
            )
            qr.add_data(pix_code)
            qr.make(fit=True)

            # Criar imagem com cores padrão
            img = qr.make_image(fill_color="black", back_color="white")

            # Converter para bytes e depois base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            payment_logger.info("✅ QR Code gerado com sucesso")
            return img_base64

        except Exception as e:
            payment_logger.error(f"❌ Erro ao gerar QR Code: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def create_payment(self, user_id: int, plan_id: int, username: str = "", first_name: str = "") -> dict:
        """
        Cria um novo pagamento

        Args:
            user_id: ID do usuário no Telegram
            plan_id: ID do plano
            username: Username do Telegram
            first_name: Nome do usuário

        Returns:
            dict: Dados do pagamento
        """
        try:
            # Buscar plano
            plan = self.session.query(Plan).get(plan_id)
            if not plan:
                payment_logger.error(f"Plano {plan_id} não encontrado")
                return None

            # Gerar código PIX
            pix_code = self.generate_pix_code(plan.price)
            if not pix_code:
                payment_logger.error("Falha ao gerar código PIX")
                return None

            # Gerar QR Code base64
            qr_base64 = self.generate_qr_code_base64(pix_code)

            # Criar transação
            transaction_id = str(uuid.uuid4())

            # Data de expiração (30 minutos)
            expires_at = datetime.now() + timedelta(minutes=30)

            # Salvar pagamento
            payment = PixPayment(
                user_id=user_id,
                plan_id=plan_id,
                amount=plan.price,
                transaction_id=transaction_id,
                pix_code=pix_code,
                pix_qr_code=qr_base64,
                expires_at=expires_at,
                status='pending'
            )

            self.session.add(payment)

            # Criar ou atualizar assinatura do usuário
            sub = self.session.query(UserSubscription).filter_by(user_id=user_id).first()
            if not sub:
                sub = UserSubscription(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    is_active=False
                )
                self.session.add(sub)

            self.session.commit()

            payment_logger.info(f"✅ Pagamento criado: {transaction_id} - R${plan.price}")

            return {
                'payment_id': payment.id,
                'transaction_id': transaction_id,
                'pix_code': pix_code,
                'pix_qr_code': qr_base64,
                'amount': plan.price,
                'expires_at': expires_at,
                'plan': {
                    'name': plan.name,
                    'days': plan.days,
                    'description': plan.description
                }
            }

        except Exception as e:
            payment_logger.error(f"❌ Erro ao criar pagamento: {e}")
            import traceback
            traceback.print_exc()
            self.session.rollback()
            return None

    async def check_payment(self, transaction_id: str) -> bool:
        """
        Verifica status do pagamento

        Args:
            transaction_id: ID da transação

        Returns:
            bool: True se pago
        """
        try:
            payment = self.session.query(PixPayment).filter_by(transaction_id=transaction_id).first()

            if not payment:
                payment_logger.error(f"Pagamento não encontrado: {transaction_id}")
                return False

            # Verificar se expirou
            if payment.expires_at and payment.expires_at < datetime.now() and payment.status == 'pending':
                payment.status = 'expired'
                self.session.commit()
                payment_logger.info(f"⏰ Pagamento expirado: {transaction_id}")
                return False

            # Se já está pago, retornar True
            if payment.status == 'paid':
                return True

            # Em produção, integrar com webhook do gateway
            # Por enquanto, simulamos pagamento após 30 segundos para teste
            if payment.created_at < datetime.now() - timedelta(seconds=30):
                payment.status = 'paid'
                payment.paid_at = datetime.now()

                # Ativar assinatura
                plan = payment.plan
                sub = self.session.query(UserSubscription).filter_by(user_id=payment.user_id).first()

                if plan.days == 9999:  # Vitalício
                    sub.expires_at = datetime(2099, 12, 31)
                else:
                    sub.expires_at = datetime.now() + timedelta(days=plan.days)

                sub.is_active = True
                sub.plan_id = plan.id

                self.session.commit()
                payment_logger.info(f"🎉 Pagamento confirmado! Usuário {payment.user_id}")
                return True

            return False

        except Exception as e:
            payment_logger.error(f"❌ Erro ao verificar pagamento: {e}")
            return False

    def get_user_subscription(self, user_id: int) -> dict:
        """
        Retorna assinatura do usuário

        Args:
            user_id: ID do usuário

        Returns:
            dict: Dados da assinatura
        """
        try:
            sub = self.session.query(UserSubscription).filter_by(user_id=user_id).first()

            if not sub:
                return {
                    'is_active': False,
                    'days_remaining': 0,
                    'status_text': '❌ Sem assinatura'
                }

            # Verificar se expirou
            if sub.expires_at and sub.expires_at < datetime.now() and sub.expires_at.year < 2099:
                sub.is_active = False
                self.session.commit()

            plan = sub.plan if sub.plan_id else None

            # Texto do status
            if not sub.is_active:
                status_text = "❌ Inativo"
            elif sub.expires_at and sub.expires_at.year > 2099:
                status_text = "👑 Vitalício"
            else:
                days = max(0, (sub.expires_at - datetime.now()).days) if sub.expires_at else 0
                status_text = f"✅ Ativo ({days} dias)"

            return {
                'is_active': sub.is_active,
                'days_remaining': max(0, (sub.expires_at - datetime.now()).days) if sub.expires_at else 0,
                'status_text': status_text,
                'expires_at': sub.expires_at,
                'plan_name': plan.name if plan else 'Desconhecido',
                'plan_days': plan.days if plan else 0
            }

        except Exception as e:
            payment_logger.error(f"Erro ao buscar assinatura: {e}")
            return {
                'is_active': False,
                'days_remaining': 0,
                'status_text': '❌ Erro'
            }

    def close(self):
        """Fecha a sessão"""
        if self.session:
            self.session.close()
