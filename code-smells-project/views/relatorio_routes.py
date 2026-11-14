from flask import Blueprint, jsonify

from controllers import relatorio_controller
from middlewares.auth import require_admin

relatorio_bp = Blueprint("relatorios", __name__)


@relatorio_bp.route("/relatorios/vendas", methods=["GET"])
@require_admin
def relatorio_vendas():
    return jsonify({"dados": relatorio_controller.get_relatorio_vendas(), "sucesso": True}), 200
