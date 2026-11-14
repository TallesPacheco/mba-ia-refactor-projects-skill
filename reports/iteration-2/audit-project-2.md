================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v24.19.0) + Express 4.22.1
Files:   27 analyzed | ~564 lines of code

## Summary
CRITICAL: 1 | HIGH: 1 | MEDIUM: 3 | LOW: 2

## Findings

### [CRITICAL] Credenciais / segredos hardcoded (AP-01)
File: src/config/index.js:1, 10, 18
File: src/db/schema.js:36, 46
Description: duas credenciais literais permanecem no código. (a) `const DEV_ADMIN_TOKEN = 'dev-admin-token'` (`src/config/index.js:1`) é usado como fallback na leitura do ambiente: `adminToken: process.env.ADMIN_TOKEN || (appEnv === 'production' ? '' : DEV_ADMIN_TOKEN)` (`:10`). O catálogo classifica fallback literal em leitura de env como AP-01 mesmo quando guardado. O valor ainda está replicado em `README.md:20`, `api.http:2` e `.env.example:11`. (b) `const SEED_USER = { ..., password: '123' }` (`src/db/schema.js:36`), consumido por `hashPassword(SEED_USER.password)` (`:46`) — senha literal de conta inicial, que PB-25 proíbe.
Impact: `APP_ENV` default é `'development'` (`src/config/index.js:3`), e `assertConfig` só rejeita o token de dev quando `appEnv === 'production'` (`:16-18`). Qualquer deploy que esqueça `APP_ENV=production` sobe com um token de admin publicamente documentado protegendo o relatório financeiro e a deleção de usuários. baseline: `GET /api/admin/financial-report` com `X-Admin-Token: dev-admin-token` → 200 com receita por curso e nomes de alunos; `DELETE /api/users/1` com o mesmo token → 200. Mitigação parcial no item (b): a senha é gravada com scrypt+salt e **nenhuma rota verifica senha** (não existe login), então a credencial `123` não autentica nada hoje — o risco se materializa quando um login for adicionado.
Recommendation: tornar `ADMIN_TOKEN` obrigatório em qualquer ambiente (sem fallback literal): se ausente, gerar com `crypto.randomBytes` no boot e imprimir uma vez no log, ou falhar o boot em todos os ambientes; remover `DEV_ADMIN_TOKEN` e o valor de `README.md`/`api.http`/`.env.example` (deixar placeholder). Para o seed, ler `SEED_USER_PASSWORD` do ambiente e, na ausência, gerar senha aleatória e imprimi-la uma vez (sem fallback literal). (playbook PB-01, PB-25)

### [HIGH] Escritas multi-etapa sem transação — escrita fora da fila na conexão compartilhada (AP-10)
File: src/models/user.model.js:13
File: src/controllers/user.controller.js:5
File: src/db/connection.js:30-45
Description: `withTransaction` serializa **apenas** as chamadas que passam por ele (`let queue = Promise.resolve()` em `src/db/connection.js:30`, `const result = queue.then(...)` em `:32`). O `DELETE` de usuário não passa pela fila: `deleteById: (id) => db.run('DELETE FROM users WHERE id = ?', [id])` (`src/models/user.model.js:13`), chamado direto em `src/controllers/user.controller.js:5`. Como `BEGIN`/`COMMIT`/`ROLLBACK` valem para a conexão inteira (uma única `new sqlite3.Database(filename)` em `src/db/connection.js:8`), um `DELETE` submetido enquanto a transação de um checkout está aberta executa **dentro** dessa transação.
Impact: confirmado empiricamente com script contra o próprio `src/db/connection.js` (segurando uma transação aberta e submetendo o `DELETE` concorrente): o `DELETE` respondeu `changes=1` — o cliente receberia **200 e a mensagem de sucesso** — e em seguida o `ROLLBACK` da transação do checkout desfez a deleção (`linhas restantes: [{"id":1,"v":"vitima"}]`). Deleção confirmada ao cliente que não aconteceu, sob carga concorrente. A janela é pequena (a transação do checkout faz 3 INSERTs), mas o resultado é silencioso: não há erro em log nem no corpo da resposta.
Recommendation: rotear **toda** escrita pela mesma fila — fazer o `DELETE` dentro de `db.withTransaction(...)` (ou expor um `db.serialize`/fila única que cubra `run` de escrita), de modo que nenhuma instrução de escrita seja submetida entre o `BEGIN` e o `COMMIT` de outra operação. Alternativa: usar uma conexão por requisição em vez de uma conexão compartilhada. (playbook PB-09, PB-17)

