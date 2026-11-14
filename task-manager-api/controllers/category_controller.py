"""Casos de uso de categorias."""
from services import category_service
from validators.category_validator import validate_category_update, validate_new_category


def list_categories():
    result = []
    for category, task_count in category_service.list_categories_with_task_count():
        data = category.to_dict()
        data['task_count'] = task_count
        result.append(data)
    return result


def create_category(payload):
    return category_service.create_category(validate_new_category(payload)).to_dict()


def update_category(category_id, payload):
    category = category_service.get_category(category_id)
    changes = validate_category_update(payload)
    return category_service.update_category(category, changes).to_dict()


def delete_category(category_id):
    category_service.delete_category(category_service.get_category(category_id))
    return {'message': 'Categoria deletada'}
