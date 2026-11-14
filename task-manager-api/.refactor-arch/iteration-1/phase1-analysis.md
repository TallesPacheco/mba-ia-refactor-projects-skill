================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.14.3
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1 (SQLAlchemy 2.1.8 transitivo), flask-cors 4.0.0, marshmallow 3.20.1 (não usada), requests 2.31.0 (não usada), python-dotenv 1.0.0 (não usada)
Domain:        Task Manager API (tasks, users, categories, reports)
Architecture:  Camadas parciais — models/routes/services/utils existem, mas regra de negócio, ORM e serialização ficam nos handlers, services/ e utils/ quase não são usados, e não há config, app factory nem error handler
Source files:  15 files analyzed
DB tables:     users, categories, tasks (SQLite via Flask-SQLAlchemy, instance/tasks.db)
================================
Entry point: app.py (python seed.py && python app.py) — app.run(debug=True, host='0.0.0.0', port=5000) hardcoded
Rotas: 22 | Baseline: .refactor-arch/baseline.md (48 requisições)
