================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js v24.19.0) + Express ^4.18.2 (instalada 4.22.1)
Files:   3 analyzed | ~180 lines of code

## Summary
CRITICAL: 6 | HIGH: 5 | MEDIUM: 5 | LOW: 4

## Findings

### [CRITICAL] Credenciais / segredos hardcoded (AP-01)
File: src/utils.js:2-5
File: src/AppManager.js:18
Description: O objeto `config` exportado contém literais de produção: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_****REDACTED****"` (prefixo de chave live) e `smtpUser: "no-reply@fullcycle.com.br"`. O seed insere o usuário Leonan com senha em texto puro `'123'`. Não há nenhum `process.env` no projeto (`grep -rn "process\.env" src` = 0).
Impact: Qualquer pessoa com acesso ao repositório obtém a chave do gateway de pagamento e a senha do banco; trocar segredo exige novo deploy; impossível ter valores distintos por ambiente.
Recommendation: Mover todos os segredos para variáveis de ambiente lidas em um módulo `config/` único, com `.env.example` contendo valores fictícios; remover a senha em texto puro do seed (gerar hash no seed). (playbook PB-01)

### [CRITICAL] God Class / God File (AP-03)
File: src/AppManager.js:4-139
File: src/utils.js:1-25
Description: A classe `AppManager` reproduz o exemplo `CoreManager` do catálogo: cria a conexão (`new sqlite3.Database(':memory:')`, linha 7), cria schema e seed (`initDb`, 10-23) e registra todas as rotas HTTP com SQL, regra de pagamento, criação de usuário, auditoria e serialização inline (`setupRoutes`, 25-138). `utils.js` mistura config com segredos, cache global, função de "criptografia" e logging.
Impact: Nenhuma responsabilidade pode ser testada ou trocada isoladamente (banco, pagamento, relatório); qualquer mudança toca o mesmo arquivo; não há como injetar outro banco.
Recommendation: Separar em config, camada de dados (conexão + schema/seed + models/repositórios por entidade: users, courses, enrollments, payments, audit_logs), services (checkout, relatório financeiro, usuários), controllers e routes; `app.js` vira composition root. (playbook PB-03)

### [CRITICAL] Exposição de dados sensíveis (AP-04)
File: src/AppManager.js:45
Description: `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` grava o número completo do cartão (PAN) e a chave live do gateway em log a cada checkout.
Impact: baseline: o log contém `Processando cartão ****REDACTED**** na chave pk_live_****REDACTED****`. Vazamento de PAN em log viola PCI-DSS e expõe a chave do gateway a quem tiver acesso aos logs.
Recommendation: Remover o log de cartão/chave; se necessário, logar apenas os 4 últimos dígitos mascarados e nunca o segredo. (playbook PB-06)

### [CRITICAL] Hash de senha fraco / caseiro (AP-05)
File: src/utils.js:17-23
File: src/AppManager.js:18, 68
Description: `badCrypto` repete 10000 vezes os 2 primeiros caracteres do Base64 da senha e corta em 10 caracteres — o resultado depende só do 1º–2º byte da senha, sem salt. Quando `pwd` falta, usa a senha default `"123456"` (linha 68). O seed grava `'123'` em texto puro (linha 18). Não há bcrypt/scrypt/argon2/pbkdf2 no projeto.
Impact: Colisões triviais confirmadas em runtime nesta sessão: `badCrypto('senhaforte')` = `badCrypto('senha')` = `c2c2c2c2c2`; `badCrypto('123')` = `badCrypto('123456')` = `MTMTMTMTMT`. O "hash" é reversível na prática e qualquer senha com o mesmo prefixo é equivalente; usuários criados sem `pwd` ficam com senha conhecida.
Recommendation: Usar `crypto.scrypt` (stdlib) com salt aleatório e comparação `timingSafeEqual`; não aplicar senha default (gerar senha aleatória ou exigir o campo conforme o contrato); gerar o hash também no seed. (playbook PB-05)

### [CRITICAL] Endpoints administrativos/destrutivos sem autenticação (AP-06)
File: src/AppManager.js:80, 131
Description: `GET /api/admin/financial-report` (receita por curso + nomes dos alunos e valores pagos) e `DELETE /api/users/:id` são registrados direto no `app` sem nenhum middleware de auth (`grep -nE "authenticate|verifyToken|requireAdmin|passport"` vazio).
Impact: baseline: `GET /api/admin/financial-report` → 200 anônimo com dados financeiros e nomes de alunos; `DELETE /api/users/1` → 200 anônimo, apagando o usuário. Qualquer cliente da rede lê dados financeiros/pessoais e apaga contas.
Recommendation: Manter as rotas e exigir credencial de admin via middleware (ex.: header `X-Admin-Token` comparado com valor de env em tempo constante), retornando 401/403 sem ela. (playbook PB-07)