### [MEDIUM] Sem catch-all de 404/405 no handler central (AP-12)
File: src/app.factory.js:42-46
Description: `createApp` registra os três routers (`:42-44`) e em seguida o error handler (`:46`), sem nenhum middleware catch-all `app.use((req, res, next) => ...)` entre eles. `grep -rnE "app\.use\(\s*\(\s*req\s*,\s*res" src/` não retorna nada. Caminhos desconhecidos e métodos não casados caem no 404 padrão do Express.
Impact: baseline: `GET /api/unknown` → `404 text/html` com página HTML completa (`<!DOCTYPE html>...<pre>Cannot GET /api/unknown</pre>`); idem `GET /__rota-inexistente__`. `GET /api/checkout` (rota existe só em POST) → `404` HTML, sem 405. `PUT /api/users/1` → `404` HTML. Em contraste, todos os erros da aplicação respondem texto puro via `src/middlewares/errorHandler.js:9,13,16`. Cliente que faz parse da resposta de erro quebra ao receber HTML; o path digitado errado é refletido no corpo da página.
Recommendation: registrar um middleware catch-all **depois** dos routers e **antes** do error handler, lançando `NotFoundError` (já existe em `src/errors/AppError.js:17`) para que o handler central responda no formato da API. Opcionalmente, responder 405 quando o path casa mas o método não. (playbook PB-23, PB-08)

### [MEDIUM] Validação de entrada ausente em `DELETE /api/users/:id` (AP-14)
File: src/routes/user.routes.js:7
File: src/controllers/user.controller.js:4-5
Description: `req.params.id` vai direto do router ao model (`res.send(await userController.deleteUser(req.params.id))` em `src/routes/user.routes.js:7` → `await userModel.deleteById(id)` em `src/controllers/user.controller.js:5`), sem checar tipo, formato ou existência do recurso. `deleteById` não inspeciona `changes`. Não há `validators/` para esta rota (só `src/validators/checkout.validator.js` existe, e cobre apenas o checkout).
Impact: verificado em runtime (porta 3102, com token válido): `DELETE /api/users/abc` → 200 `Usuário deletado...`; `DELETE /api/users/0` → 200; `DELETE /api/users/1%20OR%201=1` → 200. Nos três casos nada foi apagado — o relatório financeiro seguinte continuou mostrando `Clean Architecture revenue 997, students [Leonan 997]`. A query é parametrizada (`'DELETE FROM users WHERE id = ?'`), portanto **não** há SQL injection; o problema é confirmar ao cliente uma deleção que não ocorreu. Um script de limpeza que itere IDs recebe 200 para todos e não detecta erro.
Recommendation: validar `:id` como inteiro positivo (400 em caso contrário) e usar `changes` do resultado de `deleteById` para decidir a resposta. Mudar o 200 de id inexistente para 404 altera o contrato do baseline — tratar como mudança versionada, não silenciosa. (playbook PB-11)

### [MEDIUM] Mensagem de resposta que contradiz o comportamento real (AP-26)
File: src/controllers/user.controller.js:1, 7
Description: `const DELETE_USER_MESSAGE = 'Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.'` (`:1`) é a resposta de `DELETE /api/users/:id` (`:7`). O comportamento mudou: `enrollments.user_id ... ON DELETE CASCADE` (`src/db/schema.js:19`), `payments.enrollment_id ... ON DELETE CASCADE` (`:24`) e `PRAGMA foreign_keys = ON` (`:72`) removem os filhos automaticamente. O comentário em `:6` reconhece a divergência mas a mensagem foi mantida.
Impact: baseline #9 → #10 prova a contradição: após `DELETE /api/users/1`, o relatório não tem nenhuma entrada órfã `"Unknown"` (`Clean Architecture revenue 0, students []`), ou seja, matrículas e pagamentos foram removidos. A mensagem afirma o oposto. Severidade elevada de LOW para MEDIUM pela regra de ajuste do catálogo: a mensagem induz decisão errada sobre integridade — um operador que a lê conclui que o banco ficou inconsistente e pode rodar limpeza manual, apagando dados de outros usuários.
Recommendation: corrigir a string para descrever a cascata. Como o texto é o corpo da resposta (contrato observável), alterar numa versão nova da API ou documentar explicitamente a mudança; não é aceitável manter a mensagem falsa indefinidamente. (playbook PB-24)

