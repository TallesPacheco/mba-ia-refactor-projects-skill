from db.connection import get_db
from services import relatorio_service


def get_relatorio_vendas():
    return relatorio_service.relatorio_vendas(get_db())