### [CRITICAL] Porta fixa / bind em todas as interfaces (AP-07)
File: src/utils.js:6
File: src/app.js:12
Description: A porta `3000` é literal no config (`port: 3000`) e `app.listen(config.port, ...)` não recebe host, portanto escuta em todas as interfaces. Não há leitura de `PORT`/`HOST` do ambiente (baseline precisou de wrapper `require('./src/utils').config.port=3101` para mudar a porta).
Impact: baseline: `lsof` mostrou `TCP *:3101 (LISTEN)` — a API (incluindo as rotas admin sem auth) fica exposta em qualquer interface de rede; impossível configurar porta por ambiente sem editar código.
Recommendation: Ler `PORT` e `HOST` do ambiente no módulo de config (default `127.0.0.1` em dev e a porta original 3000) e iniciar o servidor no entry point a partir dessa config. (playbook PB-01, PB-16)

### [HIGH] Regra de negócio dentro das rotas (AP-08)
File: src/AppManager.js:28-78
Description: O handler de `POST /api/checkout` (~50 linhas) valida o payload, busca curso, busca/cria usuário com hash, decide a aprovação do pagamento (`cc.startsWith("4") ? "PAID" : "DENIED"`), cria matrícula, pagamento, registro de auditoria, popula cache e serializa a resposta — tudo inline, com SQL direto.
Impact: A regra de pagamento e o fluxo de matrícula não podem ser testados sem HTTP + banco; trocar o gateway ou a regra exige reescrever o handler.
Recommendation: Extrair um `CheckoutService` (orquestra usuário → pagamento → matrícula → auditoria) e um `PaymentGateway` isolado; o controller só lê o request, chama o service e formata a resposta. (playbook PB-04)

### [HIGH] Estado global mutável / conexão sem DI (AP-09)
File: src/utils.js:9, 12-15, 25
File: src/AppManager.js:7
Description: `let globalCache = {}` é um cache de módulo exportado, sem limite, escrito a cada checkout por `logAndCache` (`last_checkout_<userId>`) e nunca lido. A conexão SQLite é instanciada dentro do construtor de `AppManager` (`new sqlite3.Database(':memory:')`), sem injeção.
Impact: Crescimento de memória sem limite proporcional ao nº de usuários; estado compartilhado entre requisições; impossível substituir o banco em testes ou reutilizar a conexão fora da classe.
Recommendation: Criar a conexão em um módulo de banco e injetá-la nos repositórios/services pelo composition root; remover o cache global (ou substituí-lo por um componente injetado e limitado, se tiver uso real). (playbook PB-17)

### [HIGH] Escritas multi-etapa sem transação (AP-10)
File: src/AppManager.js:50-63, 69-72
Description: O checkout faz `INSERT INTO users` (69) → `INSERT INTO enrollments` (50) → `INSERT INTO payments` (54) → `INSERT INTO audit_logs` (57) em callbacks encadeados, sem `BEGIN/COMMIT/ROLLBACK` (`grep -nE "BEGIN|COMMIT|ROLLBACK"` vazio). O usuário é criado antes da decisão de pagamento; o erro do insert de auditoria é ignorado.
Impact: baseline: `POST /api/checkout` com cartão `5111...` → 400 "Pagamento recusado", mas o usuário João foi criado mesmo assim (o checkout seguinte recebeu user id 3). Falha entre matrícula e pagamento deixa matrícula sem pagamento.
Recommendation: Decidir o pagamento antes de qualquer escrita e envolver criação de usuário + matrícula + pagamento + auditoria numa única transação (`BEGIN`/`COMMIT`, `ROLLBACK` em erro) na camada de dados. (playbook PB-09)

### [HIGH] Sem módulo de config / app factory; efeitos colaterais no import (AP-11)
File: src/app.js:5-14
File: src/utils.js:1-7
Description: `app.js` cria o app, instancia `AppManager`, executa `initDb()` (schema + seed) e chama `listen` no nível do módulo; não há função que construa o app com config injetada. A "config" é um literal em `utils.js`; zero `process.env` no código.
Impact: Importar `app.js` (ex.: em testes) sobe o servidor e o banco; impossível criar uma instância com outra config/porta/banco sem editar arquivos. Além disso, `initDb` usa `db.run` assíncrono e o `listen` não espera o seed terminar.
Recommendation: Criar `config/` lendo env com defaults, uma factory `createApp({ db, config })` que monta middlewares/rotas/error handler, e um entry point que aguarda schema+seed antes do `listen`. (playbook PB-01, PB-16)