### [LOW] Nomenclatura ruim no contrato de entrada (AP-21)
File: src/validators/checkout.validator.js:13, 15, 22
Description: o corpo de `POST /api/checkout` usa campos crípticos `usr`, `eml`, `pwd`, `c_id`, `card`, desestruturados em `src/validators/checkout.validator.js:13` e mapeados para nomes internos legíveis em `:22` (`{ name, email, password, courseId, cardNumber }`). Os nomes internos já estão corretos em services/models — a dívida é apenas na borda HTTP.
Impact: legibilidade e onboarding: quem lê `api.http:9-13` precisa do validator para descobrir que `c_id` é o id do curso e `usr` é o nome (não um username). Sem impacto de runtime. Renomear quebra qualquer cliente existente, por isso o catálogo manda registrar sem renomear.
Recommendation: manter os campos atuais e documentá-los no README; aceitar os nomes novos como aliases numa versão futura (`/api/v2/checkout`) antes de descontinuar os antigos. (playbook PB-18)

### [LOW] Código morto / exports nunca consumidos (AP-23)
File: src/db/connection.js:25-27, 47
File: src/middlewares/auth.js:18
File: src/utils/password.js:8, 14, 18
File: src/db/schema.js:9
Description: três trechos sem consumidor. (a) `close` é definido (`src/db/connection.js:25-27`) e exportado (`:47`), mas nenhum módulo o chama — `grep -rn "\.close(" src/` só casa dentro de `db/connection.js`; o processo não fecha a conexão no shutdown. (b) `ADMIN_TOKEN_HEADER` é exportado em `src/middlewares/auth.js:18` e usado apenas internamente (`:9`); nenhum outro módulo importa. (c) a coluna `users.pass` (`src/db/schema.js:9`) é **escrita** (`src/models/user.model.js:6`, `src/db/schema.js:49`) e nunca lida: não há `SELECT` de `pass` em nenhum model, nem função de verificação (`verifyPassword`/`checkPassword` inexistentes), porque não há rota de login. `hashPassword` e `randomPassword` (`src/utils/password.js:8,14`) produzem dado write-only.
Impact: baixo. Toda a máquina de senha (scrypt, salt, senha aleatória) custa manutenção e dá a impressão de que existe autenticação de usuário — mas a única credencial efetiva da API é o `X-Admin-Token`. O `close` ausente no shutdown é inofensivo com `:memory:` e vira handle vazado se `DB_PATH` apontar para arquivo.
Recommendation: chamar `db.close()` num handler de `SIGTERM`/`SIGINT` (ou remover o export); remover o export de `ADMIN_TOKEN_HEADER` ou consumi-lo onde o header é documentado; manter a coluna e os helpers de senha **apenas** se a rota de login estiver planejada — caso contrário, remover junto com a coluna. Decisão de produto, não de refatoração: registrar em vez de apagar às cegas. (playbook PB-18)

Deprecated APIs: nenhuma ocorrência encontrada (greps executados: `new Buffer(`, `createCipher(`/`createDecipher(`, `url.parse(`, `body-parser`/`bodyParser.`, `^var `, `fs.exists(`, `req.param(`, `res.send(<status>,`/`res.json(<status>,`, `res.sendfile(`, `app.del(`, `require('querystring')`, `util.is[A-Z]`, `createHash('md5'|'sha1')`). O único hit de `body-parser` é um comentário em `src/middlewares/errorHandler.js:11`. A API de callback do `sqlite3` continua encapsulada num único adaptador Promise (`src/db/connection.js:10-27`), que é exatamente a correção recomendada por PB-13. Nenhum warning de deprecação no log do baseline.

