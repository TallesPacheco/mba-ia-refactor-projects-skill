import re

from errors import ValidationError
from models.constants import DEFAULT_ROLE, EMAIL_REGEX, MIN_PASSWORD_LENGTH, VALID_ROLES
from validators.common import require_payload

_EMAIL_PATTERN = re.compile(EMAIL_REGEX)


def validate_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValidationError('Nome é obrigatório')
    return name


def validate_email(email):
    if not isinstance(email, str) or not _EMAIL_PATTERN.match(email):
        raise ValidationError('Email inválido')
    return email


def validate_password(password, too_short_message):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(too_short_message)
    return password


def validate_role(role):
    if not isinstance(role, str) or role not in VALID_ROLES:
        raise ValidationError('Role inválido')
    return role


def validate_active(active):
    if not isinstance(active, bool):
        raise ValidationError('Campo active deve ser booleano')
    return active


def validate_new_user(data):
    """Campos obrigatórios e formato de POST /users (conflito de e-mail e role vêm depois)."""
    require_payload(data)
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    return {
        'name': validate_name(name),
        'email': validate_email(email),
        'password': validate_password(password, 'Senha deve ter no mínimo 4 caracteres'),
        'role': data.get('role', DEFAULT_ROLE),
    }


def validate_login(data):
    require_payload(data)
    email = data.get('email')
    password = data.get('password')
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError('Email e senha são obrigatórios')
    return email, password
