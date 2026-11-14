================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
code-smells-project/
├── app.py (composition root: create_app() + app = create_app() + __main__ lendo HOST/PORT/DEBUG da config)
├── config/
│   ├── __init__.py
│   └── settings.py
├── db/
│   ├── __init__.py
│   ├── connection.py          (conexão por requisição em flask.g, PRAGMA foreign_keys, conexão read-only p/ admin)
│   └── schema.py              (CREATE TABLE com FK/UNIQUE/NOT NULL + seed idempotente com hashes)
├── models/
│   ├── __init__.py
│   ├── constants.py
│   ├── admin_model.py
│   ├── pedido_model.py
│   ├── produto_model.py
│   └── usuario_model.py
├── services/
│   ├── __init__.py
│   ├── notification_service.py
│   ├── pedido_service.py
│   ├── relatorio_service.py
│   └── usuario_service.py
├── controllers/
│   ├── __init__.py
│   ├── admin_controller.py
│   ├── health_controller.py
│   ├── pedido_controller.py
│   ├── produto_controller.py
│   ├── relatorio_controller.py
│   └── usuario_controller.py
├── validators/
│   ├── __init__.py
│   ├── common.py
│   ├── pedido_validator.py
│   ├── produto_validator.py
│   └── usuario_validator.py
├── views/
│   ├── __init__.py
│   ├── admin_routes.py
│   ├── main_routes.py
│   ├── pedido_routes.py
│   ├── produto_routes.py
│   ├── relatorio_routes.py
│   └── usuario_routes.py
├── middlewares/
│   ├── __init__.py
│   ├── auth.py
│   └── error_handler.py
├── errors.py
├── README.md
├── requirements.txt (inalterado)
└── .env.example

