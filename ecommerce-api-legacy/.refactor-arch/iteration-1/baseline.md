# Baseline — ecommerce-api-legacy
Boot: `node -e "require('./src/utils').config.port=3101; require('./src/app')"` (porta 3101; porta 3000 hardcoded em `src/utils.js:6`, original `npm start` = `node src/app.js`) | Seed: automático no boot (`initDb()` em `src/AppManager.js:10-23`, SQLite `:memory:` — estado zera a cada boot, nenhum arquivo de banco criado)
Versões: Node v24.19.0 / Express 4.22.1 (manifesto `^4.18.2`) / sqlite3 5.1.7 (manifesto `^5.1.6`)

Estado inicial (seed): users {1: Leonan}, courses {1: Clean Architecture 997, 2: Docker 497}, enrollments {1: user 1 → course 1}, payments {1: enrollment 1, 997, PAID}.

| # | Método | Path | Payload | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | /api/admin/financial-report | - | 200 | JSON lista de {course, revenue, students:[{student, paid}]} (2 itens; Clean Architecture revenue 997, students [Leonan 997]; Docker revenue 0, students []) — ordem dos cursos NÃO determinística |
| 2 | POST | /api/checkout | `{"usr":"X"}` | 400 | text/html `Bad Request` |
| 3 | POST | /api/checkout | `{usr,eml:"x@x.com",pwd,c_id:999,card:"4111"}` | 404 | text/html `Curso não encontrado` |
| 4 | POST | /api/checkout | `{usr:"João",eml:"joao@teste.com",pwd:"123",c_id:1,card:"5111222233334444"}` | 400 | text/html `Pagamento recusado` (mas o usuário João é criado: id 2) |
| 5 | POST | /api/checkout | `{usr:"Guilherme",eml:"gui@fullcycle.com.br",pwd:"senhaforte",c_id:2,card:"4111222233334444"}` | 200 | JSON `{"msg":"Sucesso","enrollment_id":2}` (novo usuário id 3) |
| 6 | POST | /api/checkout | `{usr:"Leonan",eml:"leonan@fullcycle.com.br",c_id:2,card:"4000000000000000"}` (usuário existente, sem pwd) | 200 | JSON `{"msg":"Sucesso","enrollment_id":3}` (reusa user id 1) |
| 7 | GET | /api/admin/financial-report | - | 200 | JSON lista; Clean Architecture revenue 997 [Leonan 997]; Docker revenue 994 [Guilherme 497, Leonan 497] |
| 8 | DELETE | /api/users/999 | - | 200 | text/html `Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.` (id inexistente também 200) |
| 9 | DELETE | /api/users/1 | - | 200 | text/html mesma mensagem |
| 10 | GET | /api/admin/financial-report | - | 200 | JSON lista; alunos do user 1 aparecem como `"student":"Unknown"` (matrículas/pagamentos órfãos) |
| 11 | GET | /api/unknown | - | 404 | HTML padrão Express `Cannot GET /api/unknown` |
| 12 | POST | /api/checkout | `{bad` (JSON malformado) | 400 | HTML padrão Express com stack trace completo (caminhos absolutos de node_modules) |
| 13 | POST | /api/checkout | `{usr:"N",eml:"n@n.com",c_id:1,card:4111}` (card numérico) | — (conexão fechada, curl 52) | **processo derruba**: `TypeError: cc.startsWith is not a function` em `src/AppManager.js:46` — servidor morre |

Observações:
- Sem warnings de deprecação no log.
- Log imprime número de cartão completo e a chave de gateway: `Processando cartão ****REDACTED**** na chave pk_live_****REDACTED****`.
- Rota `/api/admin/financial-report` e `DELETE /api/users/:id` sem qualquer autenticação.
- Pagamento recusado ainda cria usuário (sem transação); DELETE de usuário deixa matrículas/pagamentos órfãos.
- Respostas de erro são texto puro (`res.send`), sucesso é JSON; a ordem dos cursos no relatório varia entre execuções (callbacks concorrentes).
- Body JSON malformado vaza stack trace (Express sem error handler, NODE_ENV não definido).
- Reprodução: banco em memória — basta reiniciar o processo para voltar ao seed. Nenhum arquivo SQLite foi criado.
- Servidor do baseline parado (`kill`; `lsof -nP -iTCP:3101 -sTCP:LISTEN` vazio).
