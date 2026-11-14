# Baseline — task-manager-api (iteração 2, projeto já refatorado na iteração 1)
Boot: `PORT=5401 .venv/bin/python -W default app.py` (comando de start original; `HOST`/`PORT`/`FLASK_DEBUG` vêm da config) | Seed: `.venv/bin/python seed.py` (apaga e recria users/categories/tasks em `instance/tasks.db`, gitignored; rodado antes do boot)
Versões: Python 3.14.3 / Flask 3.0.0 / Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.1.8 transitivo) / Werkzeug 3.1.9 / Flask-Cors 4.0.0 / python-dotenv 1.0.0
Banco: `sqlite:///tasks.db` → `instance/tasks.db` (Flask-SQLAlchemy 3). Recriar: `.venv/bin/python seed.py` (IDs voltam a começar em 1).
Credenciais de dev: `joao@email.com` / `1234` (admin), `maria@email.com` / `abcd`, `pedro@email.com` / `pass`. Header de admin: `X-Admin-Token: dev-admin-token` (default de `ADMIN_TOKEN`; sem `.env` presente).

| # | Método | Path | Payload | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | / | - | 200 | {message:"Task Manager API", version:"1.0"} |
| 2 | GET | /health | - | 200 | {status:"ok", timestamp} — timestamp em **hora local** (11:56) contra UTC (14:56) dos demais campos |
| 3 | GET | /tasks | - | 200 | lista (10) de {id,title,description,status,priority,user_id,category_id,created_at,updated_at,due_date,tags[],overdue,user_name,category_name} |
| 4 | GET | /tasks/1 | - | 200 | {id,…,tags[],overdue} (sem user_name/category_name) |
| 5 | GET | /tasks/999 | - | 404 | {error:"Task não encontrada"} |
| 6 | GET | /tasks/search?q=API | - | 200 | lista de task.to_dict() (sem overdue) — ids 5, 7 |
| 7 | GET | /tasks/search?status=pending&priority=1 | - | 200 | lista — ids 1, 4 |
| 8 | GET | /tasks/search?priority=abc | - | 400 | {error:"Prioridade inválida"} |
| 9 | GET | /tasks/stats | - | 200 | {total:10,pending:6,in_progress:2,done:1,cancelled:1,overdue:2,completion_rate:10.0} |
| 10 | GET | /users | - | 200 | lista (3) de {id,name,**email**,role,active,created_at,task_count} — sem auth |
| 11 | GET | /users/1 | - | 200 | {id,name,**email**,role,active,created_at,tasks[4]} — sem `password`, sem auth |
| 12 | GET | /users/999 | - | 404 | {error:"Usuário não encontrado"} |
| 13 | GET | /users/1/tasks | - | 200 | lista de {id,title,description,status,priority,created_at,due_date,overdue} |
| 14 | GET | /users/999/tasks | - | 404 | {error} |
| 15 | GET | /reports/summary | - | 200 | {generated_at,overview{3},tasks_by_status{4},tasks_by_priority{critical,high,medium,low,minimal},overdue{count:2,tasks[{id,title,due_date,days_overdue}]},recent_activity{2},user_productivity[3]} |
| 16 | GET | /reports/user/1 | - | 200 | {user{id,name,**email**},statistics{total_tasks,pending,in_progress,done,cancelled,overdue,high_priority,completion_rate}} — sem auth |
| 17 | GET | /reports/user/999 | - | 404 | {error} |
| 18 | GET | /categories | - | 200 | lista (4) de {id,name,description,color,created_at,task_count} — task_count [6,1,2,1] |
| 19 | GET | /__rota-inexistente__ | - | 404 | **application/json** {error:"The requested URL was not found on the server. …"} (mensagem padrão do Werkzeug, em inglês) |
| 20 | POST | /__rota-inexistente__ | {} | 404 | application/json, mesma mensagem |
| 21 | DELETE | /tasks | {} | 405 | application/json {error:"The method is not allowed for the requested URL."} |
| 22 | POST | /login | {"email":"joao@email.com","password":"1234"} | 200 | {message,token:"fake-jwt-token-1",user{…}} — **sem** `password` |
| 23 | POST | /login | (repetido, 2ª vez) | 200 | token **idêntico** `fake-jwt-token-1` (derivado do id, não rotativo) |
| 24 | POST | /login | {"email":"joao@email.com","password":"x"} | 401 | {error:"Credenciais inválidas"} |
| 25 | POST | /login | {} | 400 | {error:"Dados inválidos"} |
| 26 | POST | /tasks | {"title":"Nova task baseline","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2026-12-01","tags":["a","b"]} | 201 | task.to_dict() (id 11, tags ["a","b"], due_date "2026-12-01 00:00:00") — **sem auth** |
| 27 | POST | /tasks | {"title":"ab"} | 400 | {error:"Título muito curto"} |
| 28 | POST | /tasks | {"title":"Prioridade str","priority":"2"} | 400 | {error:"Prioridade inválida"} |
| 29 | POST | /tasks | {"title":"user ruim","user_id":999} | 404 | {error:"Usuário não encontrado"} |
| 30 | POST | /users | {"name":"Ana","email":"ana@email.com","password":"segredo"} | 201 | {id:4,name,email,role:"user",active,created_at} — sem `password`, **sem auth** |
| 31 | POST | /users | (mesmo payload) | 409 | {error:"Email já cadastrado"} |
| 32 | POST | /users | {"name":"X","email":"bad","password":"segredo"} | 400 | {error:"Email inválido"} |
| 33 | POST | /users | {…,"role":"admin"} sem header | 401 | {error:"Não autorizado"} |
| 34 | POST | /users | {…,"role":"admin"} + `X-Admin-Token` | 201 | {id:5,…,role:"admin"} |
| 35 | POST | /categories | {"name":"QA","color":"#ffffff"} | 201 | {id:5,name,description:"",color,created_at} — **sem auth** |
| 36 | POST | /categories | {} | 400 | {error:"Dados inválidos"} |
| 37 | PUT | /tasks/11 | {"status":"done","title":"Nova task atualizada"} | 200 | task.to_dict() — **sem auth** |
| 38 | PUT | /tasks/11 | {"status":"xx"} | 400 | {error:"Status inválido"} |
| 39 | PUT | /tasks/999 | {"status":"done"} | 404 | {error} |
| 40 | PUT | /users/4 | {"name":"Ana Maria","role":"manager"} sem header | 401 | {error:"Não autorizado"} |
| 41 | PUT | /users/4 | mesmo payload + `X-Admin-Token` | 200 | user.to_dict() (role manager) |
| 42 | PUT | /users/4 | {"role":"root"} + header | 400 | {error:"Role inválido"} |
| 43 | PUT | /users/4 | {"name":"Ana Only"} **sem header** | 200 | user.to_dict() — qualquer anônimo renomeia qualquer usuário |
| 44 | PUT | /users/999 | {"name":"x"} | 404 | {error} |
| 45 | PUT | /categories/5 | {"name":"QA2"} | 200 | category.to_dict() — **sem auth** |
| 46 | PUT | /categories/999 | {"name":"x"} | 404 | {error:"Categoria não encontrada"} |
| 47 | PUT | /categories/5 | corpo `x`, sem Content-Type | 415 | application/json {error:"Did not attempt to load JSON data…"} |
| 48 | PUT | /categories/5 | `null` (JSON) | 400 | {error:"Dados inválidos"} |
| 49 | POST | /tasks | {"title":"Task da Ana","user_id":4} | 201 | task.to_dict() (id 12, category_id null) |
| 50 | DELETE | /tasks/11 | sem header | 401 | {error:"Não autorizado"} |
| 51 | DELETE | /tasks/11 | + `X-Admin-Token` | 200 | {message:"Task deletada com sucesso"} |
| 52 | DELETE | /tasks/999 | + header | 404 | {error} |
| 53 | GET | /tasks/12 | - | 200 | task da Ana existe antes da deleção do usuário |
| 54 | DELETE | /users/4 | sem header | 401 | {error:"Não autorizado"} |
| 55 | DELETE | /users/4 | + header | 200 | {message:"Usuário deletado com sucesso"} |
| 56 | GET | /tasks/12 | - | 404 | task 12 apagada em cascata com o usuário 4 |
| 57 | DELETE | /users/999 | + header | 404 | {error} |
| 58 | DELETE | /categories/5 | sem header | 401 | {error:"Não autorizado"} |
| 59 | DELETE | /categories/5 | + header | 200 | {message:"Categoria deletada"} |
| 60 | DELETE | /categories/999 | + header | 404 | {error} |
| 61 | DELETE | /categories/4 | + header | 200 | {message:"Categoria deletada"} |
| 62 | GET | /tasks/4 | - | 200 | `category_id` virou null (SET NULL via ORM) |
| 63 | DELETE | /users/5 | + header | 200 | limpeza do usuário admin criado em #34 |

