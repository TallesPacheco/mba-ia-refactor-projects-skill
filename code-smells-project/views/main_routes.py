from flask import Blueprint, jsonify

from controllers import health_controller
from models.constants import APP_VERSION

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": APP_VERSION,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


@main_bp.route("/health", methods=["GET"])
def health_check():
    body, status = health_controller.get_health()
    return jsonify(body), status
