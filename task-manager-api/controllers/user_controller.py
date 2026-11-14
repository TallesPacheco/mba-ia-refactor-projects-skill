"""Casos de uso de usuários e login."""
from middlewares.auth import ensure_admin, issue_token
from models.constants import DEFAULT_ROLE
from services import user_service
from validators.common import require_payload
from validators.user_validator import (
    validate_active,
    validate_email,
    validate_login,
    validate_name,
    validate_new_user,
    validate_password,
    validate_role,
)


def list_users():
    result = []
    for user, task_count in user_service.list_users_with_task_count():
        data = user.to_dict()
        data['task_count'] = task_count
        result.append(data)
    return result


def get_user(user_id):
    user = user_service.get_user(user_id)
    data = user.to_dict()
    data['tasks'] = [task.to_dict() for task in user_service.list_user_tasks(user_id)]
    return data


def create_user(payload, is_admin):
    fields = validate_new_user(payload)
    user_service.ensure_email_available(fields['email'])
    role = validate_role(fields['role'])
    if role != DEFAULT_ROLE:
        ensure_admin(is_admin)  # só admin pode criar usuários com papel elevado
    return user_service.create_user(fields['name'], fields['email'], fields['password'], role).to_dict()


def update_user(user_id, payload, is_admin):
    user = user_service.get_user(user_id)
    require_payload(payload)
    changes = {}
    if 'name' in payload:
        changes['name'] = validate_name(payload['name'])
    if 'email' in payload:
        email = validate_email(payload['email'])
        user_service.ensure_email_available(email, exclude_user_id=user.id)
        changes['email'] = email
    if 'password' in payload:
        changes['password'] = validate_password(payload['password'], 'Senha muito curta')
    if 'role' in payload:
        changes['role'] = validate_role(payload['role'])
        ensure_admin(is_admin)  # alterar papel exige admin
    if 'active' in payload:
        changes['active'] = validate_active(payload['active'])
    return user_service.update_user(user, changes).to_dict()


def delete_user(user_id):
    user_service.delete_user(user_service.get_user(user_id))
    return {'message': 'Usuário deletado com sucesso'}


def list_user_tasks(user_id):
    user_service.get_user(user_id)
    return [task.to_summary_dict() for task in user_service.list_user_tasks(user_id)]


def login(payload):
    email, password = validate_login(payload)
    user = user_service.authenticate(email, password)
    return {
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': issue_token(user.id),
    }
