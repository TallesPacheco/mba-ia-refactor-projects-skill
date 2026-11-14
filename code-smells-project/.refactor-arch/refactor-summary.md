================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
code-smells-project/
├── app.py (composition root: create_app(config) — sem instância em nível de módulo)
├── config/
│   ├── __init__.py
│   └── settings.py            (Config por instância; modo estrito fora de development/test)
├── db/
│   ├── __init__.py
│   ├── connection.py          (conexão por requisição em flask.g, PRAGMA foreign_keys, conexão read-only p/ admin)
│   └── schema.py              (CREATE TABLE + índices + seed com senhas vindas do ambiente)
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
│   ├── auth.py                (issue_token / verify_token / require_auth / require_admin / exigir_dono_ou_admin)
│   └── error_handler.py
├── errors.py                  (+ ForbiddenError 403)
├── README.md                  (documenta credenciais, variáveis e seed)
├── requirements.txt           (inalterado: flask 3.1.1, flask-cors 5.0.1)
└── .env.example

Estrutura de pastas inalterada (projeto já estava em camadas — estratégia 5.3 do mvc-guidelines:
somente correções pontuais dos findings, nenhum arquivo movido). 40 arquivos .py, ~1251 linhas.

## Changes Applied
  [AP-01] Hashes e senhas de seed removidos do código: `SEED_USUARIOS` passou a guardar só (nome, e-mail, nome da variável de ambiente, tipo); `senha_de_seed()` lê `SEED_ADMIN_PASSWORD`/`SEED_JOAO_PASSWORD`/`SEED_MARIA_PASSWORD` e, sem elas, gera `secrets.token_urlsafe(12)` registrando a senha uma única vez no log (fora de development/test, recusa rodar). `Config.validate()` deixou de exigir a string exata `production`: qualquer `APP_ENV` fora de `development`/`test` agora rejeita `SECRET_KEY`/`ADMIN_TOKEN` vazios **ou iguais aos defaults públicos**, e rejeita `FLASK_DEBUG=1`. Boot com o token default emite WARNING → db/schema.py, config/settings.py, app.py, .env.example
  [AP-24] Login passou a emitir token assinado: `issue_token`/`verify_token` com `itsdangerous.URLSafeTimedSerializer` sobre `SECRET_KEY` (salt `auth-token`, validade `TOKEN_MAX_AGE`, default 3600s), decorator `require_auth` lendo `Authorization: Bearer <token>` ou o header de admin, e `exigir_dono_ou_admin()` para checagem de propriedade. Resposta do login ganhou a chave de topo `token` (shape de `dados` inalterado). Token forjado → 401 (validado) → middlewares/auth.py, views/usuario_routes.py, config/settings.py
  [AP-25] `GET /usuarios/<id>` e `GET /pedidos/usuario/<id>` passaram a exigir `require_auth` + dono ou admin: 401 sem credencial, 403 com token de outro usuário, 200 com o token do dono ou `X-Admin-Token` → views/usuario_routes.py, views/pedido_routes.py
  [AP-06] `POST /pedidos` passou a exigir `require_auth`; o `usuario_id` do corpo continua no contrato, mas precisa ser o do token (admin pode informar qualquer um) — a checagem é injetada pela rota como callback, mantendo o controller sem dependência do contexto Flask → views/pedido_routes.py, controllers/pedido_controller.py
  [AP-11] `app = create_app()` removido do nível de módulo: importar `app` não cria mais `loja.db` nem roda o seed (verificado com `python -c "import app"`). `flask --app app run` continua funcionando pela descoberta automática da factory; `python app.py` constrói o app dentro de `__main__`. `Config` virou instância que lê o ambiente em `create_app()`, não no import → app.py, config/settings.py
  [AP-14] Senha do cadastro passou a ter tamanho mínimo (6) e máximo (128) em `validar_cadastro`, com as constantes `SENHA_MIN`/`SENHA_MAX`; filtros de preço passaram de truthiness para `is not None`, e o validador devolve `None` para parâmetro ausente/vazio, de modo que `preco_min=0` vira filtro de verdade → validators/usuario_validator.py, validators/produto_validator.py, models/produto_model.py, models/constants.py
  [AP-19] (parcial) Índices `idx_pedidos_usuario_id` e `idx_itens_pedido_pedido_id` criados no schema; comentário do schema passou a registrar que a existência de `produto_id` é validada na escrita pelo service → db/schema.py
  [AP-21] Placeholders `<int:id>` renomeados para `<int:produto_id>` / `<int:usuario_id>` nos 4 handlers que sombreavam o builtin; as URLs públicas não mudaram → views/produto_routes.py, views/usuario_routes.py
  [AP-23] Ramo de autenticação por senha em texto puro removido: `_senha_confere` virou allowlist (só `scrypt:`/`pbkdf2:` autenticam; qualquer outro formato loga WARNING e falha). `usuario_model.atualizar_senha` e o import `hmac` do service, que só existiam para esse ramo, foram apagados → services/usuario_service.py, models/usuario_model.py
  [AP-26] `.env.example` deixou de instruir "copie para .env" (não há python-dotenv) e passou a documentar a exportação no shell e todas as 13 variáveis; README ganhou seções de configuração, autenticação (tabela de credenciais, lista de rotas por guard, exemplo com curl) e seed; 404 e 405 passaram a responder em português pelo handler central (`MENSAGENS_HTTP`), mantendo status e chave `erro` → .env.example, README.md, middlewares/error_handler.py

