import logging

from flask import Flask
from flask_cors import CORS

from config.settings import ADMIN_TOKEN_DEV, Config
from db import connection
from middlewares.error_handler import register_error_handlers
from views.admin_routes import admin_bp
from views.main_routes import main_bp
from views.pedido_routes import pedido_bp
from views.produto_routes import produto_bp
from views.relatorio_routes import relatorio_bp
from views.usuario_routes import usuario_bp

logger = logging.getLogger(__name__)


def create_app(config=None):
    config = config or Config()
    config.validate()
    logging.basicConfig(level=config.LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if config.ADMIN_TOKEN == ADMIN_TOKEN_DEV:
        logger.warning("ADMIN_TOKEN padrão de desenvolvimento em uso; defina ADMIN_TOKEN fora de dev")

    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app, origins=app.config["CORS_ORIGINS"])

    connection.init_app(app)  # teardown por requisição + schema + seed idempotente
    for blueprint in (main_bp, produto_bp, usuario_bp, pedido_bp, relatorio_bp, admin_bp):
        app.register_blueprint(blueprint)
    register_error_handlers(app)
    return app


# Sem instância em nível de módulo: importar `app` não cria mais o banco nem roda o seed.
# `flask --app app run` continua funcionando pela descoberta automática de create_app().
if __name__ == "__main__":
    app = create_app()
    logger.info("Servidor iniciado em http://%s:%s", app.config["HOST"], app.config["PORT"])
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
