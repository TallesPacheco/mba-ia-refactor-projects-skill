"""Regras de negócio e persistência de tasks."""
import logging

from sqlalchemy.orm import selectinload

from database import commit, db
from errors import NotFoundError
from models.category import Category
from models.constants import CLOSED_TASK_STATUSES, VALID_TASK_STATUSES
from models.task import Task
from models.user import User
from utils.helpers import calculate_percentage, utcnow

logger = logging.getLogger(__name__)


def overdue_filter(now):
    """Critério SQL equivalente a Task.is_overdue()."""
    return db.and_(
        Task.due_date.is_not(None),
        Task.due_date < now,
        Task.status.not_in(CLOSED_TASK_STATUSES),
    )


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        raise NotFoundError('Task não encontrada')
    return task


def list_tasks_with_relations():
    stmt = (
        db.select(Task)
        .options(selectinload(Task.user), selectinload(Task.category))
        .order_by(Task.id)
    )
    return db.session.execute(stmt).scalars().all()


def ensure_references(user_id, category_id):
    if user_id and db.session.get(User, user_id) is None:
        raise NotFoundError('Usuário não encontrado')
    if category_id and db.session.get(Category, category_id) is None:
        raise NotFoundError('Categoria não encontrada')


def create_task(fields):
    task = Task(**fields)
    db.session.add(task)
    commit('Erro ao criar task')
    logger.info('Task criada id=%s', task.id)
    return task


def update_task(task, changes):
    for key, value in changes.items():
        setattr(task, key, value)
    task.updated_at = utcnow()
    commit('Erro ao atualizar')
    logger.info('Task atualizada id=%s', task.id)
    return task


def delete_task(task):
    task_id = task.id
    db.session.delete(task)
    commit('Erro ao deletar')
    logger.info('Task deletada id=%s', task_id)


def search_tasks(query='', status='', priority=None, user_id=None):
    stmt = db.select(Task)
    if query:
        pattern = f'%{query}%'
        stmt = stmt.where(db.or_(Task.title.like(pattern), Task.description.like(pattern)))
    if status:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if user_id is not None:
        stmt = stmt.where(Task.user_id == user_id)
    return db.session.execute(stmt.order_by(Task.id)).scalars().all()


def count_tasks(*criteria):
    stmt = db.select(db.func.count(Task.id))
    if criteria:
        stmt = stmt.where(*criteria)
    return db.session.scalar(stmt)


def count_by_status():
    rows = db.session.execute(db.select(Task.status, db.func.count(Task.id)).group_by(Task.status)).all()
    counts = dict(rows)
    return {status: counts.get(status, 0) for status in VALID_TASK_STATUSES}


def task_stats():
    total = count_tasks()
    by_status = count_by_status()
    return {
        'total': total,
        **by_status,
        'overdue': count_tasks(overdue_filter(utcnow())),
        'completion_rate': calculate_percentage(by_status['done'], total),
    }
