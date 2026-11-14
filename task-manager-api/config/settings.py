"""Configuração da aplicação lida de variáveis de ambiente.

Os defaults servem apenas para desenvolvimento local e não são segredos reais.
Em produção (APP_ENV=production) os segredos obrigatórios precisam vir do ambiente.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name, default="0"):
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# Defaults públicos: servem só para desenvolvimento e são recusados em produção.
DEV_SECRET_KEY = "dev-only-insecure-key"
DEV_ADMIN_TOKEN = "dev-admin-token"


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development")

    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", DEV_ADMIN_TOKEN)
    ADMIN_TOKEN_HEADER = "X-Admin-Token"
    # Validade do token assinado devolvido por POST /login, em segundos.
    TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "3600"))

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = _env_bool("FLASK_DEBUG")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))

    CORS_ORIGINS = _env_list("CORS_ORIGINS", "http://localhost:3000")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

    REQUIRED_IN_PRODUCTION = ("SECRET_KEY", "ADMIN_TOKEN")

    @classmethod
    def validate(cls):
        if cls.APP_ENV != "production":
            return
        missing = [key for key in cls.REQUIRED_IN_PRODUCTION if not os.environ.get(key)]
        if missing:
            raise RuntimeError(f"Variáveis obrigatórias ausentes em produção: {', '.join(missing)}")
        # O SECRET_KEY assina os tokens de login: um default público permite forjá-los.
        if cls.SECRET_KEY == DEV_SECRET_KEY or cls.ADMIN_TOKEN == DEV_ADMIN_TOKEN:
            raise RuntimeError("SECRET_KEY e ADMIN_TOKEN não podem usar os defaults de desenvolvimento em produção")
        if cls.DEBUG:
            raise RuntimeError("FLASK_DEBUG não pode estar ligado em produção")
