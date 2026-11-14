================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py (composition root: create_app() + app = create_app())
├── config/
│   ├── __init__.py
│   └── settings.py (env + TOKEN_MAX_AGE; recusa defaults de dev em produção)
├── database.py (db, init_db com PRAGMA foreign_keys, commit transacional)
├── errors.py (exceções de domínio)
├── models/
│   ├── __init__.py (__all__ com os 3 models)
│   ├── constants.py
│   ├── category.py
│   ├── task.py
│   └── user.py
├── validators/
│   ├── __init__.py
│   ├── common.py (require_payload, parse_int_param, validate_optional_id/_text)
│   ├── category_validator.py
│   ├── task_validator.py
│   └── user_validator.py
├── services/
│   ├── __init__.py
│   ├── category_service.py
│   ├── report_service.py (agregações 100% no banco)
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
│   ├── auth.py (issue_token, verify_token, require_auth, ensure_owner_or_admin, require_admin)
│   └── error_handler.py
├── utils/
│   ├── __init__.py
│   └── helpers.py (utcnow, localnow, calculate_percentage, format_datetime)
├── seed.py (senhas das fixtures vindas do ambiente)
├── requirements.txt
├── README.md
└── .env.example

Estrutura de pastas inalterada (o projeto já estava em camadas MVC): 37 arquivos Python, ~1556 linhas. Nenhum arquivo criado ou removido; as correções foram pontuais nos arquivos dos 8 findings.

## Changes Applied
  [AP-01] Senhas das contas de seed vindas de `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD`/`SEED_MANAGER_PASSWORD`, **sem fallback literal**; sem a variável, `seed_password()` gera `secrets.token_urlsafe(12)` e imprime uma única vez; em `APP_ENV=production` o seed exige as variáveis → seed.py, .env.example, README.md
  [AP-06] `@require_auth` em POST/PUT de `/tasks` e `/categories`; `PUT /users/<id>` exige `@require_auth` + `ensure_owner_or_admin` (fim do takeover anônimo de senha/e-mail/active); `DELETE` continua só com `X-Admin-Token`; `POST /users` e `POST /login` seguem públicos → routes/task_routes.py, routes/category_routes.py, routes/user_routes.py, middlewares/auth.py
  [AP-24] `POST /login` devolve token assinado com `SECRET_KEY` via `itsdangerous.URLSafeTimedSerializer` e expiração `TOKEN_MAX_AGE` (default 3600 s); `verify_token`/`require_auth` validam `Authorization: Bearer <token>`; `LOGIN_TOKEN_PREFIX = 'fake-jwt-token-'` removido; produção recusa `SECRET_KEY`/`ADMIN_TOKEN` com os defaults de dev → middlewares/auth.py, controllers/user_controller.py, config/settings.py
  [AP-25] `GET /users` e `GET /reports/summary` exigem credencial; `GET /users/<id>`, `GET /users/<id>/tasks` e `GET /reports/user/<id>` exigem o token do próprio usuário ou `X-Admin-Token` (403 para terceiros) → routes/user_routes.py, routes/report_routes.py
  [AP-13] `user_report` passou de "carregar todas as tasks e contar em Python" para **uma** consulta agregada (`COUNT` + `SUM(CASE ...)` por status, atraso e prioridade alta), reaproveitando `task_service.overdue_filter`; `_count_if` virou o helper único também usado por `_user_productivity` → services/report_service.py
  [AP-14] `user_id`/`category_id` validados como inteiro ou nulo e `description` como texto ou nulo, em criação e atualização: os três 500 de bind do SQLite viraram 400 → validators/common.py, validators/task_validator.py
  [AP-15] (parcial) `/health` passou a usar `utils.helpers.localnow()` em vez de `datetime.datetime.now()` inline: a divergência de fuso ficou num único ponto nomeado e documentado. O **valor** da resposta não mudou (segue hora local) porque isso é contrato da API — ver Remaining Known Issues
  [AP-23] `TestConfig` e `get_config()` (inalcançáveis) apagados junto com o re-export em `config/__init__.py`; `__all__` em `models/__init__.py`; `marshmallow` e `requests` desinstalados do `.venv` para igualá-lo ao `requirements.txt` → config/settings.py, config/__init__.py, models/__init__.py