## Changes Applied
  [AP-01] SECRET_KEY, ADMIN_TOKEN, DEBUG, HOST, PORT, DATABASE_PATH, CORS_ORIGINS, LOG_LEVEL lidos de env com defaults só de dev (o segredo vazado não é reutilizado); seed sem senhas em texto (hashes scrypt pré-computados); boot falha em APP_ENV=production sem SECRET_KEY/ADMIN_TOKEN → config/settings.py, db/schema.py, .env.example
  [AP-02] Todas as queries com placeholders `?`; busca com cláusulas fixas + lista de parâmetros; f-strings só interpolam listas de colunas constantes/placeholders → models/*.py
  [AP-03] models.py/controllers.py/database.py (monolito) divididos em config/db/models/services/controllers/validators/views/middlewares e apagados; app.py virou composition root → todos os pacotes
  [AP-04] `senha` removida de toda serialização de usuário (SELECT de colunas explícitas); /health sem secret_key/db_path/debug; logs sem e-mail → models/usuario_model.py, controllers/health_controller.py, services/usuario_service.py
  [AP-05] werkzeug generate_password_hash no cadastro/seed e check_password_hash no login (busca por e-mail, verificação em código); senha legada em texto é aceita uma vez e regravada com hash → services/usuario_service.py, db/schema.py
  [AP-06] Decorator require_admin (header X-Admin-Token, hmac.compare_digest) em /admin/reset-db, /admin/query, POST/PUT/DELETE /produtos, GET /usuarios, GET /pedidos, PUT /pedidos/<id>/status, GET /relatorios/vendas; /admin/query restrito a um único SELECT em conexão SQLite read-only → middlewares/auth.py, views/*.py, controllers/admin_controller.py, db/connection.py
  [AP-07] debug off por padrão (FLASK_DEBUG=1 para ligar), host padrão 127.0.0.1, porta 5000 configurável por PORT; "ambiente" do /health vem de APP_ENV → app.py, config/settings.py
  [AP-08] Regras de pedido (estoque, total, baixa, notificações), relatório (faixas de desconto) e autenticação movidas para services; controllers finos; rotas só parse → controller → jsonify → services/*.py, controllers/*.py, views/*.py
  [AP-09] Conexão global com check_same_thread=False substituída por conexão por requisição (flask.g + teardown_appcontext); models recebem a conexão por parâmetro → db/connection.py, models/*.py
  [AP-10] criar pedido numa transação única (`with conn:` commit/rollback) com baixa de estoque condicional `WHERE estoque >= ?` verificando rowcount (rollback validado: 2 itens de 5 com estoque 8 → 400 e estoque intacto) → services/pedido_service.py, models/produto_model.py
  [AP-11] create_app(config_class) com config.from_object, schema/seed explícitos na factory, `app = create_app()` mantido para `flask --app app run` → app.py
  [AP-12] 17 try/except genéricos removidos; errors.py com AppError/ValidationError/UnauthorizedError/NotFoundError/ConflictError; error handler central com chave "erro" (preserva extras como "sucesso": false), HTTPException em JSON, 500 genérico logado → errors.py, middlewares/error_handler.py
  [AP-13] Pedidos com 1 query LEFT JOIN (itens + nome do produto) agrupada em Python; produtos do pedido em 1 query IN; relatório em 1 query agregada (COUNT/SUM/CASE) → models/pedido_model.py, models/produto_model.py
  [AP-14] Validadores por recurso: tipos numéricos/inteiros, quantidade > 0, usuario_id existente, categoria e tamanho do nome também no PUT, filtros de preço inválidos → 400, body ausente → 400, e-mail com formato, pedido inexistente → 404 → validators/*.py, services/pedido_service.py
  [AP-15] row_to_produto/row_to_usuario únicos, uma função listar pedidos com filtro opcional, um validador de produto para POST e PUT → models/*.py, validators/produto_validator.py
  [AP-18] CORS restrito a CORS_ORIGINS (default http://localhost:3000, http://127.0.0.1:3000) registrado na factory → app.py
  [AP-19] FKs pedidos.usuario_id e itens_pedido.pedido_id (ON DELETE CASCADE), email UNIQUE, NOT NULL nos campos obrigatórios, PRAGMA foreign_keys=ON por conexão; e-mail duplicado → 409; pedido para usuário inexistente → 400 (parcial: itens_pedido.produto_id sem FK, ver Remaining) → db/schema.py, db/connection.py, services/*.py
  [AP-20] Constantes APP_VERSION, CATEGORIAS_VALIDAS, STATUS_*, NOME_PRODUTO_MIN/MAX, FAIXAS_DESCONTO, TIPO_*; porta/caminho do banco na config → models/constants.py, config/settings.py
  [AP-21] `id` interno renomeado (produto_id, usuario_id), cursor2/cursor3/prod eliminados; parâmetro de rota `<int:id>` mantido no contrato → models/*.py, controllers/*.py
  [AP-22] Todos os print() trocados por logging (basicConfig na factory); notificações viraram Notifier injetado que loga sem PII → services/notification_service.py, app.py
  [AP-23] Imports mortos (os, sqlite3) eliminados com a remoção de database.py/models.py; nenhum import não usado nos novos módulos

## Validation
  ✓ Application boots without errors (`PORT=5104 .venv/bin/python app.py`, porta 5104; log sem traceback/exception, sem DeprecationWarning com PYTHONWARNINGS=default)
  ✓ All baseline endpoints respond (54/54 requisições do baseline repetidas e respondendo; 19/19 rotas registradas; todas com mesmo status e shape exceto as marcadas ≈ na tabela (mudanças de segurança/validação intencionais), nenhuma ≠; 10/10 rotas protegidas → 401 sem token / com token errado e sucesso com `X-Admin-Token: dev-admin-token`)
  ✓ Original start command still works (`python app.py` → 127.0.0.1:5000 por padrão, PORT por env; `flask --app app run --port 5103` também validado na iteração 2)
  ✓ Seed / initial data loads (loja.db apagado antes de cada iteração; /health → produtos 10, usuarios 3; login admin@loja.com/admin123 → 200; hashes do seed conferem para admin123, 123456 e senha123)
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep AP-01..AP-11: sem literais de segredo/senha, sem SQL concatenado com valor, sem debug/0.0.0.0, sem global/check_same_thread, sem except Exception/str(e), sem print; ocorrências restantes do grep são falsos positivos: f-strings só com constantes de colunas/placeholders, nome do header X-Admin-Token, chaves "senha" internas de validador)
  ✓ Old monolith/duplicate files removed (controllers.py, models.py, database.py apagados; `grep` não encontra `import controllers`/`from database import`/`import models` de módulo antigo)
  ✓ .env.example created
  ✓ 3 iterações de validação (1: python app.py :5102; 2: flask CLI :5103 com script corrigido para usar o id retornado; 3: python app.py :5104 após trocar senhas do seed por hashes — saída idêntica à iteração 2 exceto ordem do header Allow); servidores parados (lsof 5101-5109 vazio)

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | / | 200 | 200 | = | |
| GET | /health | 200 | 200 | ≈ | secret_key, db_path, debug removidos (fix AP-04); "ambiente" agora vem de APP_ENV ("development" por padrão, antes literal "producao") |
| GET | /produtos | 200 | 200 | = | 10 itens |
| GET | /produtos/1 | 200 | 200 | = | |
| GET | /produtos/999 | 404 | 404 | = | |
| GET | /produtos/busca?q=gamer | 200 | 200 | = | 3 itens |
| GET | /produtos/busca?categoria=moveis&preco_min=100&preco_max=2000 | 200 | 200 | = | 1 item |
| GET | /produtos/busca?q=' OR 1=1-- | 500 | 200 | ≈ | lista vazia, sem erro SQL vazado (fix AP-02/AP-12) |
| GET | /produtos/busca?q=x') OR 1=1 -- | 200 (todos) | 200 (vazio) | = | injeção não funciona mais (fix AP-02) |
| GET | /usuarios | 200 | 401 sem token / 200 com `X-Admin-Token` | ≈ | auth adicionada (fix AP-06); campo "senha" removido (fix AP-04) |
| GET | /usuarios/1 | 200 | 200 | ≈ | campo "senha" removido (fix AP-04) |
| GET | /usuarios/999 | 404 | 404 | = | |
| GET | /pedidos | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| GET | /pedidos/usuario/2 | 200 | 200 | = | |
| GET | /relatorios/vendas | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06); valores diferem após #32 porque o pedido para usuário inexistente não é mais criado |
| POST | /login (admin123) | 200 | 200 | = | |
| POST | /login (senha errada) | 401 | 401 | = | |
| POST | /login (email "admin@loja.com' --") | 200 (bypass) | 401 | = | fix AP-02 |
| POST | /login {} | 400 | 400 | = | |
| POST | /login sem body/Content-Type | 500 | 400 | ≈ | `{"erro":"Email e senha são obrigatórios"}` em vez de 415 vazado (fix AP-12/AP-14) |
| POST | /produtos (válido) | 201 | 401 sem token / 201 com `X-Admin-Token` | = | auth adicionada (fix AP-06); id 11 |
| POST | /produtos {"nome":"X"} | 400 | 400 | = | |
| POST | /produtos categoria xyz | 400 | 400 | = | |
| POST | /produtos preco -1 | 400 | 400 | = | |
| POST | /produtos nome "O'Reilly" | 500 | 201 | ≈ | apóstrofo não quebra mais o SQL (fix AP-02); por isso os ids seguintes avançam 1 |
| POST | /usuarios (válido) | 201 | 201 | = | id 4; e-mail duplicado agora → 409 "Email já cadastrado" (fix AP-19) |
| POST | /usuarios {"nome":"Teste"} | 400 | 400 | = | |
| POST | /pedidos (válido) | 201 | 201 | = | pedido_id 1, total 6179.79 |
| POST | /pedidos produto 999 | 400 | 400 | = | |
| POST | /pedidos estoque insuficiente | 400 | 400 | = | |
| POST | /pedidos itens [] | 400 | 400 | = | |
| POST | /pedidos usuario_id 999 | 201 | 400 | ≈ | `{"erro":"Usuário não encontrado","sucesso":false}` (fix AP-14/AP-19) |
| PUT | /produtos/11 (válido) | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| PUT | /produtos/999 | 404 | 404 | = | |
| PUT | /produtos/11 {"nome":"x"} | 400 | 400 | = | |
| PUT | /produtos/11 nome "y" + categoria "invalida" | 200 | 400 | ≈ | PUT usa o mesmo validador do POST ("Nome muito curto"/categoria) (fix AP-14/AP-15) |
| PUT | /pedidos/1/status aprovado | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| PUT | /pedidos/1/status foo | 400 | 400 | = | |
| PUT | /pedidos/999/status | 200 | 404 | ≈ | `{"erro":"Pedido não encontrado"}` (fix AP-14) |
| DELETE | /produtos/<id> | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| DELETE | /produtos/<id> (repetido) / 999 | 404 | 404 | = | |
| POST | /admin/query SELECT | 200 | 401 sem token / 200 com `X-Admin-Token` | ≈ | auth + conexão read-only (fix AP-06); coluna senha agora contém hash |
| POST | /admin/query {} | 400 | 400 | = | |
| POST | /admin/query "SELEC x" | 500 | 400 | ≈ | "Apenas consultas SELECT são permitidas"; SELECT inválido → 400 "Query inválida"; não-SELECT (antes 200 "Query executada") → 400 (fix AP-06/AP-12) |
| POST | /admin/reset-db | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| GET | /nao-existe | 404 (HTML) | 404 (JSON `{"erro": ...}`) | ≈ | formato de erro padronizado (fix AP-12) |

## Remaining Known Issues
  - Token de admin: enviar o header `X-Admin-Token`. Em dev o valor padrão é `dev-admin-token`; em produção defina `ADMIN_TOKEN` (e `SECRET_KEY`) por env: com `APP_ENV=production` o boot falha se faltarem.
  - Usuários de seed (só dev): admin@loja.com/admin123, joao@email.com/123456, maria@email.com/senha123. Agora guardados como hash, mas são senhas fracas e conhecidas; troque-as fora de dev.
  - O login não emite token nem sessão. Por isso GET /usuarios/<id> e GET /pedidos/usuario/<id> continuam públicos (sem como verificar o dono do dado). Recomenda-se sessão/JWT com checagem de propriedade.
  - O /admin/query foi mantido para preservar o contrato, mas recomenda-se removê-lo. Mesmo restrito a admin + SELECT read-only, ele permite ler os hashes de senha.
  - `itens_pedido.produto_id` ficou sem FK de propósito, para manter o comportamento original: deletar produto preserva o histórico do pedido e mostra "Desconhecido".
  - Um `loja.db` antigo não é migrado (CREATE TABLE IF NOT EXISTS não aplica as novas constraints) → apague e recrie com o seed. Senhas em texto puro de um banco antigo são aceitas uma vez e regravadas com hash no próximo login.
  - Cancelar um pedido ainda não devolve estoque. A regra existia no original só como mensagem e foi mantida apenas como notificação (log), para não mudar comportamento sem decisão de negócio.
  - O CORS agora só aceita as origens de CORS_ORIGINS. Clientes de outras origens precisam ser adicionados por env.
  - Nomes de campos e parâmetros do contrato (`<int:id>`, chaves em português, "Usuario ID") foram mantidos como estavam.
================================
