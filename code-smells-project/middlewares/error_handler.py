import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from errors import AppError

logger = logging.getLogger(__name__)
ERROR_KEY = "erro"  # mesma chave de erro usada pela API original

# A API responde em português; as descrições padrão do Werkzeug vêm em inglês.
MENSAGENS_HTTP = {
    404: "Rota não encontrada",
    405: "Método não permitido para esta rota",
}


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        body = {ERROR_KEY: err.message}
        body.update(err.extra)
        return jsonify(body), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({ERROR_KEY: MENSAGENS_HTTP.get(err.code, err.description)}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: "Erro interno do servidor"}), 500
