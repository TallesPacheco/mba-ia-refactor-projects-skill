from db.connection import get_db
from models import pedido_model
from services.notification_service import Notifier
from services.pedido_service import PedidoService
from validators.pedido_validator import validar_pedido, validar_status


def _service():
    return PedidoService(get_db(), Notifier())


def create_pedido(dados, autorizar=None):
    """`autorizar` recebe o usuario_id do corpo e decide se o chamador pode pedir por ele
    (injetado pela rota para manter o controller sem dependência do contexto do Flask)."""
    pedido = validar_pedido(dados)
    if autorizar is not None:
        autorizar(pedido["usuario_id"])
    return _service().criar(pedido["usuario_id"], pedido["itens"])


def list_pedidos():
    return pedido_model.listar(get_db())


def list_pedidos_usuario(usuario_id):
    return pedido_model.listar(get_db(), usuario_id=usuario_id)


def update_status_pedido(pedido_id, dados):
    novo_status = validar_status(dados)
    _service().atualizar_status(pedido_id, novo_status)