## Validation
  ✓ Application boots without errors (`PORT=5403 .venv/bin/python -W default app.py`; log sem traceback, sem DeprecationWarning/LegacyAPIWarning)
  ✓ All baseline endpoints respond (80 requisições: as 63 do baseline com credencial + 17 checagens novas de 401/403 e de tipo; nenhum 500 no log)
  ✓ Original start command still works (`python app.py` via `PORT=5403`; também `.venv/bin/flask --app app run --port 5404` → `GET /health` 200, 23 rotas registradas)
  ✓ Seed / initial data loads (`SEED_*_PASSWORD` exportadas → 3 usuários, 4 categorias, 10 tasks, IDs 1..10; sem as variáveis, gera e imprime senhas aleatórias e também conclui)
  ✓ Takeover anônimo fechado (`PUT /users/1 {"password":"invadido123"}` → 401; `POST /login` com essa senha → 401, contra 200/200 antes da correção)
  ✓ Auth validada em todas as rotas protegidas (401 sem credencial, 200/201 com `Authorization: Bearer`, 403 com token de outro usuário, `X-Admin-Token` nos DELETE e nas mudanças de `role`)
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep: sem senha literal no seed, sem `fake-jwt`, sem `environ.get(..., "<literal>")`, consumidor de `Authorization` presente em `middlewares/auth.py:54`, 11 guards registrados em `routes/`, sem `debug=True`/`0.0.0.0`, sem `password` em serializer)
  ✓ AP-13 verificado no ramo de divisão não-zero (`GET /reports/user/3` → `total_tasks 3, done 1, cancelled 1, pending 1, completion_rate 33.33`; `GET /reports/user/2` → `3 tasks, 0 done, 0.0`), ambos conferindo com `user_productivity` do baseline #15, que vem de um caminho de código não alterado
  ✓ AP-26 re-checado **depois** das correções (grep do catálogo sobre `*.py` sem resultados; revisão das strings atuais: `'Não autorizado'` e `'Acesso negado'` descrevem exatamente o que os guards fazem, e nenhuma mensagem antiga ficou falsa)
  ✓ Deprecated APIs / lint (pyflakes acusa apenas `database.py:27 'models' imported but unused`, que é o registro intencional dos models com `# noqa: F401`)
  ✓ .env.example atualizado (TOKEN_MAX_AGE + as três variáveis de senha de seed)
  ✓ DDL de integridade aplicado (`instance/tasks.db` recriado: `FOREIGN KEY(user_id) ... ON DELETE CASCADE` e `FOREIGN KEY(category_id) ... ON DELETE SET NULL` presentes no schema, não só no ORM)
  ✓ Servidores parados (`lsof` vazio em 5401, 5402, 5403 e 5404)

## Como o validador obtém as credenciais
- **Token de usuário:** `POST /login` com `{"email":"joao@email.com","password":"1234"}` (ou `maria@email.com`/`abcd`, `pedro@email.com`/`pass`) e envie `Authorization: Bearer <token>`. O valor vem de `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD`/`SEED_MANAGER_PASSWORD`, que **precisam ser exportadas antes do seed e do boot** com os valores de dev do baseline:
  `export SEED_ADMIN_PASSWORD=1234 SEED_USER_PASSWORD=abcd SEED_MANAGER_PASSWORD=pass`