### [HIGH] Validação de entrada ausente — derruba o processo (AP-14)
File: src/AppManager.js:29-35, 46, 132
Description: Os campos `usr`, `eml`, `pwd`, `c_id`, `card` são lidos sem checar tipo/formato (só presença, linha 35); `cc.startsWith("4")` assume string. `req.params.id` do DELETE vai direto ao SQL sem validação nem verificação de existência.
Impact: baseline #13: `POST /api/checkout` com `"card":4111` (número) → `TypeError: cc.startsWith is not a function` em `src/AppManager.js:46` dentro de callback do sqlite3 — **o processo Node morre** e a API fica fora do ar (DoS com uma requisição). baseline #8: `DELETE /api/users/999` (inexistente) → 200 "Usuário deletado...".
Recommendation: Validar tipos e formatos na borda (controller/validator) retornando 400 com o mesmo formato atual (`Bad Request`); retornar 404 para usuário inexistente apenas se aceito como mudança segura documentada — caso contrário manter 200 e registrar. (playbook PB-11)

### [MEDIUM] Erros engolidos / sem error handler central / stack trace vazado (AP-12)
File: src/AppManager.js:38, 57, 92-93, 104, 106, 133
File: src/app.js:5-10
Description: `err` é ignorado nos callbacks das linhas 57, 92, 104, 106 e 133; na linha 92 um erro deixa `enrollments` indefinido e `enrollments.length` (93) lançaria exceção. Erro de banco na linha 38 é respondido como 404 "Curso não encontrado". Não há middleware `(err, req, res, next)` em `app.js`. Erros saem em texto puro (`res.status(...).send("...")`) enquanto sucessos são JSON.
Impact: baseline #12: corpo JSON malformado → 400 com HTML do Express contendo stack trace completo e caminhos absolutos de `node_modules`. Falhas de banco ficam invisíveis ou mascaradas como 404.
Recommendation: Error handler central registrado após as rotas, exceções de domínio mapeadas para status, wrapper async nas rotas (Express 4), tratar `err` em toda chamada ao banco; manter o corpo texto das mensagens existentes para não quebrar clientes. (playbook PB-08)