## Validation
  ✓ Application boots without errors (`SEED_*=... PORT=5301 .venv/bin/python app.py`; log `.refactor-arch/refactor-server.log` sem traceback, exception ou DeprecationWarning com `PYTHONWARNINGS=default` — `grep -ciE "traceback|exception|deprecationwarning"` → 0)
  ✓ All baseline endpoints respond (73/73 requisições executadas; todas as 66 linhas do baseline reproduzidas com o mesmo status e shape, exceto as marcadas ≈ abaixo — mudanças de segurança intencionais; nenhuma ≠)
  ✓ Original start command still works (`python app.py` → 127.0.0.1:5000 por padrão, `PORT`/`HOST` por env; `flask --app app run --port 5302` também validado após remover `app` de nível de módulo)
  ✓ Import sem efeito colateral (`rm -f loja.db && .venv/bin/python -c "import app"` → `loja.db` não é criado; `flask --app app routes` lista as 19 rotas)
  ✓ Seed / initial data loads (`loja.db` apagado antes de cada iteração; /health → produtos 10, usuarios 3; login dos 3 usuários de seed → 200 com `SEED_*` exportadas; sem as variáveis, o seed gera e loga senhas aleatórias — verificado)
  ✓ Autorização nova validada nos dois sentidos (401 sem credencial em `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`, `POST /pedidos`; 403 com token de outro usuário nas três rotas de dono — `GET /usuarios/1`, `GET /pedidos/usuario/1` e `POST /pedidos {"usuario_id":1}` com o token do João; 200/201 com o token do dono ou `X-Admin-Token`; token forjado `eyJzdWIiOiAxfQ.forjado` → 401)
  ✓ Caminho documentado no README executado literalmente (`export $(grep -v '^#' .env.example | xargs)` + `PORT=5303 python app.py` + os dois curls do README): login devolve `token`, `GET /usuarios/1` com `Authorization: Bearer` → 200 e `GET /usuarios` com `X-Admin-Token: dev-admin-token` → 200. Para isso `.env.example` passou a trazer os defaults reais de dev (`SECRET_KEY=dev-only-insecure-key`, `ADMIN_TOKEN=dev-admin-token`) em vez de placeholders que davam 401 — valores públicos, recusados por `validate()` fora de development/test
  ✓ Config estrita fora de dev (`APP_ENV=staging` → `RuntimeError: APP_ENV=staging exige valores próprios para: SECRET_KEY, ADMIN_TOKEN`; `APP_ENV=production` com segredos próprios → passa)
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep: nenhum hash/senha literal de seed, nenhum `app = create_app()` de módulo, nenhum `except` genérico ou `str(e)`, nenhum `print`, nenhum `debug=True`/`0.0.0.0`, nenhuma referência a `atualizar_senha`; emissor e verificador de token presentes; 9 rotas com `@require_admin` e 3 com `@require_auth`. As duas ocorrências restantes de `environ.get("SECRET_KEY", SECRET_KEY_DEV)` são os defaults de dev previstos pelo PB-01, agora rejeitados por `validate()` fora de development/test)
  ✓ Nenhum arquivo antigo importável com rotas duplicadas (estrutura já em camadas; nada removido além do código morto citado)
  ✓ .env.example atualizado com as 13 variáveis (inclui `TOKEN_MAX_AGE` e as três `SEED_*`)
  ✓ Servidores encerrados (`lsof` vazio em 5201, 5202, 5301 e 5302); `loja.db` apagado ao final

