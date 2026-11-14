from flask import Blueprint, jsonify, request

from controllers import produto_controller
from middlewares.auth import require_admin

produto_bp = Blueprint("produtos", __name__)


@produto_bp.route("/produtos", methods=["GET"])
def listar_produtos():
    return jsonify({"dados": produto_controller.list_produtos(), "sucesso": True}), 200


@produto_bp.route("/produtos/busca", methods=["GET"])
def buscar_produtos():
    resultados = produto_controller.search_produtos(request.args)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@produto_bp.route("/produtos/<int:produto_id>", methods=["GET"])
def buscar_produto(produto_id):
    return jsonify({"dados": produto_controller.get_produto(produto_id), "sucesso": True}), 200


@produto_bp.route("/produtos", methods=["POST"])
@require_admin
def criar_produto():
    produto_id = produto_controller.create_produto(request.get_json(silent=True))
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


@produto_bp.route("/produtos/<int:produto_id>", methods=["PUT"])
@require_admin
def atualizar_produto(produto_id):
    produto_controller.update_produto(produto_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.route("/produtos/<int:produto_id>", methods=["DELETE"])
@require_admin
def deletar_produto(produto_id):
    produto_controller.delete_produto(produto_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
