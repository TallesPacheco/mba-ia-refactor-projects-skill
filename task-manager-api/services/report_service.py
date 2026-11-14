"""Relatórios agregados (contagens feitas no banco, sem N+1)."""
from datetime import timedelta

from database import db
from models.category import Category
from models.constants import (
    HIGH_PRIORITY_THRESHOLD,
    PRIORITY_LABELS,
    RECENT_ACTIVITY_DAYS,
    TASK_STATUS_DONE,
    VALID_TASK_STATUSES,
)
from models.task import Task
from models.user import User
from services import task_service, user_service
from utils.helpers import calculate_percentage, utcnow


def _count(model):
    return db.session.scalar(db.select(db.func.count(model.id)))


def _count_by_priority():
    rows = db.session.execute(db.select(Task.priority, db.func.count(Task.id)).group_by(Task.priority)).all()
    counts = dict(rows)
    return {label: counts.get(priority, 0) for priority, label in PRIORITY_LABELS.items()}


def _overdue_tasks(now):
    stmt = db.select(Task).where(task_service.overdue_filter(now)).order_by(Task.id)
    return [
        {
            'id': task.id,
            'title': task.title,
            'due_date': str(task.due_date),
            'days_overdue': (now - task.due_date).days,
        }
        for task in db.session.execute(stmt).scalars()
    ]


def _user_productivity():
    stmt = (
        db.select(User.id, User.name, db.func.count(Task.id), _count_if(Task.status == TASK_STATUS_DONE))
        .outerjoin(Task, Task.user_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
    )
    return [
        {
            'user_id': user_id,
            'user_name': user_name,
            'total_tasks': total,
            'completed_tasks': completed,
            'completion_rate': calculate_percentage(completed, total),
        }
        for user_id, user_name, total, completed in db.session.execute(stmt).all()
    ]


def summary_report():
    now = utcnow()
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    overdue = _overdue_tasks(now)
    return {
        'generated_at': str(now),
        'overview': {
            'total_tasks': _count(Task),
            'total_users': _count(User),
            'total_categories': _count(Category),
        },
        'tasks_by_status': task_service.count_by_status(),
        'tasks_by_priority': _count_by_priority(),
        'overdue': {
            'count': len(overdue),
            'tasks': overdue,
        },
        'recent_activity': {
            'tasks_created_last_7_days': task_service.count_tasks(Task.created_at >= since),
            'tasks_completed_last_7_days': task_service.count_tasks(
                Task.status == TASK_STATUS_DONE, Task.updated_at >= since
            ),
        },
        'user_productivity': _user_productivity(),
    }


def _count_if(criterion):
    return db.func.coalesce(db.func.sum(db.case((criterion, 1), else_=0)), 0)


def _user_statistics(user_id, now):
    """Todas as contagens do relatório individual numa única consulta agregada."""
    columns = [
        db.func.count(Task.id),
        *(_count_if(Task.status == status) for status in VALID_TASK_STATUSES),
        _count_if(task_service.overdue_filter(now)),
        _count_if(Task.priority <= HIGH_PRIORITY_THRESHOLD),
    ]
    row = db.session.execute(db.select(*columns).where(Task.user_id == user_id)).one()
    total, *status_counts, overdue, high_priority = row
    by_status = dict(zip(VALID_TASK_STATUSES, status_counts))
    return {
        'total_tasks': total,
        **by_status,
        'overdue': overdue,
        'high_priority': high_priority,
        'completion_rate': calculate_percentage(by_status[TASK_STATUS_DONE], total),
    }


def user_report(user_id):
    user = user_service.get_user(user_id)
    return {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
        },
        'statistics': _user_statistics(user_id, utcnow()),
    }
