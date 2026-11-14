import logging
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from errors import ConflictError, UnauthorizedError
from models import usuario_model

logger = logging.getLogger(__name__)
_HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def cadastrar(conn, nome, email, senha):
    if usuario_model.email_existe(conn, email):
        raise ConflictError("Email já cadastrado")
    try:
        usuario_id = usuario_model.criar(conn, nome, email, generate_password_hash(senha))
    except sqlite3.IntegrityError:
        raise ConflictError("Email já cadastrado")
    logger.info("Usuário criado usuario_id=%s", usuario_id)
    return usuario_id


def autenticar(conn, email, senha):
    row = usuario_model.buscar_credenciais_por_email(conn, email)
    if row is None or not _senha_confere(row, senha):
        logger.info("Login falhou")
        raise UnauthorizedError("Email ou senha inválidos", extra={"sucesso": False})
    logger.info("Login bem-sucedido usuario_id=%s", row["id"])
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}


def _senha_confere(row, senha):
    """Allowlist: só formatos de hash conhecidos autenticam. Qualquer outro valor
    armazenado (texto puro, formato futuro não previsto) falha em vez de ser comparado."""
    armazenada = row["senha"] or ""
    if not armazenada.startswith(_HASH_PREFIXES):
        logger.warning("Formato de senha não reconhecido para usuario_id=%s", row["id"])
        return False
    return check_password_hash(armazenada, senha)
