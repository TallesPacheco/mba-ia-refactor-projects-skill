"""Regras de negócio e persistência de usuários."""
import logging

from database import commit, db
from errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from models.task import Task
from models.user import User

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS_MESSAGE = 'Credenciais inválidas'


def get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError('Usuário não encontrado')
    return user


def list_users_with_task_count():
    stmt = (
        db.select(User, db.func.count(Task.id))
        .outerjoin(Task, Task.user_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
    )
    return db.session.execute(stmt).all()


def list_user_tasks(user_id):
    stmt = db.select(Task).where(Task.user_id == user_id).order_by(Task.id)
    return db.session.execute(stmt).scalars().all()


def find_by_email(email):
    return db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()


def ensure_email_available(email, exclude_user_id=None):
    existing = find_by_email(email)
    if existing is not None and existing.id != exclude_user_id:
        raise ConflictError('Email já cadastrado')


def create_user(name, email, password, role):
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    commit('Erro ao criar usuário')
    logger.info('Usuário criado id=%s', user.id)
    return user


def update_user(user, changes):
    for key, value in changes.items():
        if key == 'password':
            user.set_password(value)
        else:
            setattr(user, key, value)
    commit('Erro ao atualizar')
    logger.info('Usuário atualizado id=%s', user.id)
    return user


def delete_user(user):
    """Apaga o usuário; as tasks dele são removidas pela cascata declarada no model."""
    user_id = user.id
    db.session.delete(user)
    commit('Erro ao deletar')
    logger.info('Usuário deletado id=%s', user_id)


def authenticate(email, password):
    user = find_by_email(email)
    if user is None or not user.check_password(password):
        raise UnauthorizedError(INVALID_CREDENTIALS_MESSAGE)
    if not user.active:
        raise ForbiddenError('Usuário inativo')
    return user
