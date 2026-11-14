================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
Estratégia: **já em camadas → só correções pontuais** (`mvc-guidelines.md` §5.3). Nenhum arquivo
foi movido ou renomeado; 2 arquivos novos (marcados `[novo]`) e 11 alterados (`[alt]`).

```
ecommerce-api-legacy/
├── package.json                      ("start": "node src/app.js" — inalterado)
├── .env.example                      [alt] sem valores de segredo; + SEED_USER_PASSWORD
├── README.md                         [alt] autenticação, segredos gerados, contrato do checkout
├── api.http                           [alt] @adminToken virou placeholder
└── src/
    ├── app.js                        [alt] initSchema(db,{config,logger}), aviso do token gerado, shutdown SIGTERM/SIGINT
    ├── app.factory.js                [alt] + notFound() entre as rotas e o error handler
    ├── config/
    │   └── index.js                  [alt] sem fallback literal; token aleatório por boot; seedUserPassword
    ├── db/
    │   ├── connection.js             [alt] + write() (escrita avulsa na mesma fila) + invariante documentada
    │   └── schema.js                 [alt] senha do seed vem do env ou é gerada e logada
    ├── models/
    │   ├── auditLog.model.js
    │   ├── constants.js
    │   ├── course.model.js
    │   ├── enrollment.model.js
    │   ├── payment.model.js
    │   └── user.model.js             [alt] deleteById usa db.write
    ├── services/
    │   ├── checkout.service.js
    │   ├── financialReport.service.js
    │   └── paymentGateway.service.js
    ├── controllers/
    │   ├── admin.controller.js
    │   ├── checkout.controller.js
    │   └── user.controller.js        [alt] valida :id; mensagem do DELETE corrigida
    ├── routes/
    │   ├── admin.routes.js           [alt] + router.all → 405 (Allow: GET)
    │   ├── checkout.routes.js        [alt] + router.all → 405 (Allow: POST)
    │   └── user.routes.js            [alt] + router.all → 405 (Allow: DELETE)
    ├── middlewares/
    │   ├── asyncHandler.js
    │   ├── auth.js
    │   ├── errorHandler.js           [alt] envia header Allow em 405
    │   └── notFound.js               [novo] catch-all 404 + helper 405 (OPTIONS passa adiante)
    ├── errors/
    │   └── AppError.js               [alt] + MethodNotAllowedError (405, com allowed[])
    ├── validators/
    │   ├── checkout.validator.js
    │   └── user.validator.js         [novo] validateUserId (inteiro ≥ 1)
    └── utils/
        ├── logger.js
        └── password.js
```

