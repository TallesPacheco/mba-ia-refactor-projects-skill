================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.14.3
Framework:     Flask 3.1.1 (Werkzeug 3.1.9)
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib, driver cru)
Domain:        E-commerce API (produtos, usuarios, pedidos, itens_pedido)
Architecture:  Monolítica — 4 arquivos planos sem pacotes; app.py mistura config + rotas + SQL inline, models.py (314 linhas) concentra SQL dos 3 domínios + regras de negócio, sem services/config/error handler
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido (SQLite via sqlite3, arquivo loja.db no CWD)
================================
Entry point: app.py (python app.py) — host 0.0.0.0, porta 5000 e debug=True hardcoded em app.py:88
Rotas: 19 | Baseline: .refactor-arch/baseline.md (54 requisições)
