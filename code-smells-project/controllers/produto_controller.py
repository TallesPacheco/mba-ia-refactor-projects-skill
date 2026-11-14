import logging

from db.connection import get_db
from errors import NotFoundError
from models import produto_model
from validators.produto_validator import validar_filtros_busca, validar_produto

logger = logging.getLogger(__name__)


def list_produtos():
    produtos = produto_model.listar(get_db())
    logger.info("Listando %s produtos", len(produtos))
    return produtos


def get_produto(produto_id):
    produto = produto_model.buscar_por_id(get_db(), produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado", extra={"sucesso": False})
    return produto


def search_produtos(args):
    filtros = validar_filtros_busca(args)
    return produto_model.buscar(get_db(), **filtros)


def create_produto(dados):
    produto = validar_produto(dados)
    produto_id = produto_model.criar(get_db(), **produto)
    logger.info("Produto criado produto_id=%s", produto_id)
    return produto_id


def update_produto(produto_id, dados):
    conn = get_db()
    if not produto_model.buscar_por_id(conn, produto_id):
        raise NotFoundError("Produto não encontrado")
    produto = validar_produto(dados)
    produto_model.atualizar(conn, produto_id, **produto)


def delete_produto(produto_id):
    conn = get_db()
    if not produto_model.buscar_por_id(conn, produto_id):
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(conn, produto_id)
    logger.info("Produto deletado produto_id=%s", produto_id)
