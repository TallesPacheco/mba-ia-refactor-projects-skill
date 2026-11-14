================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.14 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.1.8)
Files:   15 analyzed | ~1158 lines of code

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 7 | LOW: 4

## Findings

### [CRITICAL] Credenciais / segredos hardcoded (AP-01)
File: app.py:13
File: services/notification_service.py:7, 9-10
File: seed.py:19, 26, 33
Description: `app.config['SECRET_KEY'] = 'super-secret-key-123'` literal no entry point; credenciais SMTP literais no `NotificationService` (`email_user = 'taskmanager@gmail.com'`, `email_password = 'senha123'`); senhas de seed em texto puro (`'1234'`, `'abcd'`, `'pass'`), inclusive a do usuário admin. A URI do banco (`app.py:11`) também é literal, sem leitura de ambiente.
Impact: qualquer pessoa com acesso ao repositório obtém a chave de assinatura de sessão do Flask e a senha da conta de e-mail; a senha do admin seed (`joao@email.com` / `1234`) é conhecida publicamente (baseline: POST /login com essa senha → 200, role "admin"). Impossível trocar segredos por ambiente sem editar código.
Recommendation: mover SECRET_KEY, URI do banco e credenciais SMTP para `config/settings.py` lendo variáveis de ambiente (python-dotenv já está no requirements), com `.env.example` de valores fictícios; seed lê senhas de dev do ambiente ou gera aleatórias (playbook PB-01)

### [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models/user.py:16-25
File: routes/user_routes.py:33, 85, 129, 209
Description: `User.to_dict()` inclui `'password': self.password` (linha 21), e esse dict é devolvido em GET /users/<id>, POST /users, PUT /users/<id> e dentro de `user` na resposta de POST /login.
Impact: baseline: GET /users/1 → 200 com `"password":"81dc9bdb52d04dc20036dbd8313ed055"` (md5 de "1234"); POST /login e POST/PUT /users também retornam o hash. Combinado com AP-05 (MD5 sem salt), o hash é revertido por rainbow table em segundos.
Recommendation: remover `password` de `to_dict()` (serialização pública separada), nunca retornar hash em nenhuma resposta (playbook PB-06)

### [CRITICAL] Hash de senha fraco (AP-05)
File: models/user.py:29, 32
File: routes/user_routes.py:64, 115
Description: `set_password` usa `hashlib.md5(pwd.encode()).hexdigest()` sem salt; `check_password` compara com `==` (não constante no tempo). Política mínima de senha de 4 caracteres.
Impact: hashes idênticos para senhas iguais, reversíveis por tabela pré-computada (baseline: hash de "1234" exposto e reconhecível); ataque de timing na comparação.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (já instalado com Flask), seed gerando hashes com o novo algoritmo e verificação compatível (playbook PB-05)

### [CRITICAL] Endpoints destrutivos e de usuários sem autenticação/autorização (AP-06)
File: routes/user_routes.py:52, 71-72, 119-122, 134-151, 210
File: routes/task_routes.py:225-238
File: routes/report_routes.py:211-223
File: models/user.py:34-38
Description: nenhuma rota exige credencial (sem `before_request`, decorator ou middleware de auth). O "login" emite `'fake-jwt-token-' + str(user.id)`, token previsível que nunca é validado. POST /users aceita `role` do corpo (`'admin'` permitido) e PUT /users/<id> permite promover qualquer usuário a admin; DELETE /users/<id>, /tasks/<id> e /categories/<id> são anônimos. `User.is_admin()` existe e nunca é chamado.
Impact: qualquer cliente anônimo pode criar um admin, escalar privilégios, apagar usuários com todas as suas tasks e listar e-mails de todos os usuários (baseline: DELETE /users/4 → 200 sem credencial, apagando a task 12; POST /login → `"token":"fake-jwt-token-1"`).
Recommendation: middleware/decorator de autenticação por token (header documentado + token de dev em `.env`), exigir admin para DELETE, alteração de `role` e criação de admin; manter as rotas, apenas protegê-las (playbook PB-07)

