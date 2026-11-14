"""Regras de negócio e persistência de categorias."""
import logging

from database import commit, db
from errors import NotFoundError
from models.category import Category
from models.task import Task

logger = logging.getLogger(__name__)


def get_category(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        raise NotFoundError('Categoria não encontrada')
    return category


def list_categories_with_task_count():
    stmt = (
        db.select(Category, db.func.count(Task.id))
        .outerjoin(Task, Task.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.id)
    )
    return db.session.execute(stmt).all()


def create_category(fields):
    category = Category(**fields)
    db.session.add(category)
    commit('Erro ao criar categoria')
    logger.info('Categoria criada id=%s', category.id)
    return category


def update_category(category, changes):
    for key, value in changes.items():
        setattr(category, key, value)
    commit('Erro ao atualizar')
    return category


def delete_category(category):
    """Remove a categoria; as tasks associadas ficam com category_id nulo (comportamento original)."""
    category_id = category.id
    db.session.delete(category)
    commit('Erro ao deletar')
    logger.info('Categoria deletada id=%s', category_id)
