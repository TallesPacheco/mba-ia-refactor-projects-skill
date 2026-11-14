import logging
import sqlite3

from flask import current_app

from db.connection import get_db
from models import pedido_model, produto_model, usuario_model
from models.constants import APP_VERSION

logger = logging.getLogger(__name__)


def get_health():
    """Retorna (corpo, status). Não expõe segredos nem config interna."""
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        counts = {
            "produtos": produto_model.contar(conn),
            "usuarios": usuario_model.contar(conn),
            "pedidos": pedido_model.contar(conn),
        }
    except sqlite3.Error:
        logger.exception("Health check falhou")
        return {"status": "erro", "detalhes": "Banco de dados indisponível"}, 500
    return {
        "status": "ok",
        "database": "connected",
        "counts": counts,
        "versao": APP_VERSION,
        "ambiente": current_app.config["APP_ENV"],
    }, 200