### Como reproduzir a validação
```bash
rm -f loja.db
export SEED_ADMIN_PASSWORD=admin123 SEED_JOAO_PASSWORD=123456 SEED_MARIA_PASSWORD=senha123
PORT=5301 .venv/bin/python app.py          # exporte as SEED_* ANTES do boot: o seed roda no boot
# token de usuário:
curl -s -X POST :5301/login -H 'Content-Type: application/json' -d '{"email":"joao@email.com","senha":"123456"}'  # → campo "token"
# rotas de dono:  -H "Authorization: Bearer <token>"
# rotas de admin: -H "X-Admin-Token: dev-admin-token"
```

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | / | 200 | 200 | = | |
| GET | /health | 200 | 200 | = | |
| GET | /produtos | 200 | 200 | = | 10 itens |
| GET | /produtos/1 | 200 | 200 | = | |
| GET | /produtos/999 | 404 | 404 | = | |
| GET | /produtos/busca?q=gamer | 200 | 200 | = | 3 itens |
| GET | /produtos/busca (categoria+faixa de preço) | 200 | 200 | = | 1 item |
| GET | /produtos/busca?q=' OR 1=1-- | 200 (vazio) | 200 (vazio) | = | injeção segue sem efeito |
| GET | /produtos/busca?preco_min=0&preco_max=100 | 200 (preco_min ignorado) | 200 | = | `0` agora é filtro de verdade (fix AP-14); mesmo resultado neste dataset |
| GET | /produtos/busca?preco_min=abc | 400 | 400 | = | |
| GET | /usuarios | 401 / 200 com `X-Admin-Token` | idem | = | |
| GET | /usuarios/\<id\> | 200 **sem auth** | 401 sem credencial / 403 token de outro / 200 com token do dono ou `X-Admin-Token` | ≈ | auth adicionada (fix AP-25) |
| GET | /usuarios/999 | 404 | 404 com credencial | ≈ | auth adicionada |
| GET | /pedidos | 401 / 200 com `X-Admin-Token` | idem | = | |
| GET | /pedidos/usuario/2 | 200 **sem auth** | 401 sem credencial / 200 com token do dono ou `X-Admin-Token` | ≈ | auth adicionada (fix AP-25) |
| GET | /relatorios/vendas | 401 / 200 com `X-Admin-Token` | idem | = | |
| POST | /login (válido) | 200 | 200 | ≈ | chave de topo `token` acrescentada (fix AP-24); `dados` inalterado |
| POST | /login (senha errada) | 401 | 401 | = | |
| POST | /login (e-mail com `' --`) | 401 | 401 | = | |
| POST | /login {} / sem body | 400 | 400 | = | |
| POST | /produtos | 401 / 201 com `X-Admin-Token` | idem | = | id 11 |
| POST | /produtos (payload inválido: sem preço, categoria, preço negativo) | 400 | 400 | = | |
| POST | /produtos nome "O'Reilly" | 201 | 201 | = | id 12 |
| POST | /usuarios (válido) | 201 | 201 | = | id 4 |
| POST | /usuarios (e-mail duplicado) | 409 | 409 | = | |
| POST | /usuarios {"nome":"Teste"} | 400 | 400 | = | |
| POST | /usuarios senha "abc" | (não exercitada no baseline) | 400 | — | `{"erro":"Senha deve ter pelo menos 6 caracteres"}` (fix AP-14). O baseline só usou `"abc123"` (6 caracteres), reexecutado aqui → 201: nenhum payload que o baseline aceitava passou a ser rejeitado |
| GET | /pedidos/usuario/1 com token de outro usuário | (não exercitada no baseline) | 403 | — | `{"erro":"Acesso negado"}`; completa as três vias do guard desta rota (401 / 403 / 200) |
| POST | /pedidos (válido) | 201 **sem auth** | 401 sem credencial / 201 com `Authorization: Bearer` do dono | ≈ | auth adicionada (fix AP-06); pedido_id 1, total 6179.79 |
| POST | /pedidos usuario_id de outro | 201 | 403 `{"erro":"Acesso negado"}` | ≈ | personificação bloqueada (fix AP-06) |
| POST | /pedidos produto 999 / estoque insuficiente / itens [] | 400 | 400 com credencial | ≈ | auth adicionada |
| POST | /pedidos usuario_id 999 (admin) | 400 | 400 | = | |
| GET | /produtos/1 após pedido | 200 estoque 9 | 200 estoque 9 | = | baixa de estoque preservada |
| PUT | /produtos/11 | 401 / 200 com `X-Admin-Token` | idem | = | |
| PUT | /produtos/999 | 404 | 404 | = | |
| PUT | /produtos/11 inválido (sem preço, categoria inválida) | 400 | 400 | = | |
| PUT | /pedidos/1/status | 401 / 200 com `X-Admin-Token` | idem | = | |
| PUT | /pedidos/1/status "foo" | 400 | 400 | = | |
| PUT | /pedidos/999/status | 404 | 404 | = | |
| DELETE | /produtos/\<id\> | 401 / 200 com `X-Admin-Token` | idem | = | |
| DELETE | /produtos/999 e repetido | 404 | 404 | = | |
| POST | /admin/query SELECT (inclusive coluna `senha`) | 401 / 200 com `X-Admin-Token` | idem | = | mantido como estava; segue retornando os hashes (ver Remaining) |
| POST | /admin/query {} / "SELEC x" / não-SELECT | 400 | 400 | = | |
| POST | /admin/reset-db | 401 / 200 com `X-Admin-Token` | idem | = | counts zerados depois |
| GET | /__rota-inexistente__ | 404 JSON em inglês | 404 JSON `{"erro":"Rota não encontrada"}` | ≈ | mensagem traduzida (fix AP-26); status e chave iguais |
| DELETE | /produtos (método não permitido) | 405 JSON em inglês | 405 JSON `{"erro":"Método não permitido para esta rota"}` | ≈ | mensagem traduzida (fix AP-26) |

