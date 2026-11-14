# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Organizada em camadas MVC: `config/`, `models/`, `validators/`, `services/`, `controllers/`, `routes/` e `middlewares/`, montadas pela app factory `create_app()` em `app.py`.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: ajuste segredos, porta, CORS, senhas de seed
python seed.py
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`; debug só com `FLASK_DEBUG=1`). Também funciona com `flask --app app run`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**.

As senhas das contas de seed vêm das variáveis `SEED_ADMIN_PASSWORD`, `SEED_USER_PASSWORD` e `SEED_MANAGER_PASSWORD` (ver `.env.example`). Sem elas definidas, o seed gera uma senha aleatória por conta e a imprime uma única vez na saída.

## Autenticação

Duas credenciais, ambas verificadas em `middlewares/auth.py`:

**Token de usuário.** `POST /login` com e-mail e senha devolve `{"token": "<token assinado>"}`. O token é assinado com `SECRET_KEY` (HMAC via `itsdangerous`) e expira em `TOKEN_MAX_AGE` segundos (default 3600). Envie-o em `Authorization: Bearer <token>`.

**Token de administração.** Header `X-Admin-Token` com o valor de `ADMIN_TOKEN` (default de desenvolvimento: `dev-admin-token`).

Por rota:

| Rotas | Credencial exigida |
|---|---|
| `GET /`, `GET /health`, `GET /tasks`, `GET /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats`, `GET /categories` | nenhuma |
| `POST /users` (cadastro), `POST /login` | nenhuma — definir `role` diferente de `user` exige `X-Admin-Token` |
| `POST /tasks`, `PUT /tasks/<id>`, `POST /categories`, `PUT /categories/<id>`, `GET /users`, `GET /reports/summary` | `Authorization: Bearer <token>` ou `X-Admin-Token` |
| `GET /users/<id>`, `GET /users/<id>/tasks`, `PUT /users/<id>`, `GET /reports/user/<id>` | token do **próprio** usuário ou `X-Admin-Token` |
| `DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>`, alterar `role` em `PUT /users/<id>` | `X-Admin-Token` |

Sem credencial a resposta é `401 {"error": "Não autorizado"}`; com credencial de outro usuário, `403 {"error": "Acesso negado"}`.

Em `APP_ENV=production` o boot falha se `SECRET_KEY` ou `ADMIN_TOKEN` estiverem ausentes, mantiverem os defaults de desenvolvimento, ou se `FLASK_DEBUG` estiver ligado.
