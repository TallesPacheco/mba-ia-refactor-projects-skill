import logging
import sqlite3

from db.connection import get_db, get_readonly_db
from errors import ValidationError
from models import admin_model

logger = logging.getLogger(__name__)


def reset_database():
    admin_model.resetar(get_db())
    logger.warning("BANCO DE DADOS RESETADO")


def run_query(dados):
    if not isinstance(dados, dict):
        dados = {}
    query = dados.get("sql", "")
    if not query:
        raise ValidationError("Query não informada")
    if not isinstance(query, str) or not query.strip().upper().startswith("SELECT"):
        raise ValidationError("Apenas consultas SELECT são permitidas")
    try:
        # Conexão somente leitura: nenhuma escrita é possível mesmo que o SELECT tente.
        return admin_model.consultar(get_readonly_db(), query)
    except sqlite3.Error:
        logger.warning("Query admin inválida")
        raise ValidationError("Query inválida")
