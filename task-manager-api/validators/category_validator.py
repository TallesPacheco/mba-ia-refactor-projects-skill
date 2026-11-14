from errors import ValidationError
from models.constants import COLOR_LENGTH, DEFAULT_CATEGORY_COLOR
from validators.common import require_payload


def _validate_name(name):
    if not name or not isinstance(name, str):
        raise ValidationError('Nome é obrigatório')
    return name


def _validate_color(color):
    if not isinstance(color, str) or len(color) != COLOR_LENGTH or not color.startswith('#'):
        raise ValidationError('Cor inválida')
    return color


def validate_new_category(data):
    require_payload(data)
    return {
        'name': _validate_name(data.get('name')),
        'description': data.get('description', ''),
        'color': _validate_color(data.get('color', DEFAULT_CATEGORY_COLOR)),
    }


def validate_category_update(data):
    # PUT /categories/<id> sempre aceitou `{}` (sem alterações); só corpo não-objeto é rejeitado.
    require_payload(data, allow_empty=True)
    changes = {}
    if 'name' in data:
        changes['name'] = _validate_name(data['name'])
    if 'description' in data:
        changes['description'] = data['description']
    if 'color' in data:
        changes['color'] = _validate_color(data['color'])
    return changes
