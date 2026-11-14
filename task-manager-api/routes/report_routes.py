from flask import Blueprint, jsonify

from controllers import report_controller
from middlewares.auth import ensure_owner_or_admin, require_auth

report_bp = Blueprint('reports', __name__)


# O resumo expõe nomes de usuários em `user_productivity`: exige credencial.
@report_bp.route('/reports/summary', methods=['GET'])
@require_auth
def summary_report():
    return jsonify(report_controller.summary_report()), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
@require_auth
def user_report(user_id):
    ensure_owner_or_admin(user_id)
    return jsonify(report_controller.user_report(user_id)), 200
