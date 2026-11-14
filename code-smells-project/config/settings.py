import os

# Ambientes em que os defaults inseguros de desenvolvimento são aceitos. Qualquer outro
# valor de APP_ENV (production, staging, homolog, ...) exige os segredos por variável de ambiente.
AMBIENTES_PERMISSIVOS = ("development", "test")

SECRET_KEY_DEV = "dev-only-insecure-key"
ADMIN_TOKEN_DEV = "dev-admin-token"


def _env_list(name, default):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    """Lê o ambiente no momento da instanciação (não no import), para que a factory
    possa ser chamada com variáveis definidas depois do import do módulo."""

    def __init__(self):
        self.APP_ENV = os.environ.get("APP_ENV", "development")
        self.SECRET_KEY = os.environ.get("SECRET_KEY", SECRET_KEY_DEV)
        self.DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
        self.HOST = os.environ.get("HOST", "127.0.0.1")
        self.PORT = int(os.environ.get("PORT", "5000"))
        self.DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
        self.ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", ADMIN_TOKEN_DEV)
        self.TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "3600"))
        self.CORS_ORIGINS = _env_list("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    @property
    def permissivo(self):
        return self.APP_ENV in AMBIENTES_PERMISSIVOS

    def validate(self):
        """Fora de development/test, segredos precisam ser explícitos e diferentes dos defaults públicos."""
        if self.permissivo:
            return
        problemas = []
        if self.SECRET_KEY == SECRET_KEY_DEV or not self.SECRET_KEY:
            problemas.append("SECRET_KEY")
        if self.ADMIN_TOKEN == ADMIN_TOKEN_DEV or not self.ADMIN_TOKEN:
            problemas.append("ADMIN_TOKEN")
        if problemas:
            raise RuntimeError(
                "APP_ENV=%s exige valores próprios para: %s" % (self.APP_ENV, ", ".join(problemas))
            )
        if self.DEBUG:
            raise RuntimeError("FLASK_DEBUG não pode estar ativo com APP_ENV=" + self.APP_ENV)
