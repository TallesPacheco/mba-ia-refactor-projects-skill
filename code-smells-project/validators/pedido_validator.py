from errors import ValidationError
from models.constants import STATUS_PEDIDO_VALIDOS
from validators.common import is_int


def validar_pedido(dados):
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not is_int(usuario_id):
        raise ValidationError("Usuario ID inválido")
    if not isinstance(itens, list):
        raise ValidationError("Itens do pedido devem ser uma lista")
    for item in itens:
        if (
            not isinstance(item, dict)
            or not is_int(item.get("produto_id"))
            or not is_int(item.get("quantidade"))
            or item["quantidade"] <= 0
        ):
            raise ValidationError("Item de pedido inválido: produto_id e quantidade (> 0) inteiros são obrigatórios")
    itens_normalizados = [{"produto_id": item["produto_id"], "quantidade": item["quantidade"]} for item in itens]
    return {"usuario_id": usuario_id, "itens": itens_normalizados}


def validar_status(dados):
    if not isinstance(dados, dict):
        dados = {}
    novo_status = dados.get("status", "")
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
