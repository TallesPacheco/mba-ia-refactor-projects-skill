================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py (composition root: create_app() + app = create_app())
├── config/
│   ├── __init__.py
│   └── settings.py
├── database.py (db, init_db com PRAGMA foreign_keys, commit transacional)
├── errors.py (exceções de domínio)
├── models/
│   ├── __init__.py
│   ├── constants.py
│   ├── category.py
│   ├── task.py
│   └── user.py
├── validators/
│   ├── __init__.py
│   ├── common.py
│   ├── category_validator.py
│   ├── task_validator.py
│   └── user_validator.py
├── services/
│   ├── __init__.py
│   ├── category_service.py
│   ├── report_service.py
│   ├── task_service.py
│   └── user_service.py
├── controllers/
│   ├── __init__.py
│   ├── category_controller.py
│   ├── report_controller.py
│   ├── task_controller.py
│   └── user_controller.py
├── routes/
│   ├── __init__.py
│   ├── category_routes.py
│   ├── report_routes.py
│   ├── system_routes.py
│   ├── task_routes.py
│   └── user_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── auth.py
│   └── error_handler.py
├── utils/
│   ├── __init__.py
│   └── helpers.py (utcnow, calculate_percentage, format_datetime)
├── seed.py
├── requirements.txt
├── README.md
└── .env.example

