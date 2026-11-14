"""Funções puras genéricas (sem regra de negócio)."""
from datetime import datetime, timezone


def utcnow():
    """UTC "naive", compatível com as colunas DateTime do SQLite e com o formato serializado."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def localnow():
    """Hora local do servidor. Usada só pelo `timestamp` de GET /health, que é contrato
    da API desde a versão original; todo o resto do sistema usa `utcnow()`."""
    return datetime.now()


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def format_datetime(value):
    return str(value) if value else None
