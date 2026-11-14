================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
ecommerce-api-legacy/
├── package.json                      ("start": "node src/app.js" — inalterado)
├── .env.example
├── README.md / api.http              (documentam o header X-Admin-Token)
└── src/
    ├── app.js                        (entry point: config → db + schema/seed → createApp → listen)
    ├── app.factory.js                (composition root: DI de models/services/controllers/rotas/middlewares)
    ├── config/
    │   └── index.js                  (process.env + defaults de dev, Object.freeze, assertConfig p/ produção)
    ├── db/
    │   ├── connection.js             (wrapper Promise run/get/all/exec + withTransaction serializado)
    │   └── schema.js                 (CREATE TABLE IF NOT EXISTS com FK/UNIQUE/NOT NULL + seed idempotente)
    ├── models/
    │   ├── auditLog.model.js
    │   ├── constants.js              (PaymentStatus, APPROVED_CARD_PREFIX, UNKNOWN_STUDENT)
    │   ├── course.model.js           (findActiveById, listFinancialRows — 1 query com JOIN)
    │   ├── enrollment.model.js
    │   ├── payment.model.js
    │   └── user.model.js
    ├── services/
    │   ├── checkout.service.js       (curso → pagamento → transação usuário+matrícula+pagamento+auditoria)
    │   ├── financialReport.service.js
    │   └── paymentGateway.service.js (gateway simulado, chave injetada, loga só os 4 últimos dígitos)
    ├── controllers/
    │   ├── admin.controller.js
    │   ├── checkout.controller.js
    │   └── user.controller.js
    ├── routes/
    │   ├── admin.routes.js           (GET /api/admin/financial-report + requireAdmin)
    │   ├── checkout.routes.js        (POST /api/checkout)
    │   └── user.routes.js            (DELETE /api/users/:id + requireAdmin)
    ├── middlewares/
    │   ├── asyncHandler.js
    │   ├── auth.js                   (X-Admin-Token, timingSafeEqual)
    │   └── errorHandler.js           (registrado por último; texto puro, sem stack trace)
    ├── errors/
    │   └── AppError.js               (ValidationError, UnauthorizedError, NotFoundError, PaymentDeniedError)
    ├── validators/
    │   └── checkout.validator.js
    └── utils/
        ├── logger.js                 (JSON por linha, com níveis)
        └── password.js               (scrypt + salt aleatório)

