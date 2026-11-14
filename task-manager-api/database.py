import logging
import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from errors import AppError

logger = logging.getLogger(__name__)

db = SQLAlchemy()


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db(app):
    """Liga a extensão ao app, ativa FKs no SQLite e cria o schema."""
    db.init_app(app)
    with app.app_context():
        event.listen(db.engine, "connect", _enable_sqlite_foreign_keys)
        import models  # noqa: F401  (registra os models antes do create_all)
        db.create_all()


def commit(error_message):
    """Confirma a unidade de trabalho; em falha faz rollback e lança AppError 500."""
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("Falha ao confirmar transação: %s", error_message)
        raise AppError(error_message, 500)
