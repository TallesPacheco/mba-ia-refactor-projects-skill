"""Script para popular o banco com dados iniciais (apenas desenvolvimento)."""
import logging
import os
import secrets
from datetime import timedelta

from app import app
from config.settings import Config
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import utcnow

logger = logging.getLogger(__name__)

# Fixtures de desenvolvimento: as senhas em texto vêm do ambiente (uma variável por conta,
# listadas em .env.example) e são gravadas com hash. Sem a variável definida, o seed gera uma
# senha aleatória e a imprime uma única vez — nunca há senha literal no código.
SEED_USERS = [
    {'name': 'João Silva', 'email': 'joao@email.com', 'password_env': 'SEED_ADMIN_PASSWORD', 'role': 'admin'},
    {'name': 'Maria Santos', 'email': 'maria@email.com', 'password_env': 'SEED_USER_PASSWORD', 'role': 'user'},
    {'name': 'Pedro Oliveira', 'email': 'pedro@email.com', 'password_env': 'SEED_MANAGER_PASSWORD', 'role': 'manager'},
]


def seed_password(env_var):
    value = os.environ.get(env_var)
    if value:
        return value
    if Config.APP_ENV == 'production':
        raise SystemExit(f'{env_var} é obrigatório em produção')
    value = secrets.token_urlsafe(12)
    print(f'[seed] {env_var} não definido; senha gerada para esta execução: {value}')
    return value

SEED_CATEGORIES = [
    {'name': 'Backend', 'description': 'Tarefas de backend', 'color': '#3498db'},
    {'name': 'Frontend', 'description': 'Tarefas de frontend', 'color': '#2ecc71'},
    {'name': 'DevOps', 'description': 'Tarefas de infraestrutura', 'color': '#e74c3c'},
    {'name': 'Bug', 'description': 'Correção de bugs', 'color': '#e67e22'},
]


def _seed_tasks(users, categories, now):
    joao, maria, pedro = users
    backend, frontend, devops, bug = categories
    return [
        {'title': 'Implementar autenticação JWT', 'description': 'Adicionar autenticação real com JWT', 'status': 'pending', 'priority': 1, 'user': joao, 'category': backend, 'due_date': now - timedelta(days=3)},
        {'title': 'Criar tela de login', 'description': 'Tela de login responsiva', 'status': 'in_progress', 'priority': 2, 'user': maria, 'category': frontend, 'due_date': now + timedelta(days=5)},
        {'title': 'Configurar CI/CD', 'description': 'Pipeline com GitHub Actions', 'status': 'done', 'priority': 2, 'user': pedro, 'category': devops, 'tags': 'devops,ci,github'},
        {'title': 'Corrigir bug no filtro de busca', 'description': 'Filtro não funciona com caracteres especiais', 'status': 'pending', 'priority': 1, 'user': joao, 'category': bug, 'due_date': now - timedelta(days=1)},
        {'title': 'Adicionar paginação na API', 'description': 'Endpoints retornam todos os registros', 'status': 'pending', 'priority': 3, 'user': joao, 'category': backend, 'due_date': now + timedelta(days=10)},
        {'title': 'Escrever testes unitários', 'description': 'Cobertura mínima de 80%', 'status': 'pending', 'priority': 2, 'user': maria, 'category': backend},
        {'title': 'Documentar API com Swagger', 'description': 'Gerar documentação automática', 'status': 'cancelled', 'priority': 4, 'user': pedro, 'category': backend},
        {'title': 'Refatorar models', 'description': 'Melhorar organização dos models', 'status': 'in_progress', 'priority': 3, 'user': maria, 'category': backend, 'tags': 'refactor,tech-debt'},
        {'title': 'Configurar monitoramento', 'description': 'Prometheus + Grafana', 'status': 'pending', 'priority': 4, 'user': pedro, 'category': devops, 'due_date': now + timedelta(days=20)},
        {'title': 'Melhorar validações de input', 'description': 'Usar marshmallow ou pydantic', 'status': 'pending', 'priority': 3, 'user': joao, 'category': backend, 'tags': 'improvement,validation'},
    ]


def seed_data():
    if Config.APP_ENV == 'production':
        raise SystemExit('seed.py é apenas para desenvolvimento (APP_ENV=production)')

    with app.app_context():
        try:
            # Limpeza + inserções numa única transação: em erro nada é aplicado.
            db.session.execute(db.delete(Task))
            db.session.execute(db.delete(User))
            db.session.execute(db.delete(Category))

            users = []
            for data in SEED_USERS:
                user = User(name=data['name'], email=data['email'], role=data['role'])
                user.set_password(seed_password(data['password_env']))
                users.append(user)
            categories = [Category(**data) for data in SEED_CATEGORIES]
            db.session.add_all(users + categories)
            db.session.flush()  # gera os IDs sem confirmar a transação

            now = utcnow()
            tasks = []
            for data in _seed_tasks(users, categories, now):
                tasks.append(Task(
                    title=data['title'],
                    description=data['description'],
                    status=data['status'],
                    priority=data['priority'],
                    user_id=data['user'].id,
                    category_id=data['category'].id,
                    due_date=data.get('due_date'),
                    tags=data.get('tags'),
                ))
            db.session.add_all(tasks)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('Seed falhou; nenhuma alteração foi aplicada')
            raise

        count = lambda model: db.session.scalar(db.select(db.func.count(model.id)))  # noqa: E731
        print("Seed concluído com sucesso!")
        print(f"  {count(User)} usuários")
        print(f"  {count(Category)} categorias")
        print(f"  {count(Task)} tasks")


if __name__ == '__main__':
    seed_data()
