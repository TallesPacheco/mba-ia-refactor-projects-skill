from database import db
from models.constants import CLOSED_TASK_STATUSES, DEFAULT_PRIORITY, TASK_STATUS_PENDING
from utils.helpers import format_datetime, utcnow


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=TASK_STATUS_PENDING)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    # Deletar um usuário apaga as tasks dele; deletar uma categoria deixa category_id nulo.
    user = db.relationship('User', backref=db.backref('tasks', cascade='all, delete'))
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': format_datetime(self.due_date),
            'tags': self.tags.split(',') if self.tags else [],
        }

    def to_summary_dict(self):
        """Formato reduzido usado por GET /users/<id>/tasks."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': str(self.created_at),
            'due_date': format_datetime(self.due_date),
            'overdue': self.is_overdue(),
        }

    def is_overdue(self, now=None):
        if not self.due_date or self.status in CLOSED_TASK_STATUSES:
            return False
        return self.due_date < (now or utcnow())