## Changes Applied
  [AP-01] `DEV_ADMIN_TOKEN = 'dev-admin-token'` removido: sem `ADMIN_TOKEN` no ambiente e fora de produção, um token de 24 bytes é sorteado por boot e registrado em `warn`; em `APP_ENV=production` o boot falha sem a variável. Senha de seed `'123'` removida: vem de `SEED_USER_PASSWORD` ou é gerada e logada uma vez; em produção o seed recusa rodar sem ela. Valor literal apagado também de `README.md`, `api.http` e `.env.example` → src/config/index.js, src/db/schema.js, src/app.js, .env.example, README.md, api.http
  [AP-10] `db.write(sql, params)` adicionado em `createDb` (= `withTransaction(() => run(...))`): escrita avulsa entra na mesma fila e não pode mais ser capturada pelo `BEGIN/ROLLBACK` de outra requisição. `userModel.deleteById` passou a usá-lo; invariante documentada no topo de `connection.js` → src/db/connection.js, src/models/user.model.js
  [AP-12] Catch-all `notFound()` registrado depois dos routers e antes do error handler; `router.all(PATH, methodNotAllowed([...]))` em cada arquivo de rota devolve 405 com header `Allow`; `MethodNotAllowedError` criado. `methodNotAllowed` deixa `OPTIONS` passar adiante para não transformar o preflight que o Router do Express responde sozinho (200 + `Allow`) num 405 → src/middlewares/notFound.js, src/app.factory.js, src/routes/*.js, src/errors/AppError.js, src/middlewares/errorHandler.js
  [AP-14] `validateUserId` exige `^\d+$` e inteiro seguro ≥ 1; `abc`, `0`, `1 OR 1=1` passaram de 200 falso para 400. Id bem formado inexistente continua 200 (preservação do baseline) → src/validators/user.validator.js, src/controllers/user.controller.js
  [AP-26] Mensagem do DELETE: `'Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.'` → `'Usuário deletado, junto com suas matrículas e pagamentos.'` (status 200 e tipo texto preservados) → src/controllers/user.controller.js
  [AP-21] (parcial) Campos `usr`/`eml`/`pwd`/`c_id`/`card` **não** renomeados (contrato HTTP); documentados numa tabela no README em vez disso → README.md
  [AP-23] `close` passou a ser consumido num shutdown gracioso (`SIGTERM`/`SIGINT` → `server.close` → `db.close`); `ADMIN_TOKEN_HEADER` passou a ser consumido em `src/app.js` ao logar o token gerado. A coluna `users.pass` e os helpers de senha foram mantidos (decisão de produto — ver Remaining Known Issues) → src/app.js

## Validation
  ✓ Application boots without errors (`ADMIN_TOKEN=dev-admin-token SEED_USER_PASSWORD=123 PORT=3101 npm start`, porta 3101 — log só com a linha info de boot, sem traceback)
  ✓ All baseline endpoints respond (19/19 do `baseline.md` com o mesmo status; shape igual em 15, `≈` em 4 por correção intencional — ver tabela)
  ✓ Original start command still works (`npm start` → `node src/app.js`; porta via `PORT` porque 3000 está ocupada por Docker nesta máquina; default continua 3000)
  ✓ Seed / initial data loads (relatório inicial idêntico ao baseline #1: Clean Architecture 997 [Leonan 997], Docker 0 [])
  ✓ Segredos gerados quando ausentes (boot em 3102 sem `ADMIN_TOKEN`/`SEED_USER_PASSWORD`: token de 32 chars e senha de 24 chars logados; o token sorteado respondeu 200 e o antigo literal `dev-admin-token` respondeu 401)
  ✓ Guardas de produção (`APP_ENV=production` sem segredos → `Falha no boot: Configuração obrigatória ausente em produção: ADMIN_TOKEN, PAYMENT_GATEWAY_KEY`; com eles mas sem `SEED_USER_PASSWORD` → `SEED_USER_PASSWORD é obrigatório em produção...`; com os três → sobe e responde 200)
  ✓ Correção do AP-10 verificada (mesmo script da auditoria, agora com `db.write`: o `DELETE` respondeu `changes=1` e **persistiu** após o `ROLLBACK` da transação concorrente — antes era desfeito)
  ✓ 404/405 no formato da API (`GET /api/unknown` → 404 `Rota não encontrada: GET /api/unknown`; `GET/PUT/PATCH/DELETE /api/checkout` → 405 `Allow: POST`; `PUT /api/users/1` → 405 `Allow: DELETE`; `POST /api/admin/financial-report` → 405 `Allow: GET`)
  ✓ OPTIONS e HEAD preservados (porta 3105: `OPTIONS /api/checkout` → 200 `Allow: POST`, `OPTIONS /api/users/1` → 200 `Allow: DELETE`, `OPTIONS /api/admin/financial-report` → 200 `Allow: GET,HEAD`, `OPTIONS /api/unknown` → 404 do catch-all; `HEAD /api/admin/financial-report` → 200). Uma primeira versão do `methodNotAllowed` devolvia 405 para OPTIONS — detectado nesta validação e corrigido antes de concluir.
  ✓ No CRITICAL/HIGH/MEDIUM catalog signals remaining (re-grep: `dev-admin-token` ausente em `src/`, README, api.http, .env.example e package.json; `DEV_ADMIN_TOKEN` removido; nenhuma senha literal em `src/db/`,`src/config/`; `db.write` no único write avulso; `notFound()` + 3 `methodNotAllowed`; `validateUserId` consumido; nenhuma string de resposta contraditória)
  ✓ Shutdown gracioso (`kill -TERM` → `{"msg":"Encerrando","signal":"SIGTERM"}` e processo encerrado; `db.close()` chamado)
  ✓ Syntax check de todos os 29 arquivos (`node --check`) sem erro
  ✓ Sem módulos órfãos ou imports para arquivos removidos (`grep -rnE "AppManager|require\('\./utils'\)"` vazio; todo arquivo de `src/` é alcançável a partir de `src/app.js`)
  ✓ .env.example atualizado (sem valores de segredo reais; `SEED_USER_PASSWORD` documentada)
  ✓ Servidores parados (`lsof -nP -iTCP:3101|3102|3103 -sTCP:LISTEN` vazios)

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | /api/admin/financial-report (#1) | 200 com token | 200 com token | = | mesmos valores |
| GET | /api/admin/financial-report (#1b) | 401 sem token | 401 sem token | = | |
| GET | /api/admin/financial-report (#1c) | 401 token errado | 401 token errado | = | |
| POST | /api/checkout `{"usr":"X"}` (#2) | 400 | 400 | = | `Bad Request` |
| POST | /api/checkout c_id 999 (#3) | 404 | 404 | = | `Curso não encontrado` |
| POST | /api/checkout cartão 5111… (#4) | 400 | 400 | = | `Pagamento recusado`; João não é criado |
| POST | /api/checkout Guilherme (#5) | 200 | 200 | = | `{"msg":"Sucesso","enrollment_id":2}` |
| POST | /api/checkout Leonan sem pwd (#6) | 200 | 200 | = | `{"msg":"Sucesso","enrollment_id":3}` |
| GET | /api/admin/financial-report (#7) | 200 | 200 | = | valores idênticos (997 / 994) |
| DELETE | /api/users/999 (#8b) | 401 sem token | 401 sem token | = | |
| DELETE | /api/users/999 (#8) | 200 com token | 200 com token | ≈ | texto da mensagem corrigido (fix AP-26); id inexistente segue 200 |
| DELETE | /api/users/1 (#9) | 200 com token | 200 com token | ≈ | texto da mensagem corrigido (fix AP-26); cascata inalterada |
| GET | /api/admin/financial-report (#10) | 200 | 200 | = | Clean Architecture 0 []; Docker 497 [Guilherme] |
| GET | /api/unknown (#11) | 404 text/html (página HTML do Express) | 404 `Rota não encontrada: GET /api/unknown` | ≈ | catch-all no handler central (fix AP-12) |
| GET | /__rota-inexistente__ (#11b) | 404 text/html (página HTML) | 404 `Rota não encontrada: GET /__rota-inexistente__` | ≈ | idem |
| GET | /api/checkout (#11c, método errado) | 404 text/html (página HTML) | 405 `Método não permitido…` + `Allow: POST` | ≈ | 405 correto em vez de 404 HTML (fix AP-12) |
| POST | /api/checkout JSON malformado (#12) | 400 `Bad Request` | 400 `Bad Request` | = | |
| POST | /api/checkout `card` numérico (#13) | 400 `Bad Request` | 400 `Bad Request` | = | |
| GET | /api/admin/financial-report (#14) | 200 | 200 | = | servidor vivo após #12/#13 |
| DELETE | /api/users/abc (novo caso) | 200 (sucesso falso) | 400 `Bad Request` | ≈ | validação de `:id` (fix AP-14) |
| DELETE | /api/users/0 (novo caso) | 200 (sucesso falso) | 400 `Bad Request` | ≈ | idem |
| DELETE | /api/users/1%20OR%201=1 (novo caso) | 200 (sucesso falso) | 400 `Bad Request` | ≈ | idem; nunca houve injection (query parametrizada) |
| PUT | /api/users/1 (novo caso) | 404 text/html | 405 + `Allow: DELETE` | ≈ | fix AP-12 |
| POST | /api/admin/financial-report (novo caso) | 404 text/html | 405 + `Allow: GET` | ≈ | fix AP-12 |
| OPTIONS | /api/checkout (novo caso) | 200 + `Allow: POST` | 200 + `Allow: POST` | = | preflight do Router preservado |
| OPTIONS | /api/admin/financial-report (novo caso) | 200 + `Allow: GET,HEAD` | 200 + `Allow: GET,HEAD` | = | idem |
| HEAD | /api/admin/financial-report (novo caso) | 200 | 200 | = | casa no handler GET antes do `router.all` |

## Como obter credenciais (para o próximo validador)
- **Token de admin** — header `X-Admin-Token`. Não existe mais valor default no código. Duas opções:
  1. definir você mesmo: `ADMIN_TOKEN=<valor> npm start` e enviar `-H 'X-Admin-Token: <valor>'`;
  2. não definir: o app sorteia um token por boot e o registra em `warn` (`{"msg":"ADMIN_TOKEN não definido; token gerado para esta execução","header":"X-Admin-Token","adminToken":"..."}`) — leia do log.
- **Token de login** — não se aplica: o projeto não tem rota de login nem emissão de token.
- **Variáveis que o validador deve exportar** para reproduzir o baseline com os mesmos dados:
  `ADMIN_TOKEN=dev-admin-token` e `SEED_USER_PASSWORD=123` (valores de dev usados na validação desta
  iteração; o seed grava a senha com hash scrypt). Sem elas o app funciona, mas o token e a senha
  mudam a cada boot e precisam ser lidos do log.
- Observação: o `.env.example` **não** traz esses dois valores — só placeholders
  (`troque-este-valor-apenas-desenvolvimento`). Isso é deliberado: o finding AP-01 citava
  `.env.example:11` como uma das cópias do token literal, então repetir o valor lá reintroduziria o
  problema. Os valores de dev ficam registrados aqui, neste resumo, que é documentação de
  refatoração e não arquivo de exemplo de configuração.
- Em `APP_ENV=production`: `ADMIN_TOKEN` e `PAYMENT_GATEWAY_KEY` são obrigatórios no boot e
  `SEED_USER_PASSWORD` é obrigatória para o seed.

## Remaining Known Issues
  - `DELETE /api/users/:id` com id **bem formado mas inexistente** (ex.: 999) continua respondendo 200 com a mensagem de sucesso. Preservação deliberada do baseline; o correto seria 404 usando `changes` do resultado. Mudança de contrato — fazer numa versão nova da API.
  - Campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) mantidos (AP-21 parcial): renomear quebra clientes. Documentados em tabela no README; aliases legíveis exigem versionar a API.
  - A coluna `users.pass` continua **write-only**: é gravada com scrypt+salt mas nenhuma rota lê ou verifica senha, porque não há login. `hashPassword`/`randomPassword` seguem sem consumidor de verificação. Mantido por ser decisão de produto (login planejado?) — se não houver login no roadmap, remover coluna e helpers.
  - Mensagem do DELETE foi alterada (`...ficaram sujos no banco.` → `...junto com suas matrículas e pagamentos.`). É mudança no corpo da resposta: clientes que casam a string exata precisam ser avisados.
  - Respostas de erro continuam em texto puro com `Content-Type: text/html` (default do `res.send` de string), inclusive os novos 404/405. Padronizar para `text/plain` ou JSON mudaria o contrato de **todas** as respostas de erro do baseline — não feito de propósito.
  - 500 inesperado responde `Erro interno do servidor` (sem stack trace), em vez das mensagens específicas do código original.
  - `HOST` default é `127.0.0.1`; deploys em container precisam de `HOST=0.0.0.0` explícito.
  - Gateway de pagamento é simulado (prefixo `4` aprova). `PAYMENT_GATEWAY_KEY` é injetada mas só alimenta o campo de log `gatewayConfigured` — não há integração real.
  - Não há testes automatizados (nenhum `.test.js`/`.spec.js`; `package.json` só tem o script `start`). A validação desta iteração foi por curl contra o `baseline.md` mais dois scripts ad-hoc de corrida de transação, em `scratchpad` (não versionados). Converter esses scripts em testes é o próximo passo de maior retorno.
  - Banco `:memory:` por default: o schema com FKs é recriado a cada boot. Um `DB_PATH` em arquivo criado com schema antigo exigiria migração — `CREATE TABLE IF NOT EXISTS` não altera tabela existente. Não há ferramenta de migração no projeto.
  - `enrollments.course_id` referencia `courses(id)` sem `ON DELETE` (restrição deliberada: impede apagar curso com matrículas). Não há rota de deleção de curso hoje; se houver, decidir entre `RESTRICT` explícito e desativação lógica (`active = 0`).
  - O 405 é declarado por path em cada arquivo de rota (`router.all(PATH, methodNotAllowed([...]))`). Rota nova sem essa linha volta a cair no 404 do catch-all em vez de 405 — convenção que depende de disciplina, não verificada automaticamente.
================================