- **Token de admin:** header `X-Admin-Token: dev-admin-token` (valor de `ADMIN_TOKEN`).
- Script pronto: `PORT=<porta> bash .refactor-arch/replay.sh` (faz login, monta os headers e repete as 80 requisições).

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | / | 200 | 200 | = | |
| GET | /health | 200 | 200 | = | timestamp segue em hora local (via `localnow()`) |
| GET | /tasks | 200 | 200 | = | pública; 10 itens, mesmas chaves |
| GET | /tasks/1 | 200 | 200 | = | |
| GET | /tasks/999 | 404 | 404 | = | |
| GET | /tasks/search?q=API | 200 | 200 | = | ids [5, 7] |
| GET | /tasks/search?status=pending&priority=1 | 200 | 200 | = | ids [1, 4] |
| GET | /tasks/search?priority=abc | 400 | 400 | = | |
| GET | /tasks/stats | 200 | 200 | = | total 10, overdue 2, completion_rate 10.0 |
| GET | /users | 200 | 401 sem credencial / 200 com `Bearer` ou `X-Admin-Token` | = | auth adicionada (fix AP-25) |
| GET | /users/1 | 200 | 401 sem credencial / 403 com token de outro / 200 com o próprio ou admin | = | dono-ou-admin (fix AP-25) |
| GET | /users/999 | 404 | 404 (com admin) | = | |
| GET | /users/1/tasks | 200 | 401 / 403 / 200 (dono ou admin) | = | auth adicionada (fix AP-25) |
| GET | /users/999/tasks | 404 | 404 (com admin) | = | |
| GET | /reports/summary | 200 | 401 sem credencial / 200 com | = | expõe `user_name`; auth adicionada (fix AP-25) |
| GET | /reports/user/1 | 200 | 401 / 403 / 200 (dono ou admin) | = | mesmos valores: total 4, pending 4, overdue 2, high_priority 2, completion_rate 0.0 — agora por consulta agregada (fix AP-13) |
| GET | /reports/user/999 | 404 | 404 (com admin) | = | |
| GET | /categories | 200 | 200 | = | task_count [6,1,2,1] |
| GET | /__rota-inexistente__ | 404 JSON | 404 JSON | = | |
| POST | /__rota-inexistente__ | 404 JSON | 404 JSON | = | |
| DELETE | /tasks | 405 JSON | 405 JSON | = | |
| POST | /login (válido) | 200 | 200 | ≈ | `token` continua string; valor passa a ser assinado e expira (fix AP-24) |
| POST | /login (2ª chamada) | token idêntico | token com assinatura e timestamp próprios | ≈ | não é mais derivado do id (fix AP-24) |
| POST | /login (senha errada) | 401 | 401 | = | |
| POST | /login {} | 400 | 400 | = | |
| POST | /tasks (válido) | 201 | 401 sem credencial / 201 com | = | auth adicionada (fix AP-06) |
| POST | /tasks {"title":"ab"} | 400 | 400 (com credencial) | = | |
| POST | /tasks priority "2" | 400 | 400 | = | |
| POST | /tasks user_id 999 | 404 | 404 | = | id inteiro inexistente segue 404 |
| POST | /tasks user_id {"a":1} | 500 | 400 | ≈ | {"error":"Usuário inválido"} (fix AP-14) |
| POST | /tasks user_id [1] | 500 | 400 | ≈ | {"error":"Usuário inválido"} (fix AP-14) |
| PUT | /tasks/1 description {"x":1} | 500 | 400 | ≈ | {"error":"Descrição inválida"} (fix AP-14) |
| POST | /users (válido) | 201 | 201 | = | cadastro segue público |
| POST | /users (e-mail repetido) | 409 | 409 | = | |
| POST | /users (e-mail inválido) | 400 | 400 | = | |
| POST | /users role admin sem header | 401 | 401 | = | |
| POST | /users role admin + `X-Admin-Token` | 201 | 201 | = | |
| POST | /categories (válido) | 201 | 401 sem credencial / 201 com | = | auth adicionada (fix AP-06) |
| POST | /categories {} | 400 | 400 (com credencial) | = | |
| PUT | /tasks/11 (válido) | 200 | 401 sem credencial / 200 com | = | auth adicionada (fix AP-06) |
| PUT | /tasks/11 status inválido | 400 | 400 | = | |
| PUT | /tasks/999 | 404 | 404 | = | |
| PUT | /users/4 {"name","role"} | 401 sem token / 200 com `X-Admin-Token` | 401 sem credencial / 401 com token do próprio (role exige admin) / 200 com `X-Admin-Token` | = | inalterado para admin |
| PUT | /users/4 role inválido | 400 | 400 (com admin) | = | |
| PUT | /users/4 {"name":"Ana Only"} | **200 anônimo** | 401 sem credencial / 403 de outro / 200 do próprio ou admin | = | **takeover fechado** (fix AP-06) |
| PUT | /users/1 {"password":...} anônimo | **200 + login com a senha nova** | 401 sem credencial / 200 do próprio ou admin | = | takeover de conta admin eliminado (fix AP-06) |
| GET | /reports/user/3 | 200 | 200 | = | `completion_rate` 33.33 e `done` 1 conferem com `user_productivity` do baseline #15 (ramo de divisão não-zero do fix AP-13) |
| GET | /reports/user/2 | 200 | 200 | = | 3 tasks, 0 done, `completion_rate` 0.0 — confere com baseline #15 |
| PUT | /users/999 | 404 | 404 (com admin) | = | |
| PUT | /categories/5 (válido) | 200 | 401 sem credencial / 200 com | = | auth adicionada (fix AP-06) |
| PUT | /categories/999 | 404 | 404 | = | |
| PUT | /categories/5 sem Content-Type | 415 JSON | 415 JSON | = | |
| PUT | /categories/5 body null | 400 | 400 | = | |
| POST | /tasks (task da Ana) | 201 | 201 (com credencial) | = | |
| DELETE | /tasks/11 | 401 sem token / 200 com `X-Admin-Token` | 401 sem token / 401 com token de usuário / 200 com `X-Admin-Token` | = | inalterado |
| DELETE | /tasks/999 | 404 | 404 (com admin) | = | |
| DELETE | /users/4 | 401 / 200 com admin | 401 / 200 com admin | = | task 12 apagada em cascata (GET /tasks/12 → 404) |
| DELETE | /users/999 | 404 | 404 (com admin) | = | |
| DELETE | /categories/5 | 401 / 200 com admin | 401 / 200 com admin | = | |
| DELETE | /categories/999 | 404 | 404 (com admin) | = | |
| DELETE | /categories/4 | 401 / 200 com admin | 401 / 200 com admin | = | task 4 fica com category_id null |