### [MEDIUM] Queries N+1 / agregação em memória (AP-13)
File: src/AppManager.js:83, 89-92, 102-106
Description: O relatório financeiro faz 1 query de cursos, 1 query de matrículas por curso (92, dentro de `courses.forEach`) e 2 queries por matrícula (usuário em 104 e pagamento em 106, dentro de `enrollments.forEach`), somando a receita em JS (`courseData.revenue += payment.amount`).
Impact: Nº de queries = 1 + C + 2·E (cresce linearmente com matrículas); a ordem dos cursos no JSON é não determinística (baseline: ordem variou entre #1 e #7) por depender da ordem de conclusão dos callbacks.
Recommendation: Substituir por uma query com `JOIN` courses ⟕ enrollments ⟕ users ⟕ payments e agregação (`SUM(CASE WHEN status='PAID' ...)`) ou uma query única montada em memória, preservando o shape `{course, revenue, students:[{student, paid}]}`. (playbook PB-10)

### [MEDIUM] Callback hell (AP-16)
File: src/AppManager.js:26, 37-77, 86, 93-98, 117-121
Description: O checkout aninha 6 níveis de callbacks (`db.get` → `db.get` → `db.run` → `db.run` → `db.run`, 37-77) e usa `const self = this` (26) para alternar entre `this.lastID` e `self.db`. O relatório sincroniza com contadores manuais (`coursesPending--`, `enrPending--`) e o bloco `report.push(courseData); coursesPending--; if (coursesPending === 0) res.json(report);` está duplicado em 96-98 e 119-121.
Impact: Fluxo difícil de ler e de tratar erro (um `return` esquecido gera resposta dupla ou requisição pendurada); duplicação já é fonte de divergência.
Recommendation: Wrapper Promise sobre o sqlite3 (`run/get/all` async) e reescrever handlers/services com `async/await`, eliminando contadores manuais e `self`. (playbook PB-12)

### [MEDIUM] Deprecated APIs (AP-17)
File: src/AppManager.js:37, 40, 50, 54, 57, 69, 83, 92, 104, 106, 133   — API callback do `sqlite3` (`db.run/get/all(sql, params, cb)`) → wrapper com Promise (`util.promisify` / funções `run/get/all` async)
Description: Todas as 11 chamadas ao banco usam a API de callback do `sqlite3`, listada como deprecated no catálogo. O grep do catálogo (`db\.(run|get|all|each)\([^)]*(function|=>)`) não casa porque o SQL contém `)`; foi usado `grep -nE "db\.(run|get|all|each)\(.*(function\s*\(|=>)" src/*.js` (11 ocorrências). Demais greps da tabela Node/Express (`new Buffer(`, `createCipher(`, `url.parse(`, `body-parser`, `var`, `fs.exists(`, `req.param(`, `res.send(status, body)`, `res.sendfile(`, `app.del(`, `querystring`, `util.isX`, `createHash('md5'|'sha1')`) sem ocorrência. Nenhum warning de deprecação no log do baseline.
Impact: A API de callback é a causa direta do callback hell (AP-16) e impede `async/await` e propagação de erro para um handler central.
Recommendation: Introduzir um módulo de banco com `run/get/all` promisificados e migrar todas as chamadas. (playbook PB-13)

### [MEDIUM] Integridade referencial ausente (AP-19)
File: src/AppManager.js:12-16, 131-137
Description: As tabelas não têm `FOREIGN KEY`, `UNIQUE` nem `NOT NULL` (`users.email` sem UNIQUE; `enrollments.user_id/course_id` e `payments.enrollment_id` sem REFERENCES); não há `PRAGMA foreign_keys = ON`. `DELETE FROM users WHERE id = ?` não trata matrículas/pagamentos — a própria resposta admite: "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."
Impact: baseline #10: após `DELETE /api/users/1`, o relatório lista os alunos como `"student":"Unknown"` com pagamentos órfãos ainda somados à receita.
Recommendation: Declarar FKs (com `ON DELETE CASCADE` ou deleção explícita em transação), `UNIQUE(email)`, habilitar `PRAGMA foreign_keys = ON`; preservar a mensagem de resposta do DELETE. (playbook PB-20)

### [LOW] Magic numbers / strings (AP-20)
File: src/AppManager.js:21, 46, 48, 108
File: src/utils.js:19-22
Description: Prefixo de cartão aprovado `"4"` (46), status `"PAID"`/`"DENIED"` repetidos como literais (21, 46, 48, 108); `10000`, `2` e `10` sem nome em `badCrypto`.
Impact: Regras de domínio espalhadas e duplicadas; mudar um status exige caçar strings.
Recommendation: Constantes nomeadas (`PAYMENT_STATUS.PAID/DENIED`, `APPROVED_CARD_PREFIX`) em módulo único. (playbook PB-14)

### [LOW] Nomenclatura ruim (AP-21)
File: src/AppManager.js:4, 29-33
File: src/app.js:2, 8
Description: Variáveis crípticas `u`, `e`, `p`, `cid`, `cc` (29-33) e classe genérica `AppManager`. Os campos do contrato HTTP também são crípticos (`usr`, `eml`, `pwd`, `c_id`, `card`), mas **não devem ser renomeados** (quebraria clientes).
Impact: Leitura e revisão mais lentas; nomes não expressam o domínio (checkout, matrícula, pagamento).
Recommendation: Renomear variáveis internas (`name`, `email`, `password`, `courseId`, `cardNumber`) mapeando os campos do request no controller; eliminar `AppManager` no split. (playbook PB-18)

### [LOW] console.log como logging (AP-22)
File: src/app.js:13
File: src/utils.js:13
Description: Boot (`Frankenstein LMS rodando na porta ...`) e "cache" (`[LOG] Salvando no cache: ...`) usam `console.log` sem nível nem formato (o log de cartão em AppManager.js:45 está registrado em AP-04).
Impact: Sem níveis/filtragem; logs de negócio misturados com stdout.
Recommendation: Pequeno módulo de logger com níveis (stdlib `console` encapsulado ou lib já instalada), sem dados sensíveis. (playbook PB-15)

### [LOW] Imports não usados / código morto (AP-23)
File: src/AppManager.js:2
File: src/utils.js:2-3, 5, 10, 25
Description: `totalRevenue` é declarado (`let totalRevenue = 0`, utils.js:10), exportado (25) e importado em AppManager.js:2, mas nunca usado. `dbUser`, `dbPass` e `smtpUser` (utils.js:2, 3, 5) nunca são lidos. A tabela `audit_logs` é apenas escrita.
Impact: Ruído e falsa impressão de que existe controle de receita/SMTP/credencial de banco; segredos mantidos sem necessidade.
Recommendation: Remover variáveis/exports/imports mortos; manter na config apenas chaves realmente usadas. (playbook PB-18)

Verificados sem ocorrência: AP-02 (todas as queries usam placeholders `?`; o template literal em AppManager.js:57 é valor vinculado, não SQL), AP-18 CORS (nenhum `cors` no projeto; ausência de middlewares de auth/erro já registrada em AP-06 e AP-12), AP-15 (única duplicação encontrada — bloco de contadores 96-98/119-121 — registrada em AP-16).

================================
Total: 20 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
