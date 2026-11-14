================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js v24.19.0)
Framework:     Express ^4.18.2 (instalada 4.22.1)
Dependencies:  sqlite3 ^5.1.6 (instalada 5.1.7)
Domain:        LMS / e-commerce de cursos com checkout (users, courses, enrollments, payments, audit_logs)
Architecture:  Monolítica — 3 arquivos; a classe AppManager concentra conexão, schema/seed, rotas, SQL e regras de pagamento; utils.js mistura config com segredos, cache global e "crypto"
Source files:  3 files analyzed
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite :memory: via sqlite3, driver cru)
================================
Entry point: src/app.js (npm start) — porta 3000 hardcoded em src/utils.js:6
Rotas: 3 | Baseline: .refactor-arch/baseline.md (13 requisições)
