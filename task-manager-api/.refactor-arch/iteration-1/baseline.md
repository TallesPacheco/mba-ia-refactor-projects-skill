# Baseline — task-manager-api
Boot: `.venv/bin/python -W default -m flask --app app run --host 127.0.0.1 --port 5301` (porta 5301; o original `python app.py` tem `debug=True, host='0.0.0.0', port=5000` hardcoded — o bloco `__main__` só chama `app.run`, e `db.create_all()` roda no import) | Seed: `.venv/bin/python seed.py` (apaga e recria users/categories/tasks em `instance/tasks.db`, gitignored; rodado antes do boot)
Versões: Python 3.14.3 / Flask 3.0.0 / Flask-SQLAlchemy 3.1.1 (SQLAlchemy 2.1.8 transitivo) / Werkzeug 3.1.9 / Flask-Cors 4.0.0
Banco: `sqlite:///tasks.db` → resolvido pelo Flask-SQLAlchemy 3 para `instance/tasks.db`. Recriar: `.venv/bin/python seed.py` (o seed limpa as tabelas; IDs voltam a começar em 1).

| # | Método | Path | Payload | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | / | - | 200 | {message, version} |
| 2 | GET | /health | - | 200 | {status, timestamp} (timestamp em hora local, `datetime.now()`) |
| 3 | GET | /tasks | - | 200 | lista (10) de {id,title,description,status,priority,user_id,category_id,created_at,updated_at,due_date,tags[],overdue,user_name,category_name} |
| 4 | GET | /tasks/1 | - | 200 | {id,title,description,status,priority,user_id,category_id,created_at,updated_at,due_date,tags,overdue} |
| 5 | GET | /tasks/999 | - | 404 | {error:"Task não encontrada"} |
| 6 | GET | /tasks/search?q=API | - | 200 | lista de task.to_dict() (sem overdue) — ids 5,7 |
| 7 | GET | /tasks/search?status=pending&priority=1 | - | 200 | lista de task.to_dict() — ids 1,4 |
| 8 | GET | /tasks/search?priority=abc | - | 500 | HTML do Werkzeug (ValueError: invalid literal for int()) |
| 9 | GET | /tasks/stats | - | 200 | {total:10,pending:6,in_progress:2,done:1,cancelled:1,overdue:2,completion_rate:10.0} |
| 10 | GET | /users | - | 200 | lista (3) de {id,name,email,role,active,created_at,task_count} |
| 11 | GET | /users/1 | - | 200 | {id,name,email,**password** (hash MD5),role,active,created_at,tasks[]} |
| 12 | GET | /users/999 | - | 404 | {error:"Usuário não encontrado"} |
| 13 | GET | /users/1/tasks | - | 200 | lista de {id,title,description,status,priority,created_at,due_date,overdue} |
| 14 | GET | /users/999/tasks | - | 404 | {error} |
| 15 | GET | /reports/summary | - | 200 | {generated_at,overview{total_tasks,total_users,total_categories},tasks_by_status{…},tasks_by_priority{critical,high,medium,low,minimal},overdue{count,tasks[{id,title,due_date,days_overdue}]},recent_activity{…},user_productivity[…]} |
| 16 | GET | /reports/user/1 | - | 200 | {user{id,name,email},statistics{total_tasks,done,pending,in_progress,cancelled,overdue,high_priority,completion_rate}} |
| 17 | GET | /reports/user/999 | - | 404 | {error} |
| 18 | GET | /categories | - | 200 | lista (4) de {id,name,description,color,created_at,task_count} |
| 19 | POST | /login | {"email":"joao@email.com","password":"1234"} | 200 | {message,token:"fake-jwt-token-1",user{…,**password**}} |
| 20 | POST | /login | {"email":"joao@email.com","password":"x"} | 401 | {error:"Credenciais inválidas"} |
| 21 | POST | /login | {} | 400 | {error:"Dados inválidos"} |
| 22 | POST | /tasks | {"title":"Nova task baseline","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2026-12-01","tags":["a","b"]} | 201 | task.to_dict() (id 11, tags ["a","b"], due_date "2026-12-01 00:00:00") |
| 23 | POST | /tasks | {"title":"ab"} | 400 | {error:"Título muito curto"} |
| 24 | POST | /tasks | {"title":"Prioridade str","priority":"2"} | 500 | HTML do Werkzeug (TypeError '<' str/int) |
| 25 | POST | /tasks | {"title":"user ruim","user_id":999} | 404 | {error:"Usuário não encontrado"} |
| 26 | POST | /users | {"name":"Ana","email":"ana@email.com","password":"segredo"} | 201 | {id:4,name,email,**password**,role:"user",active,created_at} |
| 27 | POST | /users | (mesmo payload) | 409 | {error:"Email já cadastrado"} |
| 28 | POST | /users | {"name":"X","email":"bad","password":"segredo"} | 400 | {error:"Email inválido"} |
| 29 | POST | /categories | {"name":"QA","color":"#ffffff"} | 201 | {id:5,name,description:"",color,created_at} |
| 30 | POST | /categories | {} | 400 | {error:"Dados inválidos"} |
| 31 | PUT | /tasks/11 | {"status":"done","title":"Nova task atualizada"} | 200 | task.to_dict() |
| 32 | PUT | /tasks/11 | {"status":"xx"} | 400 | {error:"Status inválido"} |
| 33 | PUT | /tasks/999 | {"status":"done"} | 404 | {error} |
| 34 | PUT | /users/4 | {"name":"Ana Maria","role":"manager"} | 200 | user.to_dict() (com **password**) |
| 35 | PUT | /users/4 | {"role":"root"} | 400 | {error:"Role inválido"} |
| 36 | PUT | /users/999 | {"name":"x"} | 404 | {error} |
| 37 | PUT | /categories/5 | {"name":"QA2"} | 200 | category.to_dict() |
| 38 | PUT | /categories/999 | {"name":"x"} | 404 | {error:"Categoria não encontrada"} |
| 39 | PUT | /categories/5 | (sem Content-Type) | 415 | HTML do Werkzeug |
| 40 | PUT | /categories/5 | null (JSON) | 500 | HTML do Werkzeug (TypeError NoneType not iterable) |
| 41 | POST | /tasks | {"title":"Task da Ana","user_id":4} | 201 | task.to_dict() (id 12) |
| 42 | DELETE | /tasks/11 | - | 200 | {message:"Task deletada com sucesso"} |
| 43 | DELETE | /tasks/999 | - | 404 | {error} |
| 44 | DELETE | /users/4 | - | 200 | {message:"Usuário deletado com sucesso"} (task 12 apagada junto — GET /tasks/12 → 404) |
| 45 | DELETE | /users/999 | - | 404 | {error} |
| 46 | DELETE | /categories/5 | - | 200 | {message:"Categoria deletada"} |
| 47 | DELETE | /categories/999 | - | 404 | {error} |
| 48 | DELETE | /categories/4 | - | 200 | {message} — task 4 fica com category_id null (GET /tasks/4 → 200, category_id null) |

Observações:
- Warnings no log: `LegacyAPIWarning: Query.get()` (14 ocorrências em task/user/report routes) e `DeprecationWarning: datetime.utcnow()` (rotas, models via default do SQLAlchemy e seed.py).
- 3 crashes 500 com página HTML do Werkzeug (não JSON): `/tasks/search?priority=abc` (ValueError), `POST /tasks` com priority string (TypeError), `PUT /categories/5` com body `null` (TypeError).
- Vazamento de dado sensível: `password` (hash MD5 sem salt; `81dc9bdb52d04dc20036dbd8313ed055` = md5("1234")) em GET /users/<id>, POST/PUT /users e POST /login.
- Token de login falso e previsível: `fake-jwt-token-<id>`; nenhuma rota exige autenticação (DELETE /users, /categories, /tasks abertos).
- `/health` usa hora local (`datetime.now()`), demais timestamps em UTC naive.
- Nenhuma rota destrutiva global (reset) existe.
