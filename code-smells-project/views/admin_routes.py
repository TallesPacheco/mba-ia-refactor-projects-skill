from flask import Blueprint, jsonify, request

from controllers import admin_controller
from middlewares.auth import require_admin

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_admin
def reset_database():
    admin_controller.reset_database()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


@admin_bp.route("/admin/query", methods=["POST"])
@require_admin
def executar_query():
    dados = admin_controller.run_query(request.get_json(silent=True))
    return jsonify({"dados": dados, "sucesso": True}), 200
