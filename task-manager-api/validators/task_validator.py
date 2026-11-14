from datetime import datetime

from errors import ValidationError
from models.constants import (
    DEFAULT_PRIORITY,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    TASK_DATE_FORMAT,
    TASK_STATUS_PENDING,
    VALID_TASK_STATUSES,
)
from validators.common import (
    is_number,
    parse_int_param,
    require_payload,
    validate_optional_id,
    validate_optional_text,
)

CREATE_DATE_ERROR = 'Formato de data inválido. Use YYYY-MM-DD'
UPDATE_DATE_ERROR = 'Formato de data inválido'
DESCRIPTION_ERROR = 'Descrição inválida'
USER_ID_ERROR = 'Usuário inválido'
CATEGORY_ID_ERROR = 'Categoria inválida'


def _validate_title(title):
    if not isinstance(title, str):
        raise ValidationError('Título inválido')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')
    return title


def _validate_status(status):
    if not isinstance(status, str) or status not in VALID_TASK_STATUSES:
        raise ValidationError('Status inválido')
    return status


def _validate_priority(priority):
    if not is_number(priority):
        raise ValidationError('Prioridade inválida')
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    return priority


def _normalize_tags(tags):
    if tags is None:
        return None
    if isinstance(tags, list):
        return ','.join(str(tag) for tag in tags)
    if isinstance(tags, str):
        return tags
    raise ValidationError('Tags inválidas')


def parse_due_date(value, error_message):
    if not value:
        return None
    try:
        return datetime.strptime(value, TASK_DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(error_message)


def validate_new_task(data):
    """Valida o corpo de POST /tasks na mesma ordem do contrato original.

    `due_date` é devolvido cru: a conversão acontece depois, no controller, para manter a
    mesma ordem de erros (referência inexistente antes de data mal formatada).
    """
    require_payload(data)
    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    tags = data.get('tags')
    return {
        'title': _validate_title(title),
        'description': validate_optional_text(data.get('description', ''), DESCRIPTION_ERROR),
        'status': _validate_status(data.get('status', TASK_STATUS_PENDING)),
        'priority': _validate_priority(data.get('priority', DEFAULT_PRIORITY)),
        'user_id': validate_optional_id(data.get('user_id'), USER_ID_ERROR),
        'category_id': validate_optional_id(data.get('category_id'), CATEGORY_ID_ERROR),
        'due_date': data.get('due_date'),
        'tags': _normalize_tags(tags) if tags else None,
    }


def validate_task_update(data):
    """Valida o corpo de PUT /tasks/<id>; só as chaves presentes entram no resultado."""
    require_payload(data)
    changes = {}
    if 'title' in data:
        changes['title'] = _validate_title(data['title'])
    if 'description' in data:
        changes['description'] = validate_optional_text(data['description'], DESCRIPTION_ERROR)
    if 'status' in data:
        changes['status'] = _validate_status(data['status'])
    if 'priority' in data:
        changes['priority'] = _validate_priority(data['priority'])
    if 'user_id' in data:
        changes['user_id'] = validate_optional_id(data['user_id'], USER_ID_ERROR)
    if 'category_id' in data:
        changes['category_id'] = validate_optional_id(data['category_id'], CATEGORY_ID_ERROR)
    # `due_date` segue cru: convertido pelo controller (mesma ordem de erros do original).
    if 'due_date' in data:
        changes['due_date'] = data['due_date']
    if 'tags' in data:
        changes['tags'] = _normalize_tags(data['tags'])
    return changes


def validate_search_params(args):
    return {
        'query': args.get('q', ''),
        'status': args.get('status', ''),
        'priority': parse_int_param(args.get('priority', ''), 'Prioridade inválida'),
        'user_id': parse_int_param(args.get('user_id', ''), 'Usuário inválido'),
    }