Observações:
- **Log limpo**: `.refactor-arch/baseline-server.log` (83 linhas) não tem traceback, `DeprecationWarning` nem `LegacyAPIWarning` com `-W default` no Python 3.14.3 / SQLAlchemy 2.1.8. O único WARNING é o aviso padrão do Werkzeug sobre servidor de desenvolvimento.
- **Nenhum 500**: todas as entradas inválidas respondem 4xx em JSON; 404 e 405 de rota/método inexistente também são JSON (error handler central), mas com a **mensagem padrão do Werkzeug em inglês**, diferente das mensagens de domínio em português.
- **Sem vazamento de `password`**: nenhuma das respostas (#11, #22, #30, #34, #41, #43) contém o hash.
- **Token de login previsível e nunca verificado**: `fake-jwt-token-<id>`, idêntico entre logins (#22 vs #23); nenhuma rota lê `Authorization`. A única credencial que vale algo é o `X-Admin-Token` estático.
- **Escritas sem autenticação**: `POST /tasks` (#26), `PUT /tasks/<id>` (#37), `POST /users` (#30), `PUT /users/<id>` sem `role` (#43), `POST /categories` (#35), `PUT /categories/<id>` (#45). Só os três DELETE e as mudanças de `role` exigem token.
- **Leituras de PII sem autenticação**: `GET /users` (#10), `GET /users/<id>` (#11) e `GET /reports/user/<id>` (#16) devolvem nome + e-mail de todos os usuários.
- `/health` usa `datetime.datetime.now()` (hora local: 11:56) enquanto `created_at`/`generated_at` usam UTC naive (14:56) — inconsistência de fuso herdada do contrato original.
- Integridade: cascata usuário→tasks e `SET NULL` categoria→tasks funcionam (#56, #62), porém via ORM/PRAGMA: o `instance/tasks.db` atual **não** tem as cláusulas `ondelete` no DDL (`sqlite3 instance/tasks.db ".schema tasks"` → `FOREIGN KEY(user_id) REFERENCES users (id)` sem `ON DELETE`), porque `create_all()` não altera tabela existente.
- Nenhuma rota destrutiva global (reset de banco / SQL arbitrário) existe.
- Servidor do baseline encerrado (`kill 63132`; `lsof -nP -iTCP:5401 -sTCP:LISTEN` vazio).