### [CRITICAL] Debug ligado / bind em 0.0.0.0 (AP-07)
File: app.py:33-34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)` com debug, host e porta literais no entry point.
Impact: `python app.py` expõe o debugger interativo do Werkzeug (execução remota de código via console) em todas as interfaces de rede; porta não configurável (o baseline precisou subir via `flask --app app run --port 5301` para contornar).
Recommendation: ler `DEBUG`, `HOST` (default 127.0.0.1) e `PORT` da config/ambiente, debug desligado por padrão (playbook PB-01, PB-16)

### [HIGH] Regra de negócio dentro das rotas; camada services não usada (AP-08)
File: routes/task_routes.py:11-63, 85-154, 156-223, 273-299
File: routes/user_routes.py:42-90, 134-151, 153-183
File: routes/report_routes.py:12-101, 103-155
File: services/notification_service.py:4-48
Description: os handlers validam payload, consultam o ORM, calculam atraso (`overdue`), taxas de conclusão, contagens por status/prioridade, fazem cascata de deleção, commit e serializam manualmente — tudo inline (ex.: `summary_report` com 90 linhas; `create_task`/`update_task` com ~70 linhas cada). A pasta `services/` existe, mas `NotificationService` nunca é importado; `Task.is_overdue()` (models/task.py:50-60) existe e as rotas reimplementam a regra.
Impact: regras de negócio não testáveis sem HTTP, divergência entre endpoints (ex.: GET /tasks calcula `overdue`, /tasks/search não), controllers impossíveis de reutilizar; a camada services é decorativa.
Recommendation: extrair `services/` (task_service, user_service, report_service) com a regra pesada e controllers finos chamando-os; usar `Task.is_overdue()` como fonte única (playbook PB-04)

### [HIGH] Escritas multi-etapa sem transação (AP-10)
File: seed.py:11-14, 37, 63, 92
Description: o seed apaga todas as tabelas e confirma (`commit` na linha 14) antes de inserir; depois grava users, categories e tasks em três commits separados (37, 63, 92).
Impact: qualquer falha após a linha 14 (ex.: dado inválido em uma task) deixa o banco apagado ou parcialmente populado (usuários sem categorias/tasks), sem rollback possível.
Recommendation: executar limpeza + inserções em uma única transação (`flush()` para obter IDs e um único `commit`, com rollback em erro) (playbook PB-09)

### [HIGH] Sem módulo de config / app factory; efeitos colaterais no import (AP-11)
File: app.py:9-13, 15-20, 30-31
File: seed.py:2
Description: `app = Flask(__name__)` global com config literal (`app.config[...] = '...'`), `CORS`, `init_app` e blueprints registrados no import, e `with app.app_context(): db.create_all()` em nível de módulo. Não há `create_app()` nem `config.py`; `python-dotenv` está declarado e nunca é importado. O seed faz `from app import app, db`, disparando todo o boot (e `create_all`) só para popular dados.
Impact: impossível criar uma app de teste com outra config/banco; qualquer import de `app` cria tabelas no `instance/tasks.db`; config por ambiente inexistente.
Recommendation: `config/settings.py` por ambiente + `create_app(config)` como composition root, `create_all` dentro da factory, mantendo `app = create_app()` em nível de módulo para `python app.py`, `flask --app app` e o seed (playbook PB-01, PB-16)

### [MEDIUM] Erros engolidos, `except` genérico, sem error handler central (AP-12)
File: routes/task_routes.py:62, 137, 151, 204, 221, 236
File: routes/user_routes.py:87, 130, 149
File: routes/report_routes.py:186, 207, 221
File: utils/helpers.py:46, 49, 88
File: services/notification_service.py:23
Description: 10 `except:` nus e 4 `except Exception` que escondem a causa (`get_tasks` captura tudo e devolve só "Erro interno"); erros só vão para `print(str(e))`. Não existe `errorhandler`/`register_error_handler`, e cada handler repete seu try/except/rollback.
Impact: baseline: três requisições inválidas geraram 500 com página **HTML** do Werkzeug em vez do JSON `{"error": ...}` usado pelo resto da API (`/tasks/search?priority=abc`, `POST /tasks` com priority string, `PUT /categories/5` com body `null`); 415 também sai em HTML. Formato de erro inconsistente para clientes e falhas sem log estruturado.
Recommendation: exceções de domínio + error handler central que devolve `{"error": "..."}` com status correto (404/400/409/500) e loga o stack trace no servidor; remover try/except repetidos (playbook PB-08)

### [MEDIUM] Queries N+1 / agregação em memória (AP-13)
File: routes/task_routes.py:41-57, 275-286
File: routes/user_routes.py:12-22
File: routes/report_routes.py:15-28, 30-43, 53-61, 159-163
Description: GET /tasks faz `User.query.get` e `Category.query.get` por task (1 + 2N queries); GET /users acessa `len(u.tasks)` lazy por usuário; `summary_report` executa 11 `COUNT` separados, carrega todas as tasks para contar atrasadas e faz uma query por usuário; GET /categories faz um `COUNT` por categoria; `/tasks/stats` repete 5 COUNTs + carrega tudo.
Impact: número de queries cresce linearmente com tasks/usuários/categorias; relatórios ficam lentos com volume real.
Recommendation: `joinedload`/`selectinload` para user/category, `GROUP BY status`/`priority` com `func.count`, contagem por usuário/categoria com subquery agregada e filtro de atraso no SQL (playbook PB-10)

### [MEDIUM] Validação de entrada ausente (AP-14)
File: routes/task_routes.py:96-100, 113, 166-171, 182, 260-264
File: routes/user_routes.py:102-103, 114-117, 124-125
File: routes/report_routes.py:173-180, 196-202
Description: `priority` comparado sem checar tipo (`priority < 1` com string → TypeError); `len(data['title'])` sem checar `None`/tipo; `int(priority)`/`int(user_id)` de query string sem tratamento; PUT /users aceita `name` vazio e `active` de qualquer tipo; `color` de categoria nunca validado (o helper `is_valid_color` existe e não é usado); `update_category` não verifica se o corpo é `null`. `marshmallow` está no requirements e nunca é importado.
Impact: baseline: `GET /tasks/search?priority=abc` → 500 (ValueError), `POST /tasks {"priority":"2"}` → 500 (TypeError), `PUT /categories/5` com `null` → 500 (TypeError); dados inválidos persistidos (cor arbitrária, nome vazio).
Recommendation: validação centralizada por recurso (schemas marshmallow já declarado, ou validadores no service) retornando 400 com `{"error": ...}` antes de tocar o banco (playbook PB-11)

### [MEDIUM] Código duplicado (AP-15)
File: routes/task_routes.py:17-39, 71-80, 110, 177, 283-287
File: routes/user_routes.py:61, 71, 106, 120, 162-180
File: routes/report_routes.py:33-37, 132-135
File: models/task.py:38-60
File: utils/helpers.py:19-23, 57-108, 110-116
Description: a regra de atraso (`due_date < utcnow()` e status não done/cancelled) está copiada em 7 lugares, enquanto `Task.is_overdue()` não é usado; a lista de status aparece em 5 lugares e a de roles em 3; a regex de e-mail em 3; serialização manual de task (task_routes 17-28, user_routes 162-169) duplica `Task.to_dict()`; `utils.helpers.process_task_data`, `validate_email`, `Task.validate_status/validate_priority` e as constantes `VALID_STATUSES`/`VALID_ROLES` são versões prontas nunca chamadas.
Impact: regras já divergem (POST /tasks valida data só em `%Y-%m-%d`, `parse_date` aceita também `%d/%m/%Y`; GET /tasks inclui `overdue`, `/tasks/search` não); qualquer mudança de regra precisa ser feita em vários arquivos.
Recommendation: fonte única por regra (constantes + `Task.is_overdue()` + validadores no service), apagando as cópias e os helpers não utilizados (playbook PB-18)

### [MEDIUM] Deprecated APIs (AP-17)
File: routes/task_routes.py:31, 72, 215, 285   — `datetime.utcnow()` → `datetime.now(timezone.utc)` (tratando colunas naive)
File: routes/report_routes.py:35, 42, 45, 71, 133 — `datetime.utcnow()` → `datetime.now(timezone.utc)`
File: routes/user_routes.py:172                — `datetime.utcnow()` → `datetime.now(timezone.utc)`
File: models/task.py:15, 16, 52; models/category.py:11; models/user.py:14 — `default=datetime.utcnow` → callable aware/naive explícito
File: seed.py:66, 67, 69, 70, 74; services/notification_service.py:35; utils/helpers.py:38 — `datetime.utcnow()` → `datetime.now(timezone.utc)`
File: routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227 — `Model.query.get(id)` → `db.session.get(Model, id)`
File: routes/user_routes.py:29, 94, 136, 155; routes/report_routes.py:105, 192, 213 — `Model.query.get(id)` → `db.session.get(Model, id)`
File: routes/*.py, seed.py (56 ocorrências de `Model.query.`: `grep -nE "\b[A-Z]\w*\.query\."`) — Query API legada → `db.session.execute(db.select(...))` / `db.session.scalar(...)`
File: routes/task_routes.py:141, 210; utils/helpers.py:103 — `type(x) == list` → `isinstance(x, list)`
Description: APIs marcadas como deprecated/legadas no Python 3.12+ e no SQLAlchemy 2.x instalados (SQLAlchemy 2.1.8). `hashlib.md5` para senha está registrado em AP-05.
Impact: baseline: log com 14 `LegacyAPIWarning: The Query.get() method is considered legacy` e vários `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal`; quebra em futuras versões do Python/SQLAlchemy.
Recommendation: migrar para `db.session.get`, `db.select`, `datetime.now(timezone.utc)` (mantendo valores naive em UTC no banco e o formato serializado atual) e `isinstance` (playbook PB-13)

### [MEDIUM] Middleware mal configurado — CORS aberto, sem middleware de auth/erro (AP-18)
File: app.py:15
Description: `CORS(app)` sem `origins`, liberando qualquer origem para todas as rotas, inclusive as destrutivas; não há camada de middleware para autenticação, erros ou logging de requisições.
Impact: qualquer site pode chamar a API a partir do navegador da vítima; somado a AP-06, permite deleções e escalada de privilégio cross-origin.
Recommendation: origens permitidas via config (`CORS_ORIGINS`), registro de CORS, auth e error handler na app factory (playbook PB-19)

### [MEDIUM] Integridade referencial ausente / cascata manual (AP-19)
File: models/task.py:13-14, 20-21
File: routes/user_routes.py:140-142
File: routes/report_routes.py:211-219
Description: `ForeignKey` sem `ondelete` e `relationship` sem `cascade`; SQLite sem `PRAGMA foreign_keys=ON`; DELETE /users apaga as tasks em loop manual na rota; DELETE /categories deixa o ORM anular `category_id` das tasks silenciosamente; `Task.user_id` aceita IDs inexistentes se escritos fora das rotas.
Impact: baseline: DELETE /categories/4 → 200 e GET /tasks/4 passou a ter `category_id: null` sem aviso; a cascata de usuário depende de código na rota e não vale para outros caminhos de escrita.
Recommendation: declarar a política de deleção no model (`cascade='all, delete-orphan'` para tasks do usuário, `ondelete='SET NULL'` para categoria), ligar `PRAGMA foreign_keys` no connect e remover o loop manual, preservando o comportamento observável atual (playbook PB-20)

### [LOW] Magic numbers / strings (AP-20)
File: routes/task_routes.py:96, 99, 104, 113, 167, 169, 182
File: routes/user_routes.py:52, 64, 115
File: routes/report_routes.py:24-28, 45, 129, 180
File: app.py:28, 34
Description: limites de título 3/200, faixa de prioridade 1–5, prioridade default 3, senha mínima 4, janela de 7 dias, "alta prioridade" `<= 2`, cor `'#000000'`, versão `'1.0'` e porta 5000 como literais espalhados; status (`'done'`, `'cancelled'`...) como strings soltas. `utils/helpers.py:110-116` já define `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`, nunca usados.
Impact: regras de domínio difíceis de achar e alterar; risco de divergência entre endpoints.
Recommendation: módulo de constantes único (reaproveitando as de `utils/helpers.py`) usado por models/services/validadores (playbook PB-14)

### [LOW] Nomenclatura ruim / módulo com nome enganoso (AP-21)
File: routes/report_routes.py:24-28, 157-223
File: models/category.py:14
File: seed.py:16, 23, 30, 39, 45, 51, 57, 79
Description: variáveis `p1`..`p5`, `u1`..`u3`, `c1`..`c4`, `t`, `d`, `cat`; o CRUD completo de `/categories` vive em `report_routes.py` sob o blueprint `reports`.
Impact: leitura e navegação mais difíceis; quem procura o código de categorias não o encontra pelo nome do arquivo.
Recommendation: nomes descritivos internos e mover o CRUD de categorias para controller/rota próprios, sem alterar paths nem campos HTTP (playbook PB-18)

### [LOW] `print` como logging (AP-22)
File: routes/task_routes.py:149, 153, 219, 234
File: routes/user_routes.py:83, 89, 147
File: services/notification_service.py:21, 24
File: utils/helpers.py:39, 41
File: seed.py:93-96
Description: eventos e erros registrados com `print`, sem nível, timestamp ou contexto de requisição; erros de banco viram `print(f"ERRO: {str(e)}")`.
Impact: logs não filtráveis por nível nem roteáveis; erros reais misturados a mensagens informativas no stdout.
Recommendation: módulo `logging` configurado na app factory (`logger.info`/`logger.exception`); manter `print` só na saída do script de seed, se desejado (playbook PB-15)

### [LOW] Imports não usados / código morto / dependências não usadas (AP-23)
File: app.py:7                  — `os`, `sys`, `json` não usados
File: routes/task_routes.py:7   — `json`, `os`, `sys`, `time` não usados
File: routes/user_routes.py:6   — `hashlib`, `json` não usados
File: routes/report_routes.py:7-8 — `format_date`, `calculate_percentage`, `json` importados e não usados
File: models/task.py:3          — `json` não usado
File: utils/helpers.py:3-7      — `os`, `json`, `sys`, `math`, `hashlib` não usados; funções `sanitize_string`, `generate_id`, `log_action`, `process_task_data`, `validate_email`, `is_valid_color` nunca chamadas
File: services/notification_service.py:1-48 — módulo inteiro nunca importado
File: requirements.txt:4-6      — `marshmallow`, `requests`, `python-dotenv` declarados e nunca importados
Description: imports, funções, constantes e um módulo de serviço inteiro sem uso; três dependências instaladas sem nenhum import (verificado com grep por `import`/`from` em todos os arquivos-fonte).
Impact: ruído na leitura, falsa impressão de camadas/validações existentes, superfície de dependências maior sem benefício.
Recommendation: remover imports e código morto ou torná-los a fonte única (helpers/constantes reaproveitados em PB-14/PB-18); retirar dependências não usadas ou passar a usá-las de fato (python-dotenv na config) (playbook PB-18)

Verificados sem ocorrência: AP-02 (sem SQL montado por string; `Task.title.like(f'%{query}%')` em routes/task_routes.py:252-253 usa bind parameter do SQLAlchemy — não é injeção, apenas curinga `%`/`_` não escapado), AP-03 (maior arquivo routes/task_routes.py com 299 linhas, domínio único; problema tratado em AP-08), AP-09 (sem `global`/conexão compartilhada manual; `db = SQLAlchemy()` é o padrão da extensão; o estado em memória do `NotificationService` está em código morto, AP-23), AP-16 (sem callbacks aninhados).

================================
Total: 19 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