## Remaining Known Issues
  - **Credenciais para validar:** exporte `SEED_ADMIN_PASSWORD=1234 SEED_USER_PASSWORD=abcd SEED_MANAGER_PASSWORD=pass` antes de `python seed.py` e do boot; obtenha o token de usuário em `POST /login` (`Authorization: Bearer <token>`) e use `X-Admin-Token: dev-admin-token` nas rotas admin. Sem as variáveis, o seed gera senhas aleatórias e as imprime — os logins do baseline deixam de valer.
  - **AP-15 (parcial, exige decisão de contrato):** `GET /health` continua devolvendo `timestamp` em hora local (`utils.helpers.localnow()`), 3 h defasado dos `created_at`/`generated_at` em UTC. Trocar para `utcnow()` muda um valor observável da resposta e não foi aplicado sem aprovação explícita. Nenhum campo declara fuso.
  - **Troca de senha sem senha atual:** `PUT /users/<id>` com `{"password": ...}` agora exige o token do próprio usuário (ou admin), mas não pede a senha atual. Exigi-la acrescentaria um campo obrigatório ao contrato de entrada; recomendado numa mudança acordada.
  - **Token sem revogação:** o token assinado expira em `TOKEN_MAX_AGE` (3600 s) mas não há lista de revogação nem refresh; trocar `SECRET_KEY` invalida todos de uma vez.
  - **403 em vez de 404 para id inexistente:** `ensure_owner_or_admin` roda antes de `get_user`, então um usuário autenticado **não-admin** que chama `GET /users/999`, `GET /users/999/tasks`, `PUT /users/999` ou `GET /reports/user/999` recebe 403 `{"error":"Acesso negado"}`, não o 404 do baseline (verificado em runtime com o token de `maria@email.com`). Escolha deliberada: evita enumeração de ids. Com `X-Admin-Token` o 404 original é preservado.
  - **`X-Admin-Token` não identifica usuário:** é um segredo compartilhado. Com ele, `ensure_owner_or_admin` libera qualquer id e `g.user_id` fica `None`. Um papel de admin por usuário (via `User.is_admin()`, já existente e ainda sem uso em rota) seria o passo seguinte.
  - **Leituras públicas que expõem nome:** `GET /tasks` e `GET /tasks/<id>` continuam públicas e devolvem `user_name`/`category_name`. Não estavam no finding AP-25 (que tratava de e-mail) e foram preservadas; proteger também essas rotas é mudança de contrato a decidir.
  - **Bancos antigos:** hashes MD5 anteriores à iteração 1 não logam (`check_password` devolve `False`), e um `instance/tasks.db` criado antes desta iteração não tem as cláusulas `ondelete` no DDL — `create_all()` não altera tabela existente. O banco desta sessão foi recriado (`rm instance/tasks.db && python seed.py`) e já tem o DDL completo.
  - **`category_id`/`user_id` como string:** passou de 404 ("Categoria não encontrada") para 400 ("Categoria inválida"). Mudança na direção segura, mas é alteração de status para entrada inválida.
  - **Busca `LIKE` não escapa `%` e `_`** (`services/task_service.py:76-77`): comportamento original preservado; não é injeção.
  - **Validação manual em `validators/`** no lugar de marshmallow (removido do `.venv` nesta iteração), para preservar mensagens e ordem exatas dos erros do contrato.
  - **`pyflakes` só no `.venv`,** fora do `requirements.txt`: ferramenta de checagem, não dependência da aplicação. Ele acusa `database.py:27` porque não honra `# noqa` (isso é do flake8); o import é o registro intencional dos models antes do `create_all()`.
  - **`app = create_app()` em nível de módulo** (`app.py:39`) mantém `python app.py`, `flask --app app run` e `from app import app` (seed) funcionando, ao custo de `init_db()` rodar em qualquer import. Requisito de compatibilidade do start original; não é finding.
================================