## Changes Applied
  [AP-01] SECRET_KEY, URI do banco, ADMIN_TOKEN, host/porta/debug e CORS lidos do ambiente (python-dotenv) com defaults só de dev; validação em APP_ENV=production; credenciais SMTP removidas junto com o NotificationService morto → config/settings.py, .env.example, app.py (parcial: senhas de fixture do seed continuam literais em seed.py, ver Remaining)
  [AP-04] User.to_dict() sem "password"; nenhuma resposta (GET/POST/PUT /users, POST /login) devolve o hash → models/user.py
  [AP-05] MD5 trocado por werkzeug generate_password_hash/check_password_hash (salt + comparação em tempo constante); seed grava hashes novos com as mesmas senhas → models/user.py, seed.py
  [AP-06] Header X-Admin-Token (ADMIN_TOKEN) exigido em DELETE /tasks, /users, /categories, em POST /users com role != user e em PUT /users com "role"; comparação hmac.compare_digest → middlewares/auth.py, routes/*.py, controllers/user_controller.py (parcial: token de login continua o formato de contrato "fake-jwt-token-<id>")
  [AP-07] app.run usa HOST (default 127.0.0.1), PORT (default 5000) e FLASK_DEBUG (default desligado) da config → app.py, config/settings.py
  [AP-08] Handlers reduzidos a parse → controller → jsonify; regra de negócio em services/, validação em validators/; Task.is_overdue() virou a fonte única da regra de atraso → routes/, controllers/, services/, validators/, models/task.py
  [AP-10] Seed numa única transação (deletes + inserts com flush() e um commit, rollback em erro); escritas das rotas via database.commit() com rollback → seed.py, database.py
  [AP-11] App factory create_app(config) registra CORS, banco, error handler e blueprints; create_all saiu do nível de módulo para init_db() chamado pela factory → app.py, database.py
  [AP-12] Error handler central (AppError/HTTPException/Exception → {"error": ...}, mesma chave original) com log do stack trace; todos os except nus removidos → middlewares/error_handler.py, errors.py
  [AP-13] GET /tasks com selectinload(user, category); contagens com GROUP BY/outer join em /users, /categories, /tasks/stats e /reports/summary; filtro de atraso no SQL → services/*.py
  [AP-14] Validadores por recurso: tipos de title/priority/tags/active/email/password/color, query params int, corpo null → 400 em vez de 500 → validators/*.py
  [AP-15] Listas de status/roles, regex de e-mail, regra de atraso e serialização de task centralizadas (constants, validators, Task.to_dict/to_summary_dict/is_overdue); cópias e helpers não usados apagados → models/, validators/, utils/helpers.py
  [AP-17] datetime.utcnow → utils.helpers.utcnow() (UTC naive, mesmo formato serializado); Model.query.* → db.session.get / db.select; type(x)==list → isinstance → todos os arquivos
  [AP-18] CORS restrito a CORS_ORIGINS (default http://localhost:3000); auth e error handler como middlewares registrados na factory → app.py, middlewares/
  [AP-19] PRAGMA foreign_keys=ON em cada conexão SQLite; cascata de tasks declarada no model (backref cascade='all, delete') e ondelete CASCADE/SET NULL nas FKs; loop manual de deleção removido → database.py, models/task.py, services/user_service.py
  [AP-20] Literais de domínio (limites de título, prioridade 1–5, senha mínima, janela de 7 dias, labels de prioridade, cor default, nome/versão da API) em models/constants.py
  [AP-21] CRUD de /categories movido para routes/category_routes.py (mesmos paths); p1..p5/u1..c4/t/d substituídos por nomes descritivos → routes/category_routes.py, services/report_service.py, seed.py
  [AP-22] print substituído por logging (logging.basicConfig na factory, logger.info/exception sem PII); print mantido só na saída do script de seed → services/*.py, database.py, app.py
  [AP-23] Imports mortos removidos; services/notification_service.py (nunca importado) apagado; utils/helpers.py reduzido às funções usadas; marshmallow e requests retirados do requirements.txt (python-dotenv passou a ser usado) → todos os arquivos, requirements.txt

## Validation
  ✓ Application boots without errors (PORT=5302 .venv/bin/python -W default app.py, porta 5302; log sem traceback nem DeprecationWarning/LegacyAPIWarning)
  ✓ All baseline endpoints respond (45/48 com mesmo status e shape; os 3 restantes são 500 → 400 intencionais: #8, #24, #40)
  ✓ Original start command still works (python app.py via PORT=5302; também .venv/bin/flask --app app run --port 5303 → GET /health 200; 22 rotas registradas)
  ✓ Seed / initial data loads (.venv/bin/python seed.py → 3 usuários, 4 categorias, 10 tasks; IDs 1..10; POST /login joao@email.com/1234 → 200)
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep: sem SECRET_KEY/senha SMTP literal, sem "password" em resposta, sem hashlib.md5, 3/3 DELETE com require_admin, sem debug=True/0.0.0.0, sem db.session/query em routes/controllers, 1 commit no seed, create_all só dentro de init_db; restam como hits só as fixtures de senha do seed, ver Remaining)
  ✓ Old monolith/duplicate files removed (services/notification_service.py apagado; CRUD de categorias fora de report_routes.py; grep por notification_service/process_task_data sem resultados)
  ✓ .env.example created
  ✓ Auth validada: DELETE /tasks/1, /users/1, /categories/1 sem token → 401; token errado → 401; com X-Admin-Token: dev-admin-token → 200/404 conforme baseline; PUT /users/2 {"role":"admin"} sem token → 401; POST /users role admin sem token → 401, com token → 201
  ✓ Servidores parados (lsof em 5302 e 5303 vazio)

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | / | 200 | 200 | = | |
| GET | /health | 200 | 200 | = | timestamp continua em hora local |
| GET | /tasks | 200 | 200 | = | 10 itens, mesmas chaves; sem N+1 |
| GET | /tasks/1 | 200 | 200 | = | |
| GET | /tasks/999 | 404 | 404 | = | |
| GET | /tasks/search?q=API | 200 | 200 | = | ids [5, 7] |
| GET | /tasks/search?status=pending&priority=1 | 200 | 200 | = | ids [1, 4] |
| GET | /tasks/search?priority=abc | 500 (HTML) | 400 | ≈ | {"error":"Prioridade inválida"} (fix AP-14) |
| GET | /tasks/stats | 200 | 200 | = | mesmos valores (total 10, overdue 2, completion_rate 10.0) |
| GET | /users | 200 | 200 | = | task_count via GROUP BY |
| GET | /users/1 | 200 | 200 | ≈ | campo "password" removido (fix AP-04) |
| GET | /users/999 | 404 | 404 | = | |
| GET | /users/1/tasks | 200 | 200 | = | |
| GET | /users/999/tasks | 404 | 404 | = | |
| GET | /reports/summary | 200 | 200 | = | mesmos valores em todas as seções |
| GET | /reports/user/1 | 200 | 200 | = | |
| GET | /reports/user/999 | 404 | 404 | = | |
| GET | /categories | 200 | 200 | = | task_count [6,1,2,1] |
| POST | /login (válido) | 200 | 200 | ≈ | "password" removido de "user" (fix AP-04); token mantém o formato |
| POST | /login (senha errada) | 401 | 401 | = | |
| POST | /login {} | 400 | 400 | = | |
| POST | /tasks (válido) | 201 | 201 | = | |
| POST | /tasks {"title":"ab"} | 400 | 400 | = | |
| POST | /tasks priority "2" | 500 (HTML) | 400 | ≈ | {"error":"Prioridade inválida"} (fix AP-14) |
| POST | /tasks user_id 999 | 404 | 404 | = | |
| POST | /users (válido) | 201 | 201 | ≈ | "password" removido (fix AP-04) |
| POST | /users (e-mail repetido) | 409 | 409 | = | |
| POST | /users (e-mail inválido) | 400 | 400 | = | |
| POST | /categories (válido) | 201 | 201 | = | |
| POST | /categories {} | 400 | 400 | = | |
| PUT | /tasks/11 (válido) | 200 | 200 | = | |
| PUT | /tasks/11 status inválido | 400 | 400 | = | |
| PUT | /tasks/999 | 404 | 404 | = | |
| PUT | /users/4 {"name","role"} | 200 | 401 sem token / 200 com `X-Admin-Token` | ≈ | alterar role exige admin (fix AP-06); "password" removido (fix AP-04) |
| PUT | /users/4 role inválido | 400 | 400 | = | |
| PUT | /users/999 | 404 | 404 | = | |
| PUT | /categories/5 (válido) | 200 | 200 | = | |
| PUT | /categories/999 | 404 | 404 | = | |
| PUT | /categories/5 sem Content-Type | 415 (HTML) | 415 | ≈ | erro agora em JSON {"error": ...} (fix AP-12) |
| PUT | /categories/5 body null | 500 (HTML) | 400 | ≈ | {"error":"Dados inválidos"} (fix AP-14) |
| POST | /tasks (task da Ana) | 201 | 201 | = | |
| DELETE | /tasks/11 | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| DELETE | /tasks/999 | 404 | 404 (com token) | = | |
| DELETE | /users/4 | 200 | 401 sem token / 200 com `X-Admin-Token` | = | task 12 apagada em cascata (GET /tasks/12 → 404, igual ao baseline) |
| DELETE | /users/999 | 404 | 404 (com token) | = | |
| DELETE | /categories/5 | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| DELETE | /categories/999 | 404 | 404 (com token) | = | |
| DELETE | /categories/4 | 200 | 401 sem token / 200 com `X-Admin-Token` | = | task 4 fica com category_id null (igual ao baseline) |

## Remaining Known Issues
  - Token de admin: header `X-Admin-Token`, valor de `ADMIN_TOKEN` (default de dev `dev-admin-token`, documentado em .env.example e README). Em APP_ENV=production o boot falha se SECRET_KEY/ADMIN_TOKEN não estiverem no ambiente.
  - POST /login continua devolvendo `"token": "fake-jwt-token-<id>"`: é contrato da API, previsível e não validado por nenhuma rota. Recomenda-se substituir por JWT/sessão assinada com SECRET_KEY numa mudança de contrato acordada.
  - AP-01 (parcial): as senhas de fixture do seed ('1234', 'abcd', 'pass') continuam literais em seed.py para manter os logins de dev do baseline. O seed agora recusa rodar com APP_ENV=production.
  - Bancos com hashes MD5 antigos não fazem mais login (check_password devolve False). O banco de dev é gitignored e regenerado por `python seed.py`; um banco persistente exigiria migração ou reset de senha.
  - As cláusulas `ondelete` novas só entram no schema de um banco criado do zero (create_all não altera tabela existente). Em `instance/tasks.db` já existente, a integridade vem do PRAGMA foreign_keys=ON + cascata do ORM (comportamento validado). Para aplicar o DDL: apagar instance/tasks.db e rodar seed.py.
  - Validação manual em validators/ no lugar de marshmallow, para preservar mensagens e ordem exatas dos erros do contrato; marshmallow foi retirado do requirements.txt.
  - Novas regras de validação (active booleano, tags lista/string, cor "#xxxxxx", nome não vazio no PUT /users) só rejeitam entradas que antes davam 500 ou gravavam dado absurdo; não estavam no baseline.
  - Erro 500 inesperado passa a responder {"error": "Erro interno do servidor"}; falhas de commit mantêm as mensagens originais ("Erro ao criar task", "Erro ao atualizar"...).
  - Busca LIKE não escapa os curingas % e _ do termo (não é injeção; comportamento original mantido).
  - pyflakes foi instalado só no .venv para checagem de imports; não entrou no requirements.txt.
================================