Verificados sem ocorrência: AP-02 SQL injection (todas as 15 chamadas `db.*` usam placeholders `?`; `DELETE /api/users/1 OR 1=1` não apagou nada), AP-03 God file (maior arquivo 77 linhas; nenhum arquivo mistura HTTP e SQL), AP-04 exposição de dados sensíveis (nenhum `console.*`, nenhum `SELECT *`, log de pagamento só com `cardLast4`), AP-05 hash de senha (scrypt com salt aleatório de 16 bytes), AP-06 endpoints admin sem auth (`requireAdmin` nas duas rotas; 401 verificado sem header e com token errado), AP-07 debug/0.0.0.0 (porta e host via env, `HOST` default `127.0.0.1`), AP-08 regra de negócio em rotas/controllers (routes+controllers somam 57 linhas, zero SQL), AP-09 estado global mutável (conexão criada por factory e injetada via `createApp`), AP-11 config/app factory (ambos presentes; nenhum efeito colateral no import), AP-13 N+1 (relatório financeiro em 1 query com LEFT JOINs; único loop é sobre 2 cursos estáticos do seed), AP-15 duplicação (`npx jscpd --min-lines 5 src` → 0 clones), AP-16 callback hell (nenhum `self = this` nem contador manual), AP-18 middleware mal configurado (sem CORS aberto; error handler registrado por último, após os routers), AP-19 integridade referencial (FKs, `UNIQUE`, `NOT NULL` e `PRAGMA foreign_keys = ON` presentes; `enrollments.course_id` sem `ON DELETE` é restrição intencional e não há rota de deleção de curso), AP-20 magic numbers (constantes em `src/models/constants.js`; os literais 400/500 em `src/middlewares/errorHandler.js:12` são faixas HTTP padrão), AP-22 `console.log` (nenhuma ocorrência; logger com níveis), AP-24 token previsível (não há emissão de token nem rota de login; o `X-Admin-Token` é segredo compartilhado comparado com `crypto.timingSafeEqual`), AP-25 PII sem auth (o único endpoint que devolve nomes de alunos exige `X-Admin-Token`).

## Previous Remaining Known Issues
- Token de admin via header `X-Admin-Token` com default de dev `dev-admin-token` → **persiste** (AP-01) — `src/config/index.js:1,10`; `assertConfig` só barra em `APP_ENV=production` (`:16-18`), e o default é `'development'` (`:3`).
- Mensagem do DELETE preservada mas já não descreve o comportamento (cascata) → **persiste** (AP-26) — `src/controllers/user.controller.js:1`; baseline #10 mostra zero órfãos após a deleção.
- `DELETE /api/users/:id` com id inexistente continua 200 → **persiste** (AP-14) — verificado em runtime: `/api/users/999`, `/abc`, `/0` todos 200 sem apagar nada.
- `HOST` default passou a ser `127.0.0.1` (antes 0.0.0.0) → **resolvido na direção segura** — `src/config/index.js:8`; container precisa de `HOST=0.0.0.0` explícito, como documentado em `.env.example:7`. Não é finding.
- Campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`) mantidos → **persiste** (AP-21) — `src/validators/checkout.validator.js:13`.
- Erros em texto puro; 500 inesperado responde `Erro interno do servidor` → **persiste por design** — `src/middlewares/errorHandler.js:9,16`; preservação de contrato do baseline, sem vazamento de stack trace (baseline #12 confirma). Não é finding.
- Gateway de pagamento simulado; `PAYMENT_GATEWAY_KEY` só injetada → **persiste por design** — `src/services/paymentGateway.service.js:12` usa a chave apenas em `gatewayConfigured: Boolean(apiKey)`. É stub declarado do desafio, não anti-pattern do catálogo. Não é finding.
- Não há testes automatizados → **persiste** — inventário da Fase 1: 27 arquivos-fonte, nenhum `.test.js`/`.spec.js`; `package.json:6-8` tem apenas o script `start`. Sem entrada no catálogo; registrado como dívida.
- Banco `:memory:` sem migração para `DB_PATH` em arquivo → **persiste** — `src/db/schema.js:73` usa `CREATE TABLE IF NOT EXISTS`, que não altera tabela existente. Sem entrada no catálogo; registrado como dívida.
- Sem equivalente anterior (achados novos desta iteração): AP-10 escrita fora da fila de transação, AP-12 ausência de catch-all 404/405 e AP-23 código morto não constavam nas Remaining Known Issues da iteração 1.

================================
Total: 7 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
