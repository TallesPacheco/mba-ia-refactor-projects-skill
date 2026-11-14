import logging

from errors import NotFoundError, ValidationError
from models import pedido_model, produto_model, usuario_model
from models.constants import STATUS_APROVADO, STATUS_CANCELADO

logger = logging.getLogger(__name__)
_FALHA = {"sucesso": False}


class PedidoService:
    def __init__(self, conn, notifier):
        self.conn = conn
        self.notifier = notifier

    def criar(self, usuario_id, itens):
        produtos = produto_model.buscar_por_ids(self.conn, [item["produto_id"] for item in itens])
        total = 0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise ValidationError("Produto " + str(item["produto_id"]) + " não encontrado", extra=_FALHA)
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError("Estoque insuficiente para " + produto["nome"], extra=_FALHA)
            total = total + (produto["preco"] * item["quantidade"])

        if not usuario_model.existe(self.conn, usuario_id):
            raise ValidationError("Usuário não encontrado", extra=_FALHA)

        with self.conn:  # commit no sucesso, rollback em qualquer exceção
            pedido_id = pedido_model.inserir(self.conn, usuario_id, total)
            for item in itens:
                produto = produtos[item["produto_id"]]
                pedido_model.inserir_item(self.conn, pedido_id, item["produto_id"], item["quantidade"], produto["preco"])
                if not produto_model.baixar_estoque(self.conn, item["produto_id"], item["quantidade"]):
                    raise ValidationError("Estoque insuficiente para " + produto["nome"], extra=_FALHA)

        logger.info("Pedido criado pedido_id=%s", pedido_id)
        self.notifier.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def atualizar_status(self, pedido_id, novo_status):
        if not pedido_model.existe(self.conn, pedido_id):
            raise NotFoundError("Pedido não encontrado")
        pedido_model.atualizar_status(self.conn, pedido_id, novo_status)
        if novo_status == STATUS_APROVADO:
            self.notifier.pedido_aprovado(pedido_id)
        if novo_status == STATUS_CANCELADO:
            self.notifier.pedido_cancelado(pedido_id)
