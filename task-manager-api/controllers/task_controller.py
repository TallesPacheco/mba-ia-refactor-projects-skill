"""Casos de uso de tasks: valida a entrada, chama o service e devolve dados serializáveis."""
from services import task_service
from utils.helpers import utcnow
from validators.task_validator import (
    CREATE_DATE_ERROR,
    UPDATE_DATE_ERROR,
    parse_due_date,
    validate_new_task,
    validate_search_params,
    validate_task_update,
)


def list_tasks():
    now = utcnow()
    result = []
    for task in task_service.list_tasks_with_relations():
        data = task.to_dict()
        data['overdue'] = task.is_overdue(now)
        data['user_name'] = task.user.name if task.user else None
        data['category_name'] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id):
    task = task_service.get_task(task_id)
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data


def create_task(payload):
    fields = validate_new_task(payload)
    task_service.ensure_references(fields['user_id'], fields['category_id'])
    fields['due_date'] = parse_due_date(fields['due_date'], CREATE_DATE_ERROR)
    return task_service.create_task(fields).to_dict()


def update_task(task_id, payload):
    task = task_service.get_task(task_id)
    changes = validate_task_update(payload)
    task_service.ensure_references(changes.get('user_id'), changes.get('category_id'))
    if 'due_date' in changes:
        changes['due_date'] = parse_due_date(changes['due_date'], UPDATE_DATE_ERROR)
    return task_service.update_task(task, changes).to_dict()


def delete_task(task_id):
    task_service.delete_task(task_service.get_task(task_id))
    return {'message': 'Task deletada com sucesso'}


def search_tasks(args):
    params = validate_search_params(args)
    return [task.to_dict() for task in task_service.search_tasks(**params)]


def task_stats():
    return task_service.task_stats()