## Changes Applied
  [AP-01] Segredos removidos do código; config via env (PORT, HOST, DB_PATH, ADMIN_TOKEN, PAYMENT_GATEWAY_KEY, LOG_LEVEL, APP_ENV) sem defaults reais; produção falha no boot sem ADMIN_TOKEN/PAYMENT_GATEWAY_KEY; seed grava senha com hash → src/config/index.js, src/db/schema.js, .env.example
  [AP-03] AppManager.js e utils.js apagados; split em config/db/models/services/controllers/routes/middlewares → src/**
  [AP-04] Log de PAN + chave do gateway substituído por log com cardLast4 e flag gatewayConfigured → src/services/paymentGateway.service.js
  [AP-05] badCrypto substituído por scrypt com salt aleatório; default "123456" substituído por senha aleatória; seed '123' com hash → src/utils/password.js, src/services/checkout.service.js, src/db/schema.js
  [AP-06] GET /api/admin/financial-report e DELETE /api/users/:id exigem header X-Admin-Token (401 sem/errado) → src/middlewares/auth.js, src/routes/admin.routes.js, src/routes/user.routes.js
  [AP-07] Porta/host via env (PORT default 3000, HOST default 127.0.0.1) → src/config/index.js, src/app.js
  [AP-08] Regra de checkout movida para CheckoutService + PaymentGateway; rotas só fazem parse/serialização → src/services/*, src/controllers/*, src/routes/*
  [AP-09] globalCache removido; conexão criada no entry point e injetada via createApp → src/app.js, src/app.factory.js
  [AP-10] Pagamento decidido antes de escrever; usuário+matrícula+pagamento+auditoria em BEGIN/COMMIT/ROLLBACK (rollback verificado com falha simulada: 0 linhas parciais) → src/db/connection.js, src/services/checkout.service.js
  [AP-11] App factory createApp({ db, config, logger }); listen só após schema+seed concluírem → src/app.factory.js, src/app.js
  [AP-12] Error handler central (texto puro, sem stack trace), asyncHandler, todos os erros de banco propagados como Promise rejeitada → src/middlewares/errorHandler.js, src/middlewares/asyncHandler.js
  [AP-13] Relatório financeiro com 1 query (LEFT JOINs, ORDER BY c.id, e.id) + agrupamento com Map → src/models/course.model.js, src/services/financialReport.service.js
  [AP-14] Validação de tipos do checkout (usr/eml/card string não vazia, c_id número/string, pwd string opcional); card numérico → 400 em vez de derrubar o processo → src/validators/checkout.validator.js
  [AP-16] Callbacks aninhados, self = this e contadores manuais eliminados (async/await) → src/services/*, src/models/*
  [AP-17] API de callback do sqlite3 encapsulada num único adaptador Promise (5 chamadas raw.* em db/connection.js) → src/db/connection.js
  [AP-19] FKs com ON DELETE CASCADE, UNIQUE(users.email), UNIQUE(payments.enrollment_id), NOT NULL, PRAGMA foreign_keys = ON → src/db/schema.js
  [AP-20] Constantes PaymentStatus, APPROVED_CARD_PREFIX, UNKNOWN_STUDENT; números do badCrypto eliminados junto com a função → src/models/constants.js
  [AP-21] Variáveis internas renomeadas (name, email, password, courseId, cardNumber); campos do contrato (usr, eml, pwd, c_id, card) mantidos → src/validators/checkout.validator.js
  [AP-22] console.log substituído por logger com níveis → src/utils/logger.js
  [AP-23] totalRevenue, dbUser, dbPass, smtpUser, logAndCache e globalCache removidos (re-grep sem ocorrência)

## Validation
  ✓ Application boots without errors (`PORT=3102 npm start`, porta 3102 — log só com linha info de boot, sem traceback)
  ✓ All baseline endpoints respond (13/13 com mesmo status; shape igual em 10, ≈ em 3 por correção intencional — ver tabela)
  ✓ Original start command still works (`npm start` → `node src/app.js`; porta via PORT porque 3000 está ocupada por Docker nesta máquina; default continua 3000)
  ✓ Seed / initial data loads (relatório inicial idêntico ao baseline #1; senha do seed gravada como `scrypt$...`)
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep: pk_live_/dbPass/smtpUser, console.log, badCrypto/base64, globalCache/totalRevenue, process.env presente (7), requireAdmin nas 2 rotas, BEGIN/COMMIT/ROLLBACK presentes, listen com host)
  ✓ Old monolith/duplicate files removed (src/AppManager.js e src/utils.js apagados; `grep -rnE "AppManager|\./utils['\"]\)" src package.json` vazio)
  ✓ .env.example created
  ✓ Auth validada com e sem credencial (401 sem header, 401 com token errado, 200 com `X-Admin-Token: dev-admin-token`)
  ✓ Servidores parados (`lsof -nP -iTCP:3102 -sTCP:LISTEN` vazio; PIDs npm e node finalizados)

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | /api/admin/financial-report (#1) | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06); mesmos valores; ordem dos cursos agora determinística (por id) |
| POST | /api/checkout `{"usr":"X"}` (#2) | 400 | 400 | = | `Bad Request` |
| POST | /api/checkout c_id 999 (#3) | 404 | 404 | = | `Curso não encontrado` |
| POST | /api/checkout cartão ****REDACTED****… (#4) | 400 | 400 | = | `Pagamento recusado`; usuário João não é mais criado (fix AP-10) |
| POST | /api/checkout Guilherme (#5) | 200 | 200 | = | `{"msg":"Sucesso","enrollment_id":2}`; user id interno passa de 3 para 2 (não exposto) |
| POST | /api/checkout Leonan existente, sem pwd (#6) | 200 | 200 | = | `{"msg":"Sucesso","enrollment_id":3}` |
| GET | /api/admin/financial-report (#7) | 200 | 200 com token | = | valores idênticos (997 / 994) |
| DELETE | /api/users/999 (#8) | 200 | 401 sem token / 200 com token | = | mesma mensagem; inexistente continua 200 (preservado) |
| DELETE | /api/users/1 (#9) | 200 | 401 sem token / 200 com token | = | mesma mensagem; matrículas/pagamentos removidos em cascata |
| GET | /api/admin/financial-report (#10) | 200 | 200 com token | ≈ | sem entradas órfãs `"Unknown"`: Clean Architecture revenue 0, students []; Docker 497 [Guilherme] (fix AP-19) |
| GET | /api/unknown (#11) | 404 | 404 | = | 404 padrão do Express |
| POST | /api/checkout JSON malformado (#12) | 400 (HTML + stack trace) | 400 `Bad Request` | ≈ | stack trace removido (fix AP-12) |
| POST | /api/checkout `card` numérico (#13) | processo derruba | 400 `Bad Request` | ≈ | servidor continua no ar (fix AP-14) |

## Remaining Known Issues
  - Token de admin: header `X-Admin-Token`; valor vem de `ADMIN_TOKEN` (default de dev `dev-admin-token`; em `APP_ENV=production` é obrigatório e o default é rejeitado). Clientes das rotas admin precisam enviar o header.
  - A mensagem do DELETE ("...matrículas e pagamentos ficaram sujos no banco.") foi preservada por contrato, mas não descreve mais o comportamento (agora há cascata). Sugere-se alterá-la numa versão nova da API.
  - `DELETE /api/users/:id` com id inexistente continua 200 (preservação do baseline); considerar 404 numa versão nova.
  - HOST default passou a ser 127.0.0.1 (antes escutava em todas as interfaces). Deploys em container precisam de `HOST=0.0.0.0` explícito.
  - Campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`) mantidos; renomear exige versionar a API.
  - Erros continuam em texto puro (formato original); 500 inesperado agora responde `Erro interno do servidor` em vez das mensagens específicas ("Erro DB", "Erro Matrícula"...).
  - Gateway de pagamento é simulado (prefixo "4" aprova); `PAYMENT_GATEWAY_KEY` só é injetada, não usada numa integração real.
  - Não há testes automatizados no projeto. A validação foi feita com curl contra o baseline e um teste ad-hoc de rollback.
  - Banco `:memory:`: o schema com FKs é criado a cada boot. Um `DB_PATH` em arquivo criado com o schema antigo exigiria migração (o `CREATE TABLE IF NOT EXISTS` não altera tabelas existentes).
================================
