# Baseline — ecommerce-api-legacy (iteração 2 — projeto já refatorado na iteração 1)
Boot: `PORT=3101 npm start` (= `node src/app.js`; porta 3000 default mas ocupada por Docker nesta máquina; porta/host/db vêm do env em `src/config/index.js:7-9`) | Seed: automático no boot (`initSchema(db)` em `src/app.js:13` → `src/db/schema.js:71-75`, SQLite `:memory:` — estado zera a cada boot, nenhum arquivo de banco criado)
Versões: Node v24.19.0 / Express 4.22.1 (manifesto `^4.18.2`) / sqlite3 5.1.7 (manifesto `^5.1.6`)
Credencial de admin: header `X-Admin-Token: dev-admin-token` (default de dev em `src/config/index.js:1,10`), exigido em `GET /api/admin/financial-report` e `DELETE /api/users/:id`. Nenhuma rota de login existe.

Estado inicial (seed): users {1: Leonan, pass `scrypt$...` de '123'}, courses {1: Clean Architecture 997, 2: Docker 497}, enrollments {1: user 1 → course 1}, payments {1: enrollment 1, 997, PAID}.

Sequência executada contra **um único boot** (banco `:memory:`; as linhas 5–10 dependem das mutações anteriores).

| # | Método | Path | Payload / Header | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | /api/admin/financial-report | `X-Admin-Token` válido | 200 | `application/json` lista de `{course, revenue, students:[{student, paid}]}` (2 itens, ordem determinística por `c.id`: Clean Architecture 997 [Leonan 997]; Docker 0 []) |
| 1b | GET | /api/admin/financial-report | sem header | 401 | `text/html` texto puro `Não autorizado` |
| 1c | GET | /api/admin/financial-report | `X-Admin-Token: errado` | 401 | `text/html` texto puro `Não autorizado` |
| 2 | POST | /api/checkout | `{"usr":"X"}` | 400 | `text/html` texto puro `Bad Request` |
| 3 | POST | /api/checkout | `{usr:"Z",eml:"x@x.com",pwd:"a",c_id:999,card:"4111"}` | 404 | `text/html` texto puro `Curso não encontrado` |
| 4 | POST | /api/checkout | `{usr:"João",eml:"joao@teste.com",pwd:"123",c_id:1,card:"5111222233334444"}` | 400 | `text/html` texto puro `Pagamento recusado`; **usuário João NÃO é criado** (confirmado em #7/#10) |
| 5 | POST | /api/checkout | `{usr:"Guilherme",eml:"gui@fullcycle.com.br",pwd:"senhaforte",c_id:2,card:"4111222233334444"}` | 200 | `application/json` `{"msg":"Sucesso","enrollment_id":2}` (novo usuário id 2) |
| 6 | POST | /api/checkout | `{usr:"Leonan",eml:"leonan@fullcycle.com.br",c_id:2,card:"4000000000000000"}` (usuário existente, sem pwd) | 200 | `application/json` `{"msg":"Sucesso","enrollment_id":3}` (reusa user id 1) |
| 7 | GET | /api/admin/financial-report | `X-Admin-Token` válido | 200 | `application/json`; Clean Architecture 997 [Leonan 997]; Docker 994 [Guilherme 497, Leonan 497] |
| 8b | DELETE | /api/users/999 | sem header | 401 | `text/html` `Não autorizado` |
| 8 | DELETE | /api/users/999 | `X-Admin-Token` válido | 200 | `text/html` `Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.` (id inexistente também 200) |
| 9 | DELETE | /api/users/1 | `X-Admin-Token` válido | 200 | `text/html` mesma mensagem |
| 10 | GET | /api/admin/financial-report | `X-Admin-Token` válido | 200 | `application/json`; **sem entradas órfãs `"Unknown"`**: Clean Architecture 0 []; Docker 497 [Guilherme 497] (cascata funcionando) |
| 11 | GET | /api/unknown | - | 404 | **`text/html` HTML padrão do Express** (`<!DOCTYPE html>...<pre>Cannot GET /api/unknown</pre>`) |
| 11b | GET | /__rota-inexistente__ | - | 404 | **`text/html` HTML padrão do Express** (`<pre>Cannot GET /__rota-inexistente__</pre>`) |
| 11c | GET | /api/checkout (método errado; rota existe só em POST) | - | 404 | **`text/html` HTML padrão do Express** (`<pre>Cannot GET /api/checkout</pre>`) — não há 405 |
| 12 | POST | /api/checkout | `{bad` (JSON malformado) | 400 | `text/html` texto puro `Bad Request` (sem stack trace) |
| 13 | POST | /api/checkout | `{usr:"N",eml:"n@n.com",c_id:1,card:4111}` (card numérico) | 400 | `text/html` texto puro `Bad Request`; **processo continua vivo** |
| 14 | GET | /api/admin/financial-report | `X-Admin-Token` válido | 200 | idêntico a #10 — servidor sobreviveu a #12 e #13 |

Observações:
- Nenhum warning de deprecação no log (`grep -iE 'deprecat|warning|TypeError|Error:'` vazio).
- Log não expõe PAN nem chave de gateway: `{"msg":"Processando pagamento","cardLast4":"4444","amount":997,"gatewayConfigured":false}` (JSON por linha, `src/utils/logger.js`).
- `gatewayConfigured:false` porque `PAYMENT_GATEWAY_KEY` não foi exportada no baseline (default `''`, `src/config/index.js:11`).
- Respostas de sucesso são JSON; respostas de erro da aplicação são **texto puro** com `Content-Type: text/html` (`res.send` de string em `src/middlewares/errorHandler.js:9,13,16`).
- **404 de rota inexistente / método não casado devolve HTML do Express**, não o formato de erro da API — não há catch-all antes do error handler (`src/app.factory.js:42-46`).
- Pagamento recusado não cria usuário (transação OK); DELETE de usuário remove matrículas/pagamentos em cascata (`PRAGMA foreign_keys = ON`, `src/db/schema.js:72`).
- `DELETE /api/users/:id` com id inexistente devolve 200 e a mensagem de sucesso.
- A mensagem do DELETE afirma que "matrículas e pagamentos ficaram sujos no banco", mas #10 prova o contrário (cascata) — mensagem falsa.
- Reprodução: banco em memória — basta reiniciar o processo para voltar ao seed. Nenhum arquivo SQLite foi criado.
- Servidor do baseline parado (`pkill`; `lsof -nP -iTCP:3101 -sTCP:LISTEN` vazio).
