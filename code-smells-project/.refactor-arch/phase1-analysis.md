================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.14.3
Framework:     Flask 3.1.1 (Werkzeug 3.1.9)
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib), werkzeug.security (hash de senha) — nenhuma dependência declarada e não importada
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido)
Architecture:  MVC em camadas — views/ (blueprints finos) → controllers/ → services/ → models/ (SQL), com config/, db/, validators/, middlewares/ e app factory em app.py
Source files:  40 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido (SQLite via sqlite3 da stdlib, arquivo `loja.db` no CWD)
================================

Entry point: `app.py` — `create_app()` (factory) + `app = create_app()` em nível de módulo; `python app.py` lê HOST/PORT/FLASK_DEBUG da config (`config/settings.py:12-14`), defaults 127.0.0.1:5000 com debug desligado. `flask --app app run` também funciona.
Rotas: 19 rotas da aplicação (+ `static`), confirmadas com `.venv/bin/flask --app app routes`; 9 delas exigem o header `X-Admin-Token`.
Baseline: `.refactor-arch/baseline.md` — 66 requisições (`PORT=5201 .venv/bin/python app.py`), incluindo chamadas com e sem token nas rotas protegidas, rota inexistente e método não permitido. Log em `.refactor-arch/baseline-server.log`; servidores encerrados.
Modo re-execução: artefatos da execução anterior já estavam arquivados em `.refactor-arch/iteration-1/`; nada de topo a mover.
~1120 linhas de código Python.
