"""Autenticação e autorização.

Duas credenciais, ambas verificadas aqui:
- `Authorization: Bearer <token>` — token assinado emitido por `POST /login` (HMAC sobre
  `SECRET_KEY`, com expiração `TOKEN_MAX_AGE`). Identifica o usuário.
- `X-Admin-Token` — token estático de administração (`ADMIN_TOKEN`). Não identifica usuário.
"""
import hmac
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadData, URLSafeTimedSerializer

from errors import ForbiddenError, UnauthorizedError

UNAUTHORIZED_MESSAGE = 'Não autorizado'
FORBIDDEN_MESSAGE = 'Acesso negado'
TOKEN_SALT = 'auth-token'
BEARER_PREFIX = 'Bearer '


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=TOKEN_SALT)


def issue_token(user_id):
    """Token assinado para o usuário; o campo `token` do login continua sendo uma string."""
    return _serializer().dumps({'sub': user_id})


def verify_token(token):
    """Devolve o id do usuário ou None quando a assinatura é inválida ou o token expirou."""
    try:
        # BadData cobre BadSignature, SignatureExpired e BadPayload.
        data = _serializer().loads(token, max_age=current_app.config['TOKEN_MAX_AGE'])
    except BadData:
        return None
    return data.get('sub') if isinstance(data, dict) else None


def has_admin_token():
    expected = current_app.config.get('ADMIN_TOKEN') or ''
    header = current_app.config.get('ADMIN_TOKEN_HEADER', 'X-Admin-Token')
    provided = request.headers.get(header, '')
    if not expected:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


def current_identity():
    """Resolve a credencial da requisição uma única vez e guarda em `flask.g`."""
    if 'is_admin' not in g:
        g.is_admin = has_admin_token()
        header = request.headers.get('Authorization', '')
        token = header[len(BEARER_PREFIX):].strip() if header.startswith(BEARER_PREFIX) else ''
        g.user_id = verify_token(token) if token else None
    return g.is_admin, g.user_id


def ensure_admin(is_admin):
    if not is_admin:
        raise UnauthorizedError(UNAUTHORIZED_MESSAGE)


def ensure_owner_or_admin(user_id):
    """Só o próprio usuário autenticado ou um administrador seguem adiante."""
    is_admin, current_user_id = current_identity()
    if not is_admin and current_user_id != user_id:
        raise ForbiddenError(FORBIDDEN_MESSAGE)


def require_auth(view):
    """Exige token de login válido ou token de administração."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        is_admin, user_id = current_identity()
        if not is_admin and user_id is None:
            raise UnauthorizedError(UNAUTHORIZED_MESSAGE)
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        ensure_admin(has_admin_token())
        return view(*args, **kwargs)

    return wrapper
