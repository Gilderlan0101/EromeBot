#!/usr/bin/env python3
"""
Configuração dos planos de assinatura
"""

# Adicionar diretório raiz ao path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.models import Plan
from database.models import init_db

# Planos pré-definidos (11.83 e 22.82 vitalício)
PLANS = [
    {
        'name': 'Plano 11.83',
        'description': 'Acesso por 11 dias',
        'price': 11.83,
        'days': 11,
        'features': 'Acesso completo por 11 dias,Conteúdo exclusivo,Suporte prioritário'
    },
    {
        'name': 'Plano 22.82',
        'description': 'Acesso VITALÍCIO',
        'price': 22.82,
        'days': 9999,
        'features': 'Acesso VITALÍCIO,Conteúdo exclusivo,Suporte VIP,Desconto especial'
    }
]

def init_plans():
    """Inicializa os planos no banco de dados"""
    session = init_db()
    try:
        for plan_data in PLANS:
            # Verificar se já existe
            existing = session.query(Plan).filter_by(name=plan_data['name']).first()
            if not existing:
                plan = Plan(**plan_data)
                session.add(plan)
                print(f"✅ Plano criado: {plan_data['name']}")
            else:
                # Atualizar dados existentes
                for key, value in plan_data.items():
                    setattr(existing, key, value)
                print(f"🔄 Plano atualizado: {plan_data['name']}")

        session.commit()
        print("🎯 Planos inicializados com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao inicializar planos: {e}")
        session.rollback()
    finally:
        session.close()

def get_plans():
    """Retorna lista de planos ativos"""
    session = init_db()
    try:
        plans = session.query(Plan).filter_by(is_active=True).all()
        return plans
    finally:
        session.close()

def get_plan(plan_id):
    """Retorna um plano específico"""
    session = init_db()
    try:
        return session.query(Plan).get(plan_id)
    finally:
        session.close()


if __name__ == '__main__':
    init_plans()
