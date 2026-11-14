"""Entry point e composition root da Task Manager API."""
import logging

from flask import Flask
from flask_cors import CORS

from config.settings import Config
from database import init_db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.system_routes import system_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


def create_app(config_class=Config):
    config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(
        level=app.config['LOG_LEVEL'],
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    CORS(app, origins=app.config['CORS_ORIGINS'])
    init_db(app)
    register_error_handlers(app)

    for blueprint in (system_bp, task_bp, user_bp, report_bp, category_bp):
        app.register_blueprint(blueprint)

    return app


# `app` em nível de módulo mantém `flask --app app run` e `from app import app` (seed) funcionando.
app = create_app()

if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=app.config['DEBUG'])
