from flask import Blueprint, jsonify, request

from controllers import usuario_controller
from middlewares.auth import exigir_dono_ou_admin, issue_token, require_admin, require_auth

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.route("/usuarios", methods=["GET"])
@require_admin
def listar_usuarios():
    return jsonify({"dados": usuario_controller.list_usuarios(), "sucesso": True}), 200


@usuario_bp.route("/usuarios/<int:usuario_id>", methods=["GET"])
@require_auth
def buscar_usuario(usuario_id):
    exigir_dono_ou_admin(usuario_id)
    return jsonify({"dados": usuario_controller.get_usuario(usuario_id), "sucesso": True}), 200


@usuario_bp.route("/usuarios", methods=["POST"])
def criar_usuario():
    usuario_id = usuario_controller.create_usuario(request.get_json(silent=True))
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


@usuario_bp.route("/login", methods=["POST"])
def login():
    usuario = usuario_controller.login(request.get_json(silent=True))
    return jsonify({
        "dados": usuario,
        "token": issue_token(usuario["id"]),
        "sucesso": True,
        "mensagem": "Login OK",
    }), 200
