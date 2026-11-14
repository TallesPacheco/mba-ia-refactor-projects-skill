from errors import ValidationError

INVALID_PAYLOAD_MESSAGE = 'Dados inválidos'


def require_payload(data, allow_empty=False):
    """Garante corpo JSON em objeto. `allow_empty` preserva rotas que aceitavam `{}`."""
    if not isinstance(data, dict):
        raise ValidationError(INVALID_PAYLOAD_MESSAGE)
    if not data and not allow_empty:
        raise ValidationError(INVALID_PAYLOAD_MESSAGE)
    return data


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_int_param(raw, message):
    """Converte query param opcional em int; vazio vira None."""
    if raw in (None, ''):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ValidationError(message)


def validate_optional_id(value, message):
    """Id de referência opcional: `None` ou inteiro. Evita que dict/list/str chegue ao driver."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(message)
    return value


def validate_optional_text(value, message):
    """Campo de texto opcional: `None` ou string."""
    if value is None or isinstance(value, str):
        return value
    raise ValidationError(message)
