from flask import Blueprint, jsonify, request

from controllers import pedido_controller
from middlewares.auth import exigir_dono_ou_admin, require_admin, require_auth

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.route("/pedidos", methods=["POST"])
@require_auth
def criar_pedido():
    resultado = pedido_controller.create_pedido(request.get_json(silent=True), exigir_dono_ou_admin)
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


@pedido_bp.route("/pedidos", methods=["GET"])
@require_admin
def listar_todos_pedidos():
    return jsonify({"dados": pedido_controller.list_pedidos(), "sucesso": True}), 200


@pedido_bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
@require_auth
def listar_pedidos_usuario(usuario_id):
    exigir_dono_ou_admin(usuario_id)
    return jsonify({"dados": pedido_controller.list_pedidos_usuario(usuario_id), "sucesso": True}), 200


@pedido_bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
@require_admin
def atualizar_status_pedido(pedido_id):
    pedido_controller.update_status_pedido(pedido_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