## Remaining Known Issues
  - **Credenciais para validar:** rotas de admin usam o header `X-Admin-Token` (valor de dev `dev-admin-token`, variável `ADMIN_TOKEN`). Rotas de dono usam `Authorization: Bearer <token>`, com o token vindo do campo `token` da resposta de `POST /login`. O token expira em `TOKEN_MAX_AGE` (default 3600s).
  - **Variáveis que o validador precisa exportar antes do seed e do boot:** `SEED_ADMIN_PASSWORD=admin123`, `SEED_JOAO_PASSWORD=123456`, `SEED_MARIA_PASSWORD=senha123`. O seed roda no boot; sem elas, as senhas são aleatórias (impressas uma vez no log) e os logins do baseline falham.
  - Senhas de dev do seed continuam fracas por serem as do baseline. Fora de development/test o seed exige as variáveis explicitamente, mas a força da senha não é verificada no seed (só no cadastro pela API).
  - O token de login é determinístico dentro do mesmo segundo para o mesmo usuário (granularidade de timestamp do `URLSafeTimedSerializer`). Ele é assinado e expira, mas não é um identificador único de sessão e não há revogação/logout. Para isso seria preciso uma tabela de sessões ou um `jti`.
  - **A coluna `usuarios.tipo` não é consultada para autorização em nenhum ponto.** Privilégio administrativo vem exclusivamente do `X-Admin-Token` compartilhado, então um usuário com `tipo="admin"` não tem acesso elevado pelo próprio token de login. É a mesma decisão da iteração 1 e preserva o contrato, mas o caminho natural é fazer `require_admin` aceitar também um token de usuário cujo `tipo` seja `admin`.
  - **Não há limite de tentativas em `POST /login`.** Adicionar throttling exigiria estado compartilhado entre requisições (contrário à regra de "nenhum estado mutável de módulo") ou uma dependência nova; recomenda-se rate limiting na borda (proxy/WAF) ou `Flask-Limiter` com backend externo.
  - `POST /admin/query` **não foi alterado**: continua executando um `SELECT` arbitrário em conexão read-only atrás do token de admin e devolvendo os hashes de senha. Preservar o contrato (baseline #54 → 200 com a coluna `senha`) e remover o endpoint são objetivos conflitantes; a recomendação segue sendo removê-lo ou trocá-lo por uma allowlist de consultas nomeadas, como decisão de produto.
  - `admin_model.resetar` **não foi simplificado**: os quatro `DELETE` explícitos são redundantes com `ON DELETE CASCADE`, mas são corretos e independentes do `PRAGMA foreign_keys`. Numa operação destrutiva, a redundância foi mantida de propósito.
  - `itens_pedido.produto_id` segue sem FK, por decisão da iteração anterior (o histórico do pedido sobrevive à deleção do produto e mostra "Desconhecido"). A existência do produto é validada na escrita pelo service; o schema agora registra isso no comentário.
  - Um `loja.db` anterior a esta iteração **não autentica mais**: o ramo que aceitava senha em texto puro foi removido. Apague o arquivo e deixe o boot recriar schema + seed. Bancos criados pela iteração 1 continuam válidos (hashes scrypt).
  - Cancelar um pedido ainda não devolve estoque — comportamento do baseline original, mantido; nenhuma mensagem afirma o contrário (a notificação só registra o cancelamento no log).
  - O CORS aceita apenas as origens de `CORS_ORIGINS`; clientes de outras origens precisam ser adicionados por env.
  - Nomes de campos e query params do contrato (chaves em português, `"Usuario ID"` nas mensagens de erro) foram mantidos como estavam.
  - Não há testes automatizados. A factory agora permite `create_app(TestConfig)` com `DATABASE_PATH` próprio — é o próximo passo natural.
================================
