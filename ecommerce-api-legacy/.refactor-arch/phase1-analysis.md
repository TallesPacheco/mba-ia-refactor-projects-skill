================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js v24.19.0, CommonJS)
Framework:     Express ^4.18.2 (instalado 4.22.1)
Dependencies:  express ^4.18.2, sqlite3 ^5.1.6 (instalado 5.1.7); sem ORM, sem lib de CORS, sem lib de validação, sem lib de auth — crypto/util são do stdlib (`node:crypto`, `node:util`)
Domain:        LMS API com checkout (users, courses, enrollments, payments, audit_logs)
Architecture:  MVC em camadas — rotas finas com asyncHandler, controllers/services com a regra, models encapsulando SQL, config por env, app factory e error handler central (resultado da iteração 1 desta skill)
Source files:  27 files analyzed (~564 lines of code; nenhum arquivo de teste)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite via driver cru `sqlite3`, `:memory:` por default)
================================

Entry point: `src/app.js` (`"main"` e `"scripts.start"` do package.json) — comando de start original `npm start` → `node src/app.js`. Porta/host/caminho do banco vêm do ambiente (`PORT` default 3000, `HOST` default 127.0.0.1, `DB_PATH` default `:memory:`), sem valores hardcoded no código.
Composition root: `src/app.factory.js:24` (`createApp({ db, config, logger })`) — DI de models → services → controllers → rotas → middlewares.
Rotas encontradas: 3 (`POST /api/checkout` em src/routes/checkout.routes.js:6; `GET /api/admin/financial-report` em src/routes/admin.routes.js:6, com `requireAdmin`; `DELETE /api/users/:id` em src/routes/user.routes.js:6, com `requireAdmin`). Não há rota de login nem catch-all de 404.
Modo re-execução: `.refactor-arch/iteration-1/` já contém a evidência da execução anterior (sem arquivos de topo a arquivar). As "Remaining Known Issues" daquele `refactor-summary.md` serão verificadas uma a uma na Fase 2.
Baseline de runtime: `.refactor-arch/baseline.md` (19 requisições contra um único boot em `PORT=3101 npm start`, com e sem `X-Admin-Token`; servidor encerrado).
