import hmac
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadData, URLSafeTimedSerializer

from errors import ForbiddenError, UnauthorizedError

ADMIN_TOKEN_HEADER = "X-Admin-Token"
TOKEN_SALT = "auth-token"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=TOKEN_SALT)


def issue_token(usuario_id):
    """Token assinado com SECRET_KEY; o portador não consegue forjar outro usuário."""
    return _serializer().dumps({"sub": usuario_id})


def verify_token(token):
    if not token:
        return None
    try:  # BadData cobre BadSignature, SignatureExpired e BadPayload
        dados = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except BadData:
        return None
    sub = dados.get("sub") if isinstance(dados, dict) else None
    return sub if isinstance(sub, int) else None


def is_admin_request():
    token = request.headers.get(ADMIN_TOKEN_HEADER, "").encode()
    # bytes: compare_digest com str não-ASCII lança TypeError (viraria 500)
    esperado = current_app.config["ADMIN_TOKEN"].encode()
    return bool(token and esperado) and hmac.compare_digest(token, esperado)


def _bearer_token():
    return request.headers.get("Authorization", "").removeprefix("Bearer ").strip()


def require_admin(view):
    """Somente o header X-Admin-Token. ADMIN_TOKEN vazio = admin desabilitado."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_admin_request():
            raise UnauthorizedError("Não autorizado")
        g.is_admin = True
        g.usuario_id = None
        return view(*args, **kwargs)

    return wrapper


def require_auth(view):
    """Aceita o token assinado do login (Authorization: Bearer) ou o header de admin."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        g.is_admin = is_admin_request()
        g.usuario_id = None if g.is_admin else verify_token(_bearer_token())
        if not g.is_admin and g.usuario_id is None:
            raise UnauthorizedError("Não autorizado")
        return view(*args, **kwargs)

    return wrapper


def exigir_dono_ou_admin(usuario_id):
    """Usar dentro de rota decorada com require_auth."""
    if not g.get("is_admin") and g.get("usuario_id") != usuario_id:
        raise ForbiddenError("Acesso negado")
