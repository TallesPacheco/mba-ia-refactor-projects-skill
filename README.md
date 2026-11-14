# Desafio MBA — Skill `refactor-arch`: auditoria e refatoração arquitetural automatizada

Este repositório é a entrega do desafio "Criação de Skills — Refatoração Arquitetural Automatizada", feito a partir do repositório base [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill). Ele contém a skill `refactor-arch` para Claude Code (em `.claude/skills/refactor-arch/` dentro de cada projeto), o código dos três projetos legados já refatorado para MVC pela própria skill, os relatórios de auditoria da Fase 2 em `reports/` e, em cada projeto, a pasta `.refactor-arch/` com as evidências da execução (baseline de runtime, relatório, resumo da refatoração e logs). Depois da primeira execução, a skill foi melhorada e executada de novo pelo Claude Code CLI: os logs reais estão em `reports/cli-runs/` e os relatórios da segunda iteração em `reports/iteration-2/`. A skill analisa a stack, audita o código contra um catálogo de anti-patterns, pausa para confirmação humana e então refatora e valida a aplicação, sem depender de uma tecnologia específica.

## Sumário

- [A) Análise Manual](#a-análise-manual)
  - [Projeto 1 — code-smells-project (Python/Flask)](#projeto-1--code-smells-project-pythonflask)
  - [Projeto 2 — ecommerce-api-legacy (Node.js/Express)](#projeto-2--ecommerce-api-legacy-nodejsexpress)
  - [Projeto 3 — task-manager-api (Python/Flask)](#projeto-3--task-manager-api-pythonflask)
- [B) Construção da Skill](#b-construção-da-skill)
  - [Estrutura e decisões de design](#estrutura-e-decisões-de-design)
  - [Áreas de conhecimento → arquivos](#áreas-de-conhecimento--arquivos)
  - [Catálogo de anti-patterns](#catálogo-de-anti-patterns)
  - [APIs deprecated](#apis-deprecated)
  - [Playbook de refatoração](#playbook-de-refatoração)
  - [Agnosticismo de tecnologia](#agnosticismo-de-tecnologia)
  - [Desafios encontrados e soluções](#desafios-encontrados-e-soluções)
- [C) Resultados](#c-resultados)
  - [Resumo dos relatórios de auditoria](#resumo-dos-relatórios-de-auditoria)
  - [Execução real no Claude Code CLI sobre o código original (Fases 1–2)](#execução-real-no-claude-code-cli-sobre-o-código-original-fases-12)
  - [Iteração 2: re-execução via CLI sobre o código refatorado](#iteração-2-re-execução-via-cli-sobre-o-código-refatorado)
  - [Estrutura antes/depois](#estrutura-antesdepois)
  - [Checklists de validação](#checklists-de-validação)
  - [Logs da aplicação rodando após a refatoração](#logs-da-aplicação-rodando-após-a-refatoração)
  - [Comparação de endpoints (baseline × refatorado)](#comparação-de-endpoints-baseline--refatorado)
  - [Comportamento da skill em stacks diferentes](#comportamento-da-skill-em-stacks-diferentes)
  - [Nota de transparência sobre a execução](#nota-de-transparência-sobre-a-execução)
- [D) Como Executar](#d-como-executar)

---

## A) Análise Manual

Antes de escrever a skill, li o código dos três projetos e documentei os problemas. As linhas citadas se referem ao **código original** (commit inicial, `git show HEAD:<arquivo> | nl -ba`), não ao código refatorado. Comportamentos marcados com **[runtime]** foram reproduzidos subindo a aplicação original e chamando os endpoints com `curl`.

As tabelas abaixo mostram os achados de maior impacto de cada projeto. A análise completa encontrou 15 problemas no projeto 1, 16 no projeto 2 e 16 no projeto 3.

### Projeto 1 — code-smells-project (Python/Flask)

API de e-commerce (produtos, usuários, pedidos, relatórios) com Flask 3.1.1 e `sqlite3` puro, em 4 arquivos: `app.py`, `controllers.py`, `models.py` e `database.py`.

| # | Severidade | Problema | Arquivo:linha | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | SQL Injection por concatenação de strings | `models.py:28, 47-50, 109-111, 126-129, 289-297` | Login montado como `"... WHERE email = '" + email + "' AND senha = '" + senha + "'"`. **[runtime]** `POST /login` com `' OR 1=1 --` entrou como Admin, e um produto com nome `O'Reilly` gerou 500 com erro de sintaxe SQL. |
| 2 | CRITICAL | Endpoints admin sem autenticação, incluindo execução de SQL arbitrário | `app.py:47-57` (`/admin/reset-db`), `app.py:59-78` (`/admin/query`, `cursor.execute(query)` em `:69`) | Qualquer cliente pode ler todas as senhas ou apagar o banco. **[runtime]** `POST /admin/query` com `SELECT id, email, senha FROM usuarios` → 200 com as senhas. |
| 3 | CRITICAL | Segredo hardcoded, debug ligado e segredo exposto no `/health` | `app.py:7-8`, `app.py:88` (`host="0.0.0.0", debug=True`), `controllers.py:285-289` | `SECRET_KEY` versionada e devolvida em texto pelo `GET /health`. O debugger do Werkzeug fica exposto em todas as interfaces, o que permite execução remota de código. |
| 4 | CRITICAL | Senhas em texto puro, devolvidas pela API | `database.py:31, 75-83`, `models.py:83, 99, 126-129` | Não há hash. **[runtime]** `GET /usuarios/2` → `"senha":"123456"`. Expõe dados sensíveis (OWASP A02, LGPD). |
| 5 | HIGH | Regra de negócio espalhada entre model, controller e app (sem camada de serviço) | `models.py:133-169` (estoque e total), `models.py:256-262` (faixas de desconto), `controllers.py:208-210, 247-250` | Viola SRP/MVC: as regras não podem ser testadas isoladamente. O cancelamento promete devolver estoque, mas só executa um `print`. |
| 6 | HIGH | Conexão SQLite global compartilhada entre threads, sem DI | `database.py:4-11` (`global db_connection`, `check_same_thread=False`) | Estado global mutável compartilhado por todas as requisições. Abre espaço para condições de corrida e impede trocar o banco em testes (viola DIP). |
| 7 | HIGH | Criação de pedido não atômica e sem validar quantidade | `models.py:139-168`, `controllers.py:195-201` | **[runtime]** um pedido com `quantidade: -5` → 201 com total negativo, e o estoque *subiu*. Sem transação, uma falha no meio deixa o pedido incompleto. |
| 8 | MEDIUM | Consultas N+1 na listagem de pedidos | `models.py:171-201`, `models.py:203-233` | Faz 1 + N + N·M queries. A performance degrada conforme o volume de dados cresce. |
| 9 | MEDIUM | `except Exception` que devolve `str(e)` ao cliente | `controllers.py:10-12, 21-22, 60-62` (+14 blocos), `app.py:77-78` | Vaza detalhes internos (como a mensagem SQL que facilita o achado #1) e trata todo erro como 500. Não há handler central. |
| 10 | MEDIUM | CORS aberto para qualquer origem | `app.py:9` (`CORS(app)`) | Qualquer site pode chamar a API pelo navegador da vítima, inclusive as rotas `/admin/*`. |
| 11 | LOW | Números e strings mágicas | `controllers.py:52` (categorias), `controllers.py:242` (status), `models.py:257-262` (faixas 10000/5000/1000), `app.py:88` (porta) | Valores de domínio duplicados e sem nome, com risco de divergência. |
| 12 | LOW | `print()` como logging, incluindo PII | `controllers.py:8, 179, 182, 208-210`, `app.py:83-86` | Não há níveis nem destino configurável, e e-mails aparecem no stdout. |

### Projeto 2 — ecommerce-api-legacy (Node.js/Express)

LMS com fluxo de checkout (cursos, matrículas, pagamentos, relatório financeiro) em Express 4 e `sqlite3` em `:memory:`, distribuído em `src/app.js`, `src/AppManager.js` e `src/utils.js`.

| # | Severidade | Problema | Arquivo:linha | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | Credenciais e chave de pagamento hardcoded | `src/utils.js:1-7` (`dbPass` L3, `paymentGatewayKey` L4) | Senha de banco de "produção" e chave `pk_live_...` estão no repositório. Não dá para rotacioná-las sem deploy. |
| 2 | CRITICAL | Número de cartão e chave do gateway gravados em log | `src/AppManager.js:45` | **[runtime]** apareceu no log `Processando cartão 4111222233334444 na chave pk_live_...`. Viola PCI-DSS. |
| 3 | CRITICAL | Hash de senha caseiro e reversível, com senha padrão | `src/utils.js:17-23` (`badCrypto`), `src/AppManager.js:68` (`p \|\| "123456"`), `src/AppManager.js:18` (seed `'123'`) | O hash só depende dos 2 primeiros caracteres em Base64 e não tem salt. Um usuário criado sem senha recebe uma senha conhecida. |
| 4 | CRITICAL | God class `AppManager` | `src/AppManager.js:4-139` | Uma classe só cria a conexão, o schema e o seed, registra as rotas e implementa checkout, pagamento e relatório. Não é possível testar a regra sem Express e SQLite. |
| 5 | HIGH | Rota admin e DELETE sem autenticação | `src/AppManager.js:80` (`/api/admin/financial-report`), `src/AppManager.js:131` (`DELETE /api/users/:id`) | Expõe dados financeiros e pessoais e permite apagar usuários anonimamente (**[runtime]** 200 sem credenciais). |
| 6 | HIGH | Checkout sem transação | `src/AppManager.js:50-61`, `src/AppManager.js:69` | O usuário é criado antes da decisão de pagamento, e os INSERTs são independentes. Uma falha deixa matrícula sem pagamento ou usuários órfãos. |
| 7 | HIGH | Estado global mutável sem DI | `src/utils.js:9-10` (`globalCache`, `totalRevenue`), `src/AppManager.js:7` | O cache cresce sem limite (vazamento de memória) e a conexão é criada dentro do construtor, então não pode ser substituída por mock. |
| 8 | MEDIUM | Sem validação de entrada: uma requisição derruba o processo | `src/AppManager.js:29-35, 46` (`cc.startsWith`) | **[runtime]** `"card": 4111` (número) causa `TypeError` não capturado dentro do callback e **derruba o servidor**. É um DoS trivial. |
| 9 | MEDIUM | N+1 no relatório financeiro | `src/AppManager.js:83-127` | Executa 1 + C + 2E queries, com contadores manuais para sincronizar os callbacks. |
| 10 | MEDIUM | Callback hell / API callback do `sqlite3` (padrão obsoleto) | `src/AppManager.js:37-77` (5 níveis), `src/AppManager.js:83-127` | O fluxo é difícil de seguir, há risco de resposta dupla ou nunca enviada, e os erros não se propagam. |
| 11 | MEDIUM | Erros ignorados e nenhum error handler | `src/AppManager.js:57, 92-93, 104, 106, 133-135` | **[runtime]** JSON malformado devolve HTML com stack trace e o caminho absoluto do servidor. |
| 12 | LOW | Nomes crípticos | `src/AppManager.js:29-33` (`u`, `e`, `p`, `cid`, `cc`), `badCrypto` | Dificultam a leitura e a manutenção. |
| 13 | LOW | Magic numbers/strings e porta fixa | `src/AppManager.js:46` (`"4"` aprova), status `'PAID'`/`'DENIED'` repetidos, `src/utils.js:6` (`port: 3000`) | A regra de negócio fica escondida e a porta não é configurável (**[runtime]** a 3000 estava ocupada). |

### Projeto 3 — task-manager-api (Python/Flask)

Gerenciador de tarefas com Flask 3.0 e Flask-SQLAlchemy. Já tinha as pastas `models/`, `routes/`, `services/` e `utils/`, mas a separação existia só nas pastas: a regra de negócio estava nos handlers, e `services/notification_service.py` e `utils/helpers.py` não eram usados.

| # | Severidade | Problema | Arquivo:linha | Justificativa |
|---|---|---|---|---|
| 1 | CRITICAL | Segredos hardcoded | `app.py:13` (`SECRET_KEY`), `services/notification_service.py:7-10` (usuário e senha SMTP) | Os segredos vazam com o repositório, e a `SECRET_KEY` conhecida permite forjar sessões. |
| 2 | CRITICAL | Hash de senha devolvido nas respostas | `models/user.py:21` (`'password'` em `to_dict()`) | **[runtime]** `GET /users/1` → `"password":"81dc9bdb..."` (`md5("1234")`). |
| 3 | CRITICAL | MD5 sem salt para senhas, com mínimo de 4 caracteres | `models/user.py:27-32`, `routes/user_routes.py:64` | Hash rápido e sem salt cai com rainbow table, e a comparação com `==` não é em tempo constante. |
| 4 | CRITICAL | Autenticação e autorização inexistentes | `routes/user_routes.py:207-211` (`'fake-jwt-token-' + str(user.id)`), `:52`, `:119-122` | Qualquer cliente anônimo cria um admin, promove usuários ou apaga dados. O token de login nunca é validado. |
| 5 | CRITICAL | Debug ligado em `0.0.0.0` | `app.py:34` | Expõe o debugger do Werkzeug na rede. |
| 6 | HIGH | Regra de negócio nas rotas, camada de serviço não usada | `routes/task_routes.py:85-154, 156-223`, `routes/report_routes.py:12-101`, CRUD de categorias em `routes/report_routes.py:157-223` | Viola SRP/MVC e é a causa das duplicações (achado #9). |
| 7 | HIGH | Sem config/app factory e `create_all()` no import | `app.py:9-31` (`db.create_all()` em `:30-31`) | Não é possível ter config por ambiente nem banco de teste isolado, e o seed cria o schema como efeito colateral. |
| 8 | HIGH | `except:` sem tipo e 500 em HTML | `routes/task_routes.py:62` (+11), ponto de crash em `routes/task_routes.py:113` | **[runtime]** `"priority":"alta"` → 500 HTML com `TypeError`. Erros são engolidos e o contrato de erro fica inconsistente. |
| 9 | MEDIUM | Duplicação de regra | regra de atraso copiada 6×, por exemplo `routes/task_routes.py:30-39`, enquanto `Task.is_overdue()` (`models/task.py:50-60`) nunca é chamado | Uma mudança de regra exige editar 4 a 6 lugares, e as cópias já divergem. |
| 10 | MEDIUM | N+1 e agregações em Python | `routes/task_routes.py:41-57` (`User.query.get`/`Category.query.get` por task), `routes/report_routes.py:15-37, 53-68` | `GET /tasks` faz 1 + 2N queries e o summary faz cerca de 15 + N. |
| 11 | MEDIUM | APIs deprecated | `datetime.utcnow()` (22×, por exemplo `models/task.py:15-16`), `Model.query.get()` (16×, por exemplo `routes/task_routes.py:42`) | **[runtime]** 31 `DeprecationWarning` no Python 3.14 e 36 `LegacyAPIWarning` no SQLAlchemy 2.1.8. |
| 12 | LOW | Imports, dependências e código morto | `app.py:7` (`os, sys, json`), `requirements.txt` (`marshmallow`, `requests` não usados), `utils/helpers.py` sem uso | Gera ruído e a falsa impressão de que existe uma camada de validação. |
| 13 | LOW | Magic numbers/strings (as constantes existem e são ignoradas) | `routes/task_routes.py:110, 177` (status), `routes/user_routes.py:64` (senha 4), constantes em `utils/helpers.py:110-116` sem uso | Deixa a intenção obscura e cria risco de divergência. |

---

## B) Construção da Skill

A skill está em `<projeto>/.claude/skills/refactor-arch/`, com uma cópia idêntica em cada um dos 3 projetos. A igualdade foi verificada com `diff -r`, que não acusou nenhuma diferença.

```
.claude/skills/refactor-arch/
├── SKILL.md                              (174 linhas — prompt orquestrador)
└── references/
    ├── project-analysis.md               (242 linhas)
    ├── anti-patterns-catalog.md          (578 linhas)
    ├── report-template.md                (159 linhas)
    ├── mvc-guidelines.md                 (159 linhas)
    └── refactoring-playbook.md           (1106 linhas)
```

Esta é a versão final, já com a iteração descrita em [Desafios encontrados e soluções](#desafios-encontrados-e-soluções): catálogo AP-01…AP-26, playbook PB-01…PB-25 e modo re-execução no `SKILL.md`.

### Estrutura e decisões de design

1. **O `SKILL.md` só orquestra.** Ele define o propósito, as entradas, as 3 fases sequenciais (Análise → Auditoria → Refatoração), o que cada fase produz e como ela termina. Todo o conhecimento de domínio fica nos arquivos de referência.
2. **Progressive disclosure.** Uma tabela no topo diz *em que fase* cada referência deve ser lida, e cada fase começa com "Leia agora ...". O catálogo só entra no contexto na Fase 2, e o playbook e as guidelines só na Fase 3. Isso economiza contexto e evita que o agente comece a refatorar enquanto ainda está auditando.
3. **Baseline de runtime na Fase 1, usado como oráculo da Fase 3.** Antes de qualquer mudança, a skill instala as dependências num ambiente isolado, sobe a aplicação original, chama **todas** as rotas com `curl` (incluindo casos inválidos) e salva método/path/payload/status/shape em `.refactor-arch/baseline.md`. Na Fase 3, cada requisição do baseline é repetida e comparada. Assim "os endpoints continuam respondendo" vira um teste objetivo, e não uma impressão.
4. **Gate obrigatório com tabela de racionalizações.** A Fase 2 termina imprimindo exatamente `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e encerrando o turno. Para não dar brecha ao agente, o `SKILL.md` traz uma tabela "Racionalização × Realidade" (por exemplo, "Vou só criar a pasta `config/` adiantado" → "Criar arquivo no projeto é modificação. Pergunte.") e uma lista de red flags. Antes do `y`, só é permitido escrever em `.refactor-arch/`, `.venv/` e `node_modules/`.
5. **Saídas persistidas em `.refactor-arch/`.** `baseline.md`, `audit-report.md`, `refactor-summary.md` e os logs do servidor ficam no projeto, como evidência auditável. A skill não copia nada para `reports/` sozinha: ela só avisa que o relatório pode ser copiado.
6. **Validação em loop, com no máximo 3 iterações.** A Fase 3 restaura os dados iniciais, sobe a aplicação com o **comando de start original**, compara com o baseline, roda de novo os greps dos findings CRITICAL/HIGH e confere que os módulos antigos não são mais importados. O que não passar vai para "Remaining Known Issues", marcado com ✗.
7. **Linhas exatas.** Toda referência `arquivo:linha` precisa ser confirmada com `grep -n` ou `nl -ba` na mesma sessão. É proibido citar linhas de memória.
8. **Seções "Quick reference" e "Common mistakes"** reúnem as armadilhas reais encontradas durante as execuções (porta ocupada, binding do `sqlite3`, `utcnow()` × datetime aware, error handler do Express registrado antes das rotas, pacote `app/` ao lado de `app.py`).
9. **Modo re-execução.** Se `.refactor-arch/` já existe, a skill move só os arquivos de topo dessa pasta para `.refactor-arch/iteration-<n>/` (n = próximo inteiro livre) antes de gravar qualquer coisa. Assim a evidência anterior nunca é sobrescrita. Quando o projeto já foi refatorado, a Fase 2 também precisa verificar cada item da seção "Remaining Known Issues" do `refactor-summary.md` anterior. Sobrescrever a pasta em vez de arquivá-la aparece na lista de red flags.

### Áreas de conhecimento → arquivos

| Área de conhecimento obrigatória | Arquivo | Conteúdo |
|---|---|---|
| Análise de projeto | `references/project-analysis.md` | Escopo de contagem, detecção de linguagem por manifesto (Python, Node, Go, Java, Ruby, PHP, C#, Rust), framework e versão (manifesto + import), banco/ORM, inferência de domínio, entry point, classificação de arquitetura (monolito / camadas parciais / em camadas), enumeração de rotas por framework (Flask, FastAPI, Django, Express, NestJS, Spring, Rails, Laravel, Go) e roteiro do baseline de runtime (§9) |
| Catálogo de anti-patterns | `references/anti-patterns-catalog.md` | Escala de severidade do desafio + regras de ajuste, 26 anti-patterns (AP-01 a AP-26) com descrição, greps de detecção por stack, falsos positivos, exemplo e PB de correção, e uma seção de APIs deprecated |
| Template de relatório | `references/report-template.md` | Formato exato dos blocos `PHASE 1: PROJECT ANALYSIS`, `ARCHITECTURE AUDIT REPORT` e `PHASE 3: REFACTORING COMPLETE`, além das regras do relatório (ordenação, linhas exatas, um finding por causa raiz, Summary igual aos blocos, evidência de runtime) |
| Guidelines de arquitetura | `references/mvc-guidelines.md` | Responsabilidades de cada camada (Config, Models, Services, Controllers, Views/Routes, Middlewares, Composition root), regras de dependência, convenções de nomes, árvores por stack (Flask, Express, genérica) e estratégia de adaptação ao nível de arquitetura atual (§5) |
| Playbook de refatoração | `references/refactoring-playbook.md` | 25 padrões (PB-01 a PB-25) com código antes/depois e as "Regras de preservação de comportamento" |

### Catálogo de anti-patterns

| ID | Anti-pattern | Severidade |
|---|---|---|
| AP-01 | Credenciais / segredos hardcoded (inclui senhas de seed/fixture) | CRITICAL |
| AP-02 | SQL Injection (concatenação / f-string / template literal) | CRITICAL |
| AP-03 | God Class / God File | CRITICAL |
| AP-04 | Exposição de dados sensíveis | CRITICAL |
| AP-05 | Hash de senha fraco, caseiro ou ausente | CRITICAL |
| AP-06 | Endpoints administrativos/destrutivos sem autenticação/autorização | CRITICAL |
| AP-07 | Debug ligado / bind em 0.0.0.0 no entry point | CRITICAL |
| AP-08 | Regra de negócio dentro de rotas/controllers | HIGH |
| AP-09 | Estado global mutável / conexão compartilhada sem DI | HIGH |
| AP-10 | Escritas multi-etapa sem transação | HIGH |
| AP-11 | Sem módulo de config / app factory; efeitos colaterais no import | HIGH |
| AP-12 | Erros engolidos, `except` genérico, sem error handler central (inclui 404/405 de rota inexistente fora do handler), stack trace vazado | MEDIUM |
| AP-13 | Queries N+1 / agregação em memória | MEDIUM |
| AP-14 | Validação de entrada ausente | MEDIUM |
| AP-15 | Código duplicado | MEDIUM |
| AP-16 | Callback hell | MEDIUM |
| AP-17 | APIs deprecated | MEDIUM |
| AP-18 | Middleware mal configurado (CORS aberto, sem middleware de auth/erro) | MEDIUM |
| AP-19 | Integridade referencial ausente / cascata manual | MEDIUM |
| AP-20 | Magic numbers / strings | LOW |
| AP-21 | Nomenclatura ruim / sombreamento de builtins | LOW |
| AP-22 | `print` / `console.log` como logging | LOW |
| AP-23 | Imports não usados / código morto / dependências não usadas | LOW |
| AP-24 | Token de autenticação previsível / não assinado / nunca verificado (ex.: login) | CRITICAL |
| AP-25 | PII listada em endpoint sem autenticação | HIGH |
| AP-26 | Mensagem de resposta que contradiz o comportamento real | LOW |

Totais por severidade: **CRITICAL 8** (AP-01…07, AP-24), **HIGH 5** (AP-08…11, AP-25), **MEDIUM 8** (AP-12…19) e **LOW 5** (AP-20…23, AP-26), num total de 26 entradas. Os IDs AP-24 a AP-26 foram acrescentados na iteração da skill e mantêm a numeração anterior estável. No relatório, os findings são ordenados por severidade e, dentro dela, por ID.

**Por que estes.** O catálogo nasceu da análise manual: cada problema recorrente nos 3 projetos virou uma entrada **genérica**, descrita pelo sinal que a identifica e não pelo arquivo onde apareceu. A distribuição segue a escala do desafio: segurança e God Class em CRITICAL, violações de MVC/SOLID (regra em controller, estado global, ausência de DI e de factory) em HIGH, padronização e performance em MEDIUM, legibilidade em LOW. A regra de ajuste permite **subir** um nível quando há impacto comprovado (por exemplo, falta de validação que derruba o processo → HIGH) e proíbe rebaixar um item de segurança comprovado. Cada entrada traz um grep e exige confirmação por leitura, porque grep sozinho gera falso positivo. As três entradas novas vieram da revisão da primeira execução (ver [Desafios](#desafios-encontrados-e-soluções)). O AP-24 procura tokens montados por concatenação e também a ausência de qualquer consumidor do header `Authorization`. O AP-25 cruza a tabela de rotas da Fase 1 com os campos pessoais serializados. Ele sobe para CRITICAL quando a resposta também traz credencial. O AP-26 manda repetir a checagem das mensagens **depois** da Fase 3, porque uma correção pode tornar falsa uma mensagem antiga.

### APIs deprecated

O catálogo tem uma seção própria, com tabelas *API deprecated → equivalente moderno → grep de detecção*:

- **Python / Flask / SQLAlchemy:** `datetime.utcnow()`/`utcfromtimestamp()`, `Model.query.get()`, Query API legada (`Model.query.filter_by...`), `get_or_404`/`first_or_404` legados, `@before_first_request`, `JSONEncoder`/`json_encoder`, `_app_ctx_stack`, `attachment_filename`, `hashlib.md5/sha1/sha256` para senha, `ext.declarative`, `engine.execute()`, `type(x) == list`.
- **Node.js / Express:** `new Buffer()`, `crypto.createCipher`, `url.parse`, `body-parser`, API callback do `sqlite3`, `var`, `fs.exists`, `req.param()`, `res.send(status, body)`, `res.sendfile`, `app.del`, `querystring`, `util.isX`, `createHash('md5'|'sha1')` para senha.
- **Outras stacks (referência rápida):** Django, Java/Spring, Go e PHP.

Todas as ocorrências são agregadas num único finding "Deprecated APIs (AP-17)". Quando nenhuma é encontrada, o relatório registra a linha `Deprecated APIs: nenhuma ocorrência encontrada (greps: ...)`, que foi o que aconteceu no projeto 1. Os greps são cruzados com os warnings que aparecem no log do baseline.

### Playbook de refatoração

| PB | Padrão | Resolve |
|---|---|---|
| PB-01 | Extrair config para variáveis de ambiente | AP-01, AP-07, AP-11 |
| PB-02 | Queries parametrizadas | AP-02 |
| PB-03 | Quebrar God class em model / controller / route | AP-03 |
| PB-04 | Controller fino + service para regra de negócio | AP-08 |
| PB-05 | Hash de senha forte (werkzeug / bcrypt / scrypt) | AP-05 |
| PB-06 | Remover dados sensíveis de respostas e logs | AP-04 |
| PB-07 | Middleware/decorator de auth em rotas admin/destrutivas | AP-06 |
| PB-08 | Error handler centralizado + exceções de domínio | AP-12 |
| PB-09 | Transação em escritas multi-etapa | AP-10 |
| PB-10 | Eliminar N+1 (JOIN / IN / eager loading / GROUP BY) | AP-13 |
| PB-11 | Camada de validação de entrada | AP-14 |
| PB-12 | Callback → async/await (wrapper Promise do sqlite3) | AP-16 |
| PB-13 | Substituir APIs deprecated | AP-17 |
| PB-14 | Magic numbers → constantes / enums | AP-20 |
| PB-15 | Logging no lugar de print / console.log | AP-22 |
| PB-16 | App factory / composition root | AP-07, AP-11 |
| PB-17 | Conexão por requisição / injeção de dependência | AP-09 |
| PB-18 | DRY, código morto e nomes | AP-15, AP-21, AP-23 |
| PB-19 | Configurar CORS e middlewares | AP-18 |
| PB-20 | Integridade referencial | AP-19 |
| PB-21 | Token de login assinado e com expiração + `require_auth` | AP-24 |
| PB-22 | Proteger listagens/detalhes com PII | AP-25 |
| PB-23 | Catch-all 404/405 → error handler central | AP-12 |
| PB-24 | Corrigir mensagens de resposta enganosas | AP-26 |
| PB-25 | Senhas de seed/fixture vindas do ambiente | AP-01 |

Cada padrão tem exemplos ANTES/DEPOIS em Python e/ou JavaScript. O arquivo termina com as **Regras de preservação de comportamento**: os mesmos paths, métodos, parâmetros, status e shapes para requisições válidas. Mudanças só são permitidas "na direção segura" e precisam ser documentadas: remover campos sensíveis, exigir auth em rota admin com token de dev documentado, transformar 500 em 400/404/422 e restringir endpoints perigosos. Depois da iteração, também entram nessa lista: exigir auth em endpoints com PII (PB-22), trocar o valor do token de login por um token assinado mantendo o nome e o tipo do campo (PB-21), responder rotas inexistentes pelo handler central (PB-23) e corrigir o texto de uma mensagem que ficou falsa, sem mudar status nem shape (PB-24). O seed e o comando de start continuam funcionando, os campos do contrato não são renomeados e nenhuma feature nova é adicionada.

### Agnosticismo de tecnologia

- **Heurísticas genéricas, com tabelas de dicas por stack.** Cada passo é descrito de forma neutra ("SQL montado como string em vez de placeholders") e acompanhado de tabelas com o comando ou grep de cada stack (Flask, Express, Django, FastAPI, Spring, Rails, Laravel, Go...). O agente escolhe a linha da stack detectada na Fase 1.
- **Nenhum nome específico dos projetos.** Os exemplos do catálogo e do playbook usam entidades genéricas (`users`, `products`, `orders`), e as convenções exigem usar os nomes de entidade **na língua do código original**. Por isso o projeto 1 ficou com `produto_model.py` e o projeto 2 com `course.model.js`.
- **Adaptação ao nível de arquitetura** (`mvc-guidelines.md` §5): **monolito → split completo** (projetos 1 e 2) e **camadas parciais → incremental** (projeto 3). No modo incremental, a skill preserva o que funciona (modelos ORM, blueprints com as URLs certas), insere controllers e services, reaproveita o código existente que não era usado (por exemplo, `Task.is_overdue()` virou a fonte única da regra de atraso) e move código fora do lugar (o CRUD de categorias saiu de `report_routes.py` para `category_routes.py`, com os mesmos paths).
- **Camada "View" numa API.** As guidelines definem que, numa API, a View é a camada de rotas + serialização JSON. O projeto 1 usa `views/`, o 2 usa `routes/` (convenção do Express) e o 3 manteve o pacote `routes/` que já existia, como pede a estratégia incremental.
- **Prova prática.** A mesma cópia da skill, sem nenhuma alteração por projeto, rodou em Flask com `sqlite3` puro, Express com `sqlite3` callback/`:memory:` e Flask-SQLAlchemy. Isso vale para as duas iterações e para as execuções via CLI sobre o código original.

### Desafios encontrados e soluções

| Desafio | Solução |
|---|---|
| **Ambiente Python 3.14.** Os projetos fixam versões antigas (Flask 3.0.0), que resolveram SQLAlchemy 2.1.8 como dependência transitiva. No 3.14, `utcnow()` e `Query.get()` passaram a emitir warnings reais. | A skill instala as dependências em `.venv` isolado e sobe o baseline com `-W default`/`PYTHONWARNINGS=default`, o que transforma os warnings em evidência de runtime para o AP-17 (31 `DeprecationWarning` e 36 `LegacyAPIWarning` no projeto 3). Na validação final, o log não tem nenhum warning. |
| **Binding nativo do `sqlite3` ausente após `npm install`** (projeto 2). | Resolvido com `cd node_modules/sqlite3 && npx prebuild-install -r napi`. A correção foi incorporada à Fase 1 e ao "Quick reference" do `SKILL.md`. |
| **Porta 3000 ocupada pelo Docker, e portas/debug hardcoded** (`port: 3000`, `app.run(host='0.0.0.0', debug=True)`). | Sem editar arquivos, o baseline sobe pela CLI do framework (`flask --app app run --host 127.0.0.1 --port <p>`) ou por um wrapper (`node -e "require('./src/utils').config.port=3101; require('./src/app')"`). Na Fase 3, a porta passou a ser configurável por `PORT`, com o mesmo default de antes. |
| **O grep do catálogo para a API callback do `sqlite3` usava `[^)]*` e não casava**, porque o SQL dentro da chamada contém `)`. Isso apareceu na execução do projeto 2: o agente usou um grep alternativo e registrou isso no relatório. | **Iteração da skill:** o padrão foi trocado por `.*` nas 3 cópias, com uma nota explicando o motivo. |
| **Trocar `utcnow()` por datetime *aware* quebra comparações** com colunas *naive* do SQLite (`TypeError`) e muda o formato serializado (`+00:00`). | O playbook (PB-13) avisa sobre isso e oferece um helper de UTC *naive*, e o item entrou em "Common mistakes". O projeto 3 usa `utils.helpers.utcnow()`, que mantém o mesmo formato de resposta. |
| **Adicionar auth às rotas admin sem quebrar o critério "endpoints originais respondem".** | Na primeira execução, a auth usou o header `X-Admin-Token` com default de dev `dev-admin-token`, documentado em `.env.example`, no README do projeto e no bloco da Fase 3. A validação testa 401 sem token ou com token errado e sucesso com o token. Estado atual, depois da iteração 2: nos projetos 1 e 3 o default de dev continua no `.env.example`. Ele é recusado no boot fora de `development`/`test` (P1) ou em `APP_ENV=production` (P3). No projeto 2 não há mais default no código: sem `ADMIN_TOKEN`, um token aleatório é gerado a cada boot e registrado no log, e em `APP_ENV=production` o boot falha. Nos projetos 1 e 3, o token de usuário assinado (`Authorization: Bearer`) complementa o token de admin. |
| **Corrigir segurança mantendo o comportamento** (mesmos paths, métodos e shapes). | As regras de preservação do playbook e a tabela de comparação foram aplicadas a cada requisição. As diferenças aparecem como `≈`, com justificativa (por exemplo, campo `senha` removido, ou 500 → 400). Rotas perigosas foram **protegidas, não removidas**: `/admin/query` passou a exigir admin e a aceitar só SELECT numa conexão read-only. |
| **Ordem não determinística no relatório financeiro (Node).** A ordem dos cursos dependia da ordem em que os callbacks terminavam, então duas execuções do baseline deram resultados diferentes. | A comparação com o baseline foi feita por valores, e não por posição. O refatorado usa uma única query com `ORDER BY c.id, e.id`, e a ordem agora é determinística. |
| **A primeira execução deixou pendências que o catálogo não cobria.** A revisão dos resultados mostrou: PII em `GET /usuarios/<id>` (P1) e `GET /users*` (P3) sem autenticação; login sem token (P1) ou com `fake-jwt-token-<id>` nunca validado (P3); 404 de rota inexistente em HTML no P2; mensagem do DELETE do P2 que afirmava "dados sujos" depois de a cascata ter sido corrigida; e senhas de seed literais no código. | **Iteração da skill:** o catálogo ganhou AP-24 (token previsível, CRITICAL), AP-25 (PII sem auth, HIGH) e AP-26 (mensagem que contradiz o comportamento, LOW). O AP-01 passou a cobrir senhas de seed/fixture e o AP-12 o 404/405 de rota desconhecida. O playbook ganhou PB-21 a PB-25. A iteração 2, executada via CLI, corrigiu esses pontos nos 3 projetos (ver [Iteração 2](#iteração-2-re-execução-via-cli-sobre-o-código-refatorado)). |
| **Rodar a skill de novo apagaria a evidência da primeira execução** em `.refactor-arch/`. | Foi criado o modo re-execução no `SKILL.md`: os arquivos de topo vão para `.refactor-arch/iteration-<n>/`. Na iteração 2, a primeira execução ficou preservada em `iteration-1/` nos 3 projetos. |
| **Token de admin de dev repetido no `.env.example` do P2.** O finding AP-01 da iteração 2 citava a própria cópia do token literal no `.env.example`. | O `.env.example` do P2 passou a trazer só placeholders. Os valores de dev usados na validação (`ADMIN_TOKEN=dev-admin-token`, `SEED_USER_PASSWORD=123`) estão registrados em `.refactor-arch/refactor-summary.md` e na seção [D](#d-como-executar). |
| **Corrida no smoke test: seed + boot levam alguns segundos**, e um `curl` disparado logo depois do start encontrava a porta ainda fechada. | O smoke test independente espera a aplicação ficar pronta (porta respondendo) antes de chamar os endpoints. |

---

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | Stack detectada | Arquivos | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---|---|---|---|---|---|---|
| 1 — code-smells-project | Python 3.14 + Flask 3.1.1 | 4 (~780 LOC) | 7 | 4 | 6 | 4 | **21** |
| 2 — ecommerce-api-legacy | Node.js v24.19.0 + Express 4.22.1 | 3 (~180 LOC) | 6 | 5 | 5 | 4 | **20** |
| 3 — task-manager-api | Python 3.14 + Flask 3.0.0 / Flask-SQLAlchemy 3.1.1 | 15 (~1158 LOC) | 5 | 3 | 7 | 4 | **19** |

Os números vêm das linhas `Summary` e `Total` de [`reports/audit-project-1.md`](reports/audit-project-1.md), [`reports/audit-project-2.md`](reports/audit-project-2.md) e [`reports/audit-project-3.md`](reports/audit-project-3.md), e batem com a contagem dos blocos `### [...]` de cada arquivo. Os problemas da análise manual (seção A) aparecem nos relatórios. Por exemplo, no projeto 1: SQL Injection (AP-02), endpoints admin sem auth (AP-06), segredo hardcoded (AP-01), senha sem hash (AP-05), N+1 (AP-13), CORS aberto (AP-18), magic numbers (AP-20) e `print` (AP-22). Os relatórios também trazem achados que a análise manual não destacou, como a integridade referencial (AP-19) nos 3 projetos.

Estes três relatórios continuam sendo a entrega oficial da Fase 2: eles foram gerados na primeira execução, sobre o código original, com a versão da skill de então (AP-01…AP-23). As duas subseções a seguir registram as execuções posteriores, feitas com a skill final.

### Execução real no Claude Code CLI sobre o código original (Fases 1–2)

Para mostrar o fluxo pelo CLI de verdade, sem subagentes, a skill final foi executada com `claude -p "/refactor-arch"` em **cópias limpas do código original** (extraídas do commit inicial, `git HEAD`). Os logs estão em `reports/cli-runs/project-{1,2,3}-original-phases-1-2.log`. Eles trazem os textos do assistente e as chamadas de ferramenta, resumidas a partir do `stream-json`.

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Fim do log |
|---|---|---|---|---|---|---|
| 1 — code-smells-project | 8 | 4 | 7 | 4 | **23** | `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` |
| 2 — ecommerce-api-legacy | 6 | 6 | 5 | 4 | **21** | idem |
| 3 — task-manager-api | 8 | 4 | 7 | 5 | **24** | idem |

- **O gate funcionou.** As três execuções pararam na pergunta `[y/n]`. Cada log termina com o `git status --short` da cópia, que mostra só arquivos não versionados: os de `.refactor-arch/` e artefatos de runtime gerados ao subir a aplicação original no baseline, ou seja, o cache de bytecode `__pycache__/` e, no projeto 3, o `instance/tasks.db` criado pelo `create_all()` no import. Nenhum arquivo versionado foi modificado antes da confirmação.
- **O catálogo novo apareceu.** Comparando os IDs com os relatórios oficiais: no projeto 1 surgiram AP-25 (CRITICAL; a descrição registra que a resposta também trazia a senha) e AP-26 (MEDIUM). No projeto 2 surgiu AP-26 (MEDIUM), e três severidades foram classificadas de outra forma (AP-12 e AP-19 subiram para HIGH, AP-14 ficou em MEDIUM). No projeto 3 surgiram AP-24 (`fake-jwt-token-<id>`), AP-25 (ambos CRITICAL) e AP-26 (LOW), além de AP-03 e AP-09, que a primeira execução não tinha registrado. Essas diferenças explicam os totais maiores que os da tabela anterior. Elas também mostram que a classificação de severidade varia um pouco entre execuções.
- **Limite.** Essas cópias **não foram refatoradas**: o objetivo era só demonstrar o fluxo do CLI até o gate. O código refatorado deste repositório vem da primeira execução mais a iteração 2.

### Iteração 2: re-execução via CLI sobre o código refatorado

A skill final foi executada de novo, pelo CLI, sobre os projetos **já refatorados**, em dois turnos não interativos:

1. `claude -p "/refactor-arch"`: Fases 1 e 2, até o gate;
2. `claude -p "y" --resume <session-id>`: confirmação e Fase 3, na mesma sessão.

Os logs estão em `reports/cli-runs/project-{1,2,3}-iteration-2.log`, e os relatórios da Fase 2 em `reports/iteration-2/audit-project-{1,2,3}.md`. Em cada projeto, os arquivos de topo de `.refactor-arch/` são a iteração 2, e `.refactor-arch/iteration-1/` guarda a primeira execução, arquivada pelo modo re-execução.

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Findings |
|---|---|---|---|---|---|---|
| 1 — code-smells-project | 2 | 3 | 2 | 3 | **10** | AP-01 (senhas de seed e fallbacks), AP-24 (login sem token), AP-06, AP-11, AP-25, AP-14, AP-19, AP-21, AP-23, AP-26 |
| 2 — ecommerce-api-legacy | 1 | 1 | 3 | 2 | **7** | AP-01 (token de admin de dev e senha de seed), AP-10, AP-12 (sem catch-all 404/405), AP-14, AP-26 (mensagem do DELETE), AP-21, AP-23 |
| 3 — task-manager-api | 3 | 1 | 3 | 1 | **8** | AP-01 (senhas de seed), AP-06 (takeover anônimo via `PUT /users/<id>`), AP-24 (`fake-jwt`), AP-25, AP-13, AP-14, AP-15, AP-23 |

O que a Fase 3 da iteração 2 corrigiu, segundo cada `.refactor-arch/refactor-summary.md`:

- **Projeto 1.** O login passou a devolver um token assinado (HMAC via `itsdangerous.URLSafeTimedSerializer` sobre `SECRET_KEY`), que expira em `TOKEN_MAX_AGE` (default 3600 s). `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` e `POST /pedidos` passaram a exigir `Authorization: Bearer <token>` do dono ou `X-Admin-Token`: 401 sem credencial, 403 com o token de outro usuário. As senhas do seed vêm de `SEED_ADMIN_PASSWORD`/`SEED_JOAO_PASSWORD`/`SEED_MARIA_PASSWORD`. Sem elas, o seed gera senhas aleatórias e as registra uma vez no log. `app = create_app()` saiu do nível de módulo. 404/405 respondem em português pelo handler central. Validação: 73/73 requisições, nenhuma divergência não intencional.
- **Projeto 2.** Foi criado um catch-all 404/405 no formato da API (`Rota não encontrada: GET /api/unknown`; 405 com header `Allow`). A mensagem do DELETE virou `Usuário deletado, junto com suas matrículas e pagamentos.`. O default `dev-admin-token` saiu do código: sem `ADMIN_TOKEN`, um token aleatório é gerado a cada boot e registrado no log, e em `APP_ENV=production` o boot falha. A senha do seed vem de `SEED_USER_PASSWORD`. `DELETE /api/users/:id` passou a validar o id. A escrita avulsa entrou na fila de transação (`db.write`). Validação: 19/19 requisições do baseline com o mesmo status.
- **Projeto 3.** O login passou a devolver um token assinado e com expiração (`itsdangerous`), validado por `require_auth`. O prefixo `fake-jwt-token-` foi removido. `GET /users`, `GET /reports/summary` e as rotas de escrita de tasks e categorias exigem credencial. `GET/PUT /users/<id>`, `GET /users/<id>/tasks` e `GET /reports/user/<id>` exigem o token do próprio usuário ou `X-Admin-Token`, o que fechou o takeover anônimo de conta. As senhas do seed vêm de `SEED_*_PASSWORD`, sem fallback literal. O relatório por usuário passou a usar uma consulta agregada. Validação: 80 requisições (as 63 do baseline com credencial + 17 checagens novas), nenhum 500.

Pendências que os resumos da iteração 2 ainda listam em "Remaining Known Issues":

- **Projeto 1:** o token não tem revogação/logout e é determinístico dentro do mesmo segundo; a coluna `usuarios.tipo` não é usada para autorização (admin vem só do `X-Admin-Token`); não há limite de tentativas no login; `POST /admin/query` continua devolvendo os hashes de senha para admin (contrato preservado); cancelar um pedido não devolve estoque (comportamento original); `itens_pedido.produto_id` não tem FK; um `loja.db` antigo precisa ser recriado; não há testes automatizados.
- **Projeto 2:** `DELETE` de um id bem formado mas inexistente continua respondendo 200; os campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) foram mantidos; a coluna `users.pass` só é gravada, porque não existe login; os erros continuam em texto com `Content-Type: text/html`; o gateway é simulado; não há testes automatizados; o 405 depende de cada arquivo de rota declarar `router.all`.
- **Projeto 3:** `/health` continua em hora local (AP-15 parcial, por ser valor observável do contrato); a troca de senha não pede a senha atual; o token não tem revogação; um usuário não-admin recebe 403, e não 404, para id inexistente; o `X-Admin-Token` não identifica usuário; `GET /tasks*` continua público e expõe `user_name`; um banco antigo precisa ser recriado; a busca `LIKE` não escapa `%`/`_`.

### Estrutura antes/depois

Árvores geradas com `git ls-tree -r --name-only HEAD <projeto>` (antes) e `find` no working tree (depois), excluindo `.venv`, `node_modules`, `__pycache__`, `.claude`, `.refactor-arch`, `instance` e `*.db`. O "depois" é o estado atual, após a iteração 2. Nessa iteração, a skill tratou os 3 projetos como "já em camadas" e só fez correções pontuais. Nos projetos 1 e 3 nenhum arquivo foi movido. No projeto 2 foram criados `src/middlewares/notFound.js` e `src/validators/user.validator.js`.

#### Projeto 1 — code-smells-project (monolito → split completo)

```
ANTES                                   DEPOIS
code-smells-project/                    code-smells-project/
├── README.md                           ├── .env.example
├── app.py                              ├── app.py                 (composition root: create_app(), sem app em nível de módulo)
├── controllers.py                      ├── errors.py              (exceções de domínio, incl. 403)
├── database.py                         ├── config/                __init__.py, settings.py
├── models.py                           ├── db/                    __init__.py, connection.py, schema.py (seed com senhas do env)
└── requirements.txt                    ├── models/                admin, pedido, produto, usuario (_model.py) + constants
                                        ├── services/              notification, pedido, relatorio, usuario (_service.py)
                                        ├── controllers/           admin, health, pedido, produto, relatorio, usuario (_controller.py)
                                        ├── validators/            common, pedido, produto, usuario (_validator.py)
                                        ├── views/                 admin, main, pedido, produto, relatorio, usuario (_routes.py)
                                        ├── middlewares/           auth.py (token assinado, require_auth/require_admin), error_handler.py
                                        ├── README.md
                                        └── requirements.txt       (inalterado)
```

Os arquivos `controllers.py`, `models.py` e `database.py` foram apagados depois da migração.

#### Projeto 2 — ecommerce-api-legacy (God class → split completo)

```
ANTES                                   DEPOIS
ecommerce-api-legacy/                   ecommerce-api-legacy/
├── README.md                           ├── .env.example, README.md, api.http, package.json ("start" inalterado)
├── api.http                            └── src/
├── package.json / package-lock.json        ├── app.js               (entry point: config → db + schema/seed → createApp → listen)
└── src/                                    ├── app.factory.js       (composition root com DI)
    ├── app.js                              ├── config/index.js
    ├── AppManager.js                       ├── db/connection.js (wrapper Promise + withTransaction), schema.js
    └── utils.js                            ├── models/              auditLog, course, enrollment, payment, user + constants
                                            ├── services/            checkout, financialReport, paymentGateway
                                            ├── controllers/         admin, checkout, user
                                            ├── routes/              admin, checkout, user (.routes.js)
                                            ├── middlewares/         asyncHandler, auth, errorHandler, notFound (catch-all 404/405)
                                            ├── errors/AppError.js
                                            ├── validators/          checkout.validator.js, user.validator.js
                                            └── utils/               logger.js, password.js (scrypt + salt)
```

Os arquivos `src/AppManager.js` e `src/utils.js` foram apagados.

#### Projeto 3 — task-manager-api (camadas parciais → incremental)

```
ANTES                                   DEPOIS
task-manager-api/                       task-manager-api/
├── README.md                           ├── .env.example, README.md
├── app.py                              ├── app.py                 (create_app() + app = create_app())
├── database.py                         ├── config/                (novo) __init__.py, settings.py
├── seed.py                             ├── database.py            (init_db, PRAGMA foreign_keys, commit transacional)
├── requirements.txt                    ├── errors.py              (novo)
├── models/                             ├── seed.py                (transação única, senhas vindas de SEED_*_PASSWORD)
│   ├── category.py                     ├── requirements.txt       (sem marshmallow/requests)
│   ├── task.py                         ├── models/                category, task, user + constants.py (novo)
│   └── user.py                         ├── validators/            (novo) common, category, task, user
├── routes/                             ├── services/              (novo conteúdo) category, report, task, user
│   ├── report_routes.py                ├── controllers/           (novo) category, report, task, user
│   ├── task_routes.py                  ├── routes/                category_routes.py (novo), report, system (novo), task, user
│   └── user_routes.py                  ├── middlewares/           (novo) auth.py (token assinado, require_auth), error_handler.py
├── services/                           └── utils/helpers.py       (reduzido a utcnow, localnow, calculate_percentage, format_datetime)
│   └── notification_service.py
└── utils/
    └── helpers.py
```

Os modelos ORM e os blueprints existentes foram preservados. O arquivo `services/notification_service.py`, que nunca era importado, foi apagado. O CRUD de categorias saiu de `report_routes.py` para `category_routes.py`, com os mesmos paths.

### Checklists de validação

As checklists mostram o estado atual. Os itens das Fases 1 e 2 se referem à auditoria oficial sobre o código original (`reports/audit-project-N.md`), confirmada depois pela execução via CLI sobre o código original. Os itens da Fase 3 se referem ao código depois da iteração 2. As evidências estão em `<projeto>/.refactor-arch/` (iteração 2 no topo e primeira execução em `iteration-1/`), em `reports/`, em `reports/cli-runs/` e no smoke test independente da próxima seção.

#### Projeto 1 — code-smells-project

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python 3.14)
- [x] Framework detectado corretamente (Flask 3.1.1 + flask-cors 5.0.1, sqlite3 stdlib)
- [x] Domínio da aplicação descrito corretamente (e-commerce: produtos, usuários, pedidos, relatórios)
- [x] Número de arquivos analisados condiz com a realidade (4 arquivos-fonte: app.py, controllers.py, models.py, database.py)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (21 na auditoria oficial; 23 na execução via CLI com a skill final)
- [x] Detecção de APIs deprecated incluída (se aplicável) — nenhuma ocorrência; o relatório lista os greps executados
- [x] Skill pausa e pede confirmação antes da Fase 3 (também no CLI real: logs em reports/cli-runs/)

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (models/, views/, controllers/ + services/, validators/)
- [x] Configuração extraída para módulo de config (config/settings.py + .env.example; senhas do seed vêm de SEED_*)
- [x] Models criados para abstrair dados (models/*_model.py, queries parametrizadas)
- [x] Views/Routes separadas para visualização ou roteamento (views/*_routes.py)
- [x] Controllers concentram o fluxo da aplicação (controllers/*_controller.py)
- [x] Error handling centralizado (middlewares/error_handler.py + errors.py; 404/405 em JSON)
- [x] Entry point claro (app.py → create_app())
- [x] Aplicação inicia sem erros (python app.py; log sem traceback nem DeprecationWarning)
- [x] Endpoints originais respondem corretamente (iteração 2: 73/73 requisições; diferenças só nas mudanças de segurança documentadas)
```

Pendências resolvidas na iteração 2: o login agora emite um token assinado e com expiração, e `GET /usuarios/<id>` e `GET /pedidos/usuario/<id>` exigem o token do dono ou `X-Admin-Token`. Pendências que continuam documentadas: cancelar um pedido ainda não devolve estoque (comportamento original mantido); `/admin/query` foi mantido para preservar o contrato, restrito a admin + SELECT read-only, e ainda devolve os hashes; o token não tem revogação; não há limite de tentativas no login.

#### Projeto 2 — ecommerce-api-legacy

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [x] Linguagem detectada corretamente (JavaScript / Node.js v24.19.0)
- [x] Framework detectado corretamente (Express ^4.18.2, instalada 4.22.1; sqlite3 5.1.7)
- [x] Domínio da aplicação descrito corretamente (LMS com checkout: cursos, matrículas, pagamentos, relatório financeiro)
- [x] Número de arquivos analisados condiz com a realidade (3: app.js, AppManager.js, utils.js)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (20 na auditoria oficial; 21 na execução via CLI com a skill final)
- [x] Detecção de APIs deprecated incluída (se aplicável) — API callback do sqlite3, 11 ocorrências
- [x] Skill pausa e pede confirmação antes da Fase 3 (também no CLI real: logs em reports/cli-runs/)

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (src/models, src/routes, src/controllers + services/)
- [x] Configuração extraída para módulo de config (src/config/index.js + .env.example; sem segredo default no código)
- [x] Models criados para abstrair dados (src/models/*.model.js)
- [x] Views/Routes separadas para visualização ou roteamento (src/routes/*.routes.js)
- [x] Controllers concentram o fluxo da aplicação (src/controllers/*.controller.js)
- [x] Error handling centralizado (src/middlewares/errorHandler.js + asyncHandler + notFound + errors/AppError.js)
- [x] Entry point claro (src/app.js → app.factory.js; npm start inalterado)
- [x] Aplicação inicia sem erros (ADMIN_TOKEN=... SEED_USER_PASSWORD=... PORT=<p> npm start)
- [x] Endpoints originais respondem corretamente (iteração 2: 19/19 do baseline com o mesmo status; shape igual em 15, ≈ em 4 por correção intencional)
```

Pendências resolvidas na iteração 2: rotas inexistentes respondem 404 no formato da API (e métodos não suportados, 405 com `Allow`); a mensagem do DELETE virou `Usuário deletado, junto com suas matrículas e pagamentos.`; não existe mais o token de admin default `dev-admin-token` no código; a senha do seed vem de `SEED_USER_PASSWORD`. Pendências que continuam documentadas: `DELETE` de um id bem formado mas inexistente continua retornando 200, como no baseline; os campos crípticos do contrato (`usr`, `eml`, `pwd`, `c_id`, `card`) foram mantidos; os erros saem em texto com `Content-Type: text/html`; o gateway de pagamento continua simulado.

#### Projeto 3 — task-manager-api

```markdown
## Checklist de Validação

### Fase 1 — Análise
- [x] Linguagem detectada corretamente (Python 3.14)
- [x] Framework detectado corretamente (Flask 3.0.0 + Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.1.8)
- [x] Domínio da aplicação descrito corretamente (Task Manager: tasks, usuários, categorias, relatórios)
- [x] Número de arquivos analisados condiz com a realidade (15 arquivos .py)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (19 na auditoria oficial; 24 na execução via CLI com a skill final)
- [x] Detecção de APIs deprecated incluída (se aplicável) — datetime.utcnow, Model.query.get / Query API legada, type(x) == list
- [x] Skill pausa e pede confirmação antes da Fase 3 (também no CLI real: logs em reports/cli-runs/)

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC (models/, routes/, controllers/ + services/, validators/)
- [x] Configuração extraída para módulo de config (config/settings.py + .env.example; senhas do seed vêm de SEED_*_PASSWORD, sem fallback literal)
- [x] Models criados para abstrair dados (models/ preservados e enriquecidos: to_dict sem password, is_overdue)
- [x] Views/Routes separadas para visualização ou roteamento (routes/ existente + category_routes.py)
- [x] Controllers concentram o fluxo da aplicação (controllers/ novo)
- [x] Error handling centralizado (middlewares/error_handler.py + errors.py)
- [x] Entry point claro (app.py → create_app())
- [x] Aplicação inicia sem erros (seed + python app.py; sem DeprecationWarning/LegacyAPIWarning)
- [x] Endpoints originais respondem corretamente (iteração 2: as 63 requisições do baseline com credencial + 17 checagens novas; nenhum 500)
```

Pendências resolvidas na iteração 2: as senhas do seed saíram de `seed.py` e vêm de `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD`/`SEED_MANAGER_PASSWORD` (sem elas, o seed gera e imprime senhas aleatórias); o `POST /login` devolve um token assinado e com expiração, validado por `require_auth`, no lugar de `fake-jwt-token-<id>`; `GET /users*` e os relatórios exigem credencial; `PUT /users/<id>` não pode mais ser usado anonimamente. Pendências que continuam documentadas: `/health` em hora local (AP-15 parcial); a troca de senha não pede a senha atual; o token não tem revogação; `GET /tasks*` continua público com `user_name`; um banco antigo precisa ser recriado com `python seed.py`.

### Logs da aplicação rodando após a refatoração

O log abaixo é do **smoke test independente**, executado pela sessão orquestradora depois da iteração 2, fora das sessões que rodaram a skill. Ele sobe cada aplicação com o comando de start original e as variáveis de ambiente indicadas na própria linha (`.env.example` exportado nos projetos 1 e 3; `ADMIN_TOKEN` e `SEED_USER_PASSWORD` explícitos no projeto 2), espera a porta responder e chama os endpoints principais com `curl`. A linha `###` de cada bloco é o comando usado. As respostas foram truncadas pelo próprio script, e os códigos de cor ANSI foram removidos. Este log substitui o smoke test anterior, feito depois da primeira execução.

```text
### P1 code-smells-project: export $(grep -v '^#' .env.example | xargs); PORT=5191 python app.py
GET     /                                            -> 200 {"endpoints":{"health":"/health","login":"/login","pedidos":"/pedidos","produtos":"/produtos","relat
GET     /health                                      -> 200 {"ambiente":"development","counts":{"pedidos":0,"produtos":10,"usuarios":3},"database":"connected","
GET     /produtos                                    -> 200 {"dados":[{"ativo":1,"categoria":"informatica","criado_em":"2026-11-14 15:16:03","descricao":"Notebo
GET     /produtos/busca?q=gamer                      -> 200 {"dados":[{"ativo":1,"categoria":"informatica","criado_em":"2026-11-14 15:16:03","descricao":"Notebo
POST    /login                                       -> 200 {"dados":{"email":"maria@email.com","id":3,"nome":"Maria Santos","tipo":"cliente"},"mensagem":"Login
GET     /usuarios/3 (sem token)                      -> 401 {"erro":"Não autorizado"} 
GET     /usuarios/3 (Bearer dono)                    -> 200 {"dados":{"criado_em":"2026-11-14 15:16:04","email":"maria@email.com","id":3,"nome":"Maria Santos","
GET     /usuarios (admin)                            -> 200 {"dados":[{"criado_em":"2026-11-14 15:16:04","email":"admin@loja.com","id":1,"nome":"Admin","tipo":"
POST    /pedidos (Bearer)                            -> 201 {"dados":{"pedido_id":1,"total":5999.99},"mensagem":"Pedido criado com sucesso","sucesso":true} 
GET     /relatorios/vendas (admin)                   -> 200 {"dados":{"desconto_aplicavel":300.0,"faturamento_bruto":5999.99,"faturamento_liquido":5699.99,"pedi
GET     /nao-existe                                  -> 404 {"erro":"Rota não encontrada"} 
```

```text
### P2 ecommerce-api-legacy: ADMIN_TOKEN=dev-admin-token SEED_USER_PASSWORD=123 PORT=3191 npm start
POST    /api/checkout                                -> 200 {"msg":"Sucesso","enrollment_id":2}
POST    /api/checkout card numerico                  -> 400 Bad Request
GET     /api/admin/financial-report (sem)            -> 401 Não autorizado
GET     /api/admin/financial-report (admin)          -> 200 [{"course":"Clean Architecture","revenue":1994,"students":[{"student":"Leonan","paid":997},{"student
DELETE  /api/users/2 (admin)                         -> 200 Usuário deletado, junto com suas matrículas e pagamentos.
GET     /api/unknown                                 -> 404 Rota não encontrada: GET /api/unknown
```

```text
### P3 task-manager-api: export $(grep -v '^#' .env.example | xargs); python seed.py; PORT=5391 python app.py
GET     /health                                      -> 200 {"status":"ok","timestamp":"2026-11-14 12:16:47.345865"} 
GET     /tasks                                       -> 200 [{"category_id":1,"category_name":"Backend","created_at":"2026-11-14 15:16:43.961567","description":
POST    /login                                       -> 200 {"message":"Login realizado com sucesso","token":"eyJzdWIiOjF9.avh7Xw.pCdAVoQR_0cUOlPwxeoRjt99N80","
GET     /users (sem token)                           -> 401 {"error":"Não autorizado"} 
GET     /users (Bearer)                              -> 200 [{"active":true,"created_at":"2026-11-14 15:16:43.952648","email":"joao@email.com","id":1,"name":"Jo
GET     /users/1 (Bearer)                            -> 200 {"active":true,"created_at":"2026-11-14 15:16:43.952648","email":"joao@email.com","id":1,"name":"Jo\
GET     /tasks/stats                                 -> 200 {"cancelled":1,"completion_rate":10.0,"done":1,"in_progress":2,"overdue":2,"pending":6,"total":10} 
POST    /tasks (Bearer)                              -> 201 {"category_id":null,"created_at":"2026-11-14 15:16:48.106621","description":"","due_date":null,"id":
GET     /reports/summary                             -> 200 {"generated_at":"2026-11-14 15:16:48.153415","overdue":{"count":2,"tasks":[{"days_overdue":3,"due_da
GET     /categories                                  -> 200 [{"color":"#3498db","created_at":"2026-11-14 15:16:43.950110","description":"Tarefas de backend","id
DELETE  /categories/4 (sem admin)                    -> 401 {"error":"Não autorizado"} 
GET     /nao-existe                                  -> 404 {"error":"The requested URL was not found on the server. If you entered the URL manually please chec
```

O que o smoke test mostra:

- nenhuma resposta de usuário contém `senha`/`password`;
- projeto 1: `POST /login` devolve um token; `GET /usuarios/3` responde 401 sem token e 200 com o Bearer do dono; as listagens e o relatório respondem com `X-Admin-Token`; rota inexistente responde 404 em JSON;
- projeto 2: `card` numérico responde 400 sem derrubar o processo; o relatório financeiro responde 401 sem token e 200 com `X-Admin-Token`; a mensagem do DELETE é a nova (`...junto com suas matrículas e pagamentos.`); rota inexistente responde 404 no formato texto da API;
- projeto 3: `POST /login` devolve um token assinado (`eyJ...`) no lugar de `fake-jwt-token-<id>`; `GET /users` responde 401 sem token e 200 com Bearer; `DELETE` sem admin responde 401; rota inexistente responde 404 em JSON.

### Comparação de endpoints (baseline × refatorado)

As tabelas abaixo comparam o **código original** com o resultado da **primeira execução**. As tabelas completas estão em `<projeto>/.refactor-arch/iteration-1/refactor-summary.md`. A comparação da iteração 2, que usa como baseline o código já refatorado, está em `<projeto>/.refactor-arch/refactor-summary.md`. Em resumo, a iteração 2 mudou estes pontos em relação às tabelas abaixo: no projeto 1, `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` e `POST /pedidos` passaram a exigir token, e o login ganhou a chave `token`; no projeto 2, a mensagem do DELETE mudou e rotas inexistentes respondem 404/405 no formato da API; no projeto 3, `GET /users*` e `/reports/*` exigem credencial, as escritas de tasks e categorias exigem token, e o valor de `token` no login passou a ser assinado. Legenda: `=` shape idêntico; `≈` diferença intencional e documentada.

**Projeto 1 — 54/54 requisições do baseline respondem; 19/19 rotas registradas; nenhuma divergência não intencional.** Destaques:

| Requisição | Antes | Depois | Obs |
|---|---|---|---|
| `GET /health` | 200 | 200 ≈ | `secret_key`, `db_path` e `debug` removidos |
| `GET /usuarios/1` | 200 | 200 ≈ | campo `senha` removido |
| `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, escrita de produtos, `/admin/*` | 200/201 | 401 sem token / 200–201 com `X-Admin-Token` | auth adicionada (AP-06) |
| `POST /login` com `admin@loja.com' --` | 200 (bypass) | 401 | SQL Injection corrigida |
| `POST /produtos` nome `O'Reilly` | 500 | 201 | apóstrofo não quebra mais o SQL |
| `POST /pedidos` com `usuario_id` 999 | 201 | 400 | validação + integridade |
| `PUT /pedidos/999/status` | 200 | 404 | recurso inexistente |
| `POST /admin/query` não-SELECT | 200 | 400 | só SELECT, em conexão read-only |
| `GET /nao-existe` | 404 HTML | 404 JSON | formato de erro padronizado |

**Projeto 2 — 13/13 requisições com o mesmo status; shape igual em 10, ≈ em 3.**

| # | Requisição | Antes | Depois | Obs |
|---|---|---|---|---|
| 1, 7, 10 | `GET /api/admin/financial-report` | 200 | 401 sem token / 200 com token | mesmos valores; ordem agora determinística; #10 sem órfãos `"Unknown"` (cascata) |
| 2–6 | `POST /api/checkout` (inválido, curso 999, cartão recusado, sucesso ×2) | 400/404/400/200/200 | idem | cartão recusado não cria mais usuário órfão |
| 8, 9 | `DELETE /api/users/:id` | 200 | 401 sem token / 200 com token | mesma mensagem (contrato) |
| 11 | rota inexistente | 404 | 404 | |
| 12 | JSON malformado | 400 HTML + stack trace | 400 `Bad Request` | stack trace removido |
| 13 | `card` numérico | **processo derrubado** | 400 | servidor continua no ar |

**Projeto 3 — 45/48 requisições idênticas; os 3 restantes eram 500 e agora são 400.**

| # | Requisição | Antes | Depois |
|---|---|---|---|
| 8 | `GET /tasks/search?priority=abc` | 500 (HTML) | 400 `{"error":"Prioridade inválida"}` |
| 24 | `POST /tasks` com `priority: "2"` | 500 (HTML) | 400 `{"error":"Prioridade inválida"}` |
| 40 | `PUT /categories/5` com body `null` | 500 (HTML) | 400 `{"error":"Dados inválidos"}` |

Também houve mudanças intencionais nos shapes: o campo `password` foi removido de `/users*` e `/login`, e o 415 passou a sair em JSON. Os `DELETE` e as mudanças de `role` exigem `X-Admin-Token`. As estatísticas (`/tasks/stats`, `/reports/summary`) deram os mesmos valores do baseline.

### Comportamento da skill em stacks diferentes

- **Detecção.** Nos 3 projetos, a Fase 1 identificou linguagem, framework e versão pelo manifesto e pelo import, inclusive a versão *instalada* diferente da declarada (Express `^4.18.2` → 4.22.1; SQLAlchemy 2.1.8 transitivo).
- **Monolito × camadas parciais.** Nos projetos 1 e 2, a skill aplicou o split completo e apagou os arquivos monolíticos. No projeto 3, aplicou a estratégia incremental: preservou os modelos e blueprints, inseriu `controllers/`, `services/` e `validators/`, aproveitou código que não era usado (`Task.is_overdue()`) e apagou o que continuou morto (`notification_service.py`). Mesmo num projeto "organizado", ela encontrou 5 CRITICAL.
- **Particularidades do Node.** O mesmo catálogo detectou callback hell e a API callback do `sqlite3` (AP-16/AP-17), que não se aplicam aos projetos Python. A refatoração usou o PB-12 (wrapper Promise + `async/await`), um `asyncHandler` para o Express 4 e o error handler registrado por último. Com o banco `:memory:`, o `listen` só acontece depois do schema e do seed.
- **Particularidades do Flask.** No projeto 1, a conexão passou a ser por requisição (`flask.g`). No projeto 3, o `create_all()` saiu do import e foi para a factory, e `app = create_app()` foi mantido em nível de módulo para não quebrar `from app import app` no seed nem `flask --app app run`.
- **Formato de erro.** Cada projeto manteve a sua chave de erro original: `erro` no 1, texto puro no 2 e `error` no 3. A padronização só substituiu o que antes saía em HTML ou stack trace.
- **Iteração da skill.** A execução no projeto 2 revelou o defeito no grep do `sqlite3` (`[^)]*`), corrigido nas 3 cópias. Durante a validação, o projeto 1 precisou de 3 iterações (por exemplo, trocar as senhas do seed por hashes pré-computados, que a iteração 2 depois substituiu por variáveis `SEED_*`).
- **Re-execução sobre código já refatorado.** Na iteração 2, a Fase 1 dos 3 projetos classificou a arquitetura como "já em camadas", e a Fase 3 aplicou só correções pontuais, sem mover arquivos. O modo re-execução arquivou a primeira execução em `iteration-1/`. No projeto 2, o log mostra ``Re-execution mode detected (`iteration-1/` exists)``. A validação do projeto 2 também pegou uma regressão da própria refatoração: a primeira versão do `methodNotAllowed` devolvia 405 para `OPTIONS`. Ela foi corrigida antes de concluir, segundo o `refactor-summary.md`.

### Nota de transparência sobre a execução

A skill foi executada de duas formas.

**1. Primeira execução: subagentes seguindo o `SKILL.md`.** Um subagente do Claude Code por projeto, sobre o código original. No gate da Fase 2, cada agente parou e imprimiu `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`. Os relatórios foram salvos em `reports/audit-project-{1,2,3}.md` **antes** de qualquer alteração no código. A confirmação `y` foi dada pela sessão orquestradora em nome do aluno. As evidências dessa execução (`baseline.md`, `audit-report.md`, `refactor-summary.md` e os logs do servidor) estão em `<projeto>/.refactor-arch/iteration-1/`. Os arquivos `phase1-analysis.md` dessa execução foram gravados pela sessão orquestradora a partir da saída impressa por cada agente, porque a regra de salvá-los veio depois.

**2. Execuções reais pelo Claude Code CLI, sem subagentes, com a skill final.**
- Sobre cópias limpas do código original, só Fases 1–2 (`claude -p "/refactor-arch"`): as três pararam no gate e nenhum arquivo versionado foi modificado. Ninguém respondeu ao gate, e as cópias não foram refatoradas. Logs em `reports/cli-runs/project-{1,2,3}-original-phases-1-2.log`.
- Iteração 2 sobre os projetos já refatorados, em dois turnos: `claude -p "/refactor-arch"` e depois `claude -p "y" --resume <session-id>`. O `y` do segundo turno foi enviado pela sessão orquestradora em nome do aluno. Logs em `reports/cli-runs/project-{1,2,3}-iteration-2.log`. Evidências no topo de `<projeto>/.refactor-arch/`.

Os logs do CLI foram extraídos do `stream-json`: eles trazem os textos do assistente e as chamadas de ferramenta resumidas. **Nenhum arquivo foi commitado pelos agentes.** Os logs da iteração 2 terminam com "Nada commitado" / "Nenhum commit feito". O `git log` do repositório continua mostrando só o commit inicial (`6d1ce62`): o código refatorado está no working tree, sem commit.

Ajustes feitos na skill **entre** as execuções (já presentes nas 3 cópias, que continuam idênticas): (1) o grep da API de callback do `sqlite3` passou de `[^)]*` para `.*`; (2) a Fase 1 passou a salvar o bloco em `.refactor-arch/phase1-analysis.md`, e o relatório da Fase 2 passou a terminar com a linha do gate; (3) foi incluída a dica `npm install-scripts approve sqlite3`, porque o npm ≥ 11 bloqueia install scripts. Pelo mesmo motivo, o `package.json` do projeto 2 ganhou `"allowScripts": {"sqlite3@5.1.7": true}`, para que um `npm install` limpo funcione; (4) catálogo AP-24…AP-26, extensão de AP-01 e AP-12, playbook PB-21…PB-25 e modo re-execução (ver seção B).

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e autenticado (`claude --version`).
- **Python 3.10+** (testado com 3.14.3), com `venv`.
- **Node.js 18+** (testado com v24.19.0) e npm.
- `curl` e `lsof` para validar.

### Executar a skill

A skill fica em `.claude/skills/refactor-arch/` em cada projeto e deve ser chamada a partir da raiz do projeto. Há duas formas.

**Interativa:** abra o Claude Code e digite o comando da skill.

```bash
cd code-smells-project        # ou ecommerce-api-legacy / task-manager-api
claude
# no prompt do Claude Code:
/refactor-arch
# ... Fases 1 e 2 ... "Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]"
y
```

**Não interativa, em dois turnos** (a forma usada na iteração 2 e nos logs de `reports/cli-runs/`):

```bash
cd code-smells-project
claude -p "/refactor-arch"                 # turno 1: Fases 1-2, termina no gate [y/n]
claude -p "y" --resume <session-id>        # turno 2: confirmação → Fase 3, na mesma sessão
```

O `<session-id>` é o id da sessão do turno 1 (por exemplo, o campo `session_id` com `--output-format json`, ou a sessão listada por `claude --resume`). Para auditar sem refatorar, rode só o turno 1 ou responda `n`.

A ordem sugerida é 1 → 2 → 3: do monolito mais simples, para a outra stack e por fim o projeto parcialmente organizado. Cada execução imprime o bloco `PHASE 1: PROJECT ANALYSIS`, gera o relatório e **para** no gate `[y/n]`. As saídas ficam em `.refactor-arch/`. Depois da Fase 2, copie `.refactor-arch/audit-report.md` para `reports/audit-project-N.md`, se quiser. Se `.refactor-arch/` já existir, a execução anterior é arquivada em `.refactor-arch/iteration-<n>/`.

Observação: os projetos deste repositório já estão refatorados, então uma nova execução vai auditar o código novo, e não o legado. Para reproduzir do zero, extraia o código do commit inicial, por exemplo com `git archive HEAD code-smells-project | tar -x -C <destino>`, ou use um clone do repositório base. Depois copie a pasta `.claude/skills/refactor-arch/` para dentro da cópia, porque ela não faz parte do commit inicial.

### Subir as aplicações refatoradas

> **macOS:** a porta 5000 costuma estar ocupada pelo AirPlay Receiver (processo `ControlCenter`). Se `localhost:5000` não responder com a API, suba com outra porta (`PORT=5191 .venv/bin/python app.py`) e ajuste os `curl` abaixo, ou desative o AirPlay Receiver nas configurações do sistema.

**Projeto 1 — code-smells-project (Flask, porta 5000)**

```bash
cd code-smells-project
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export $(grep -v '^#' .env.example | xargs)   # o projeto lê só o ambiente (não usa python-dotenv)
.venv/bin/python app.py                       # 127.0.0.1:5000; outra porta: PORT=5191 .venv/bin/python app.py
```

O banco `loja.db` é criado com o seed no boot. As senhas das contas vêm de `SEED_ADMIN_PASSWORD`/`SEED_JOAO_PASSWORD`/`SEED_MARIA_PASSWORD` (no `.env.example`: `admin123`, `123456`, `senha123`). Sem essas variáveis, o seed gera senhas aleatórias e as registra uma vez no log. Exporte as variáveis **antes** do boot. Para voltar ao estado inicial, rode `rm -f loja.db`.

**Projeto 2 — ecommerce-api-legacy (Express, porta 3000)**

```bash
cd ecommerce-api-legacy
npm install
# o package.json já libera o install script do sqlite3 ("allowScripts"), exigido pelo npm >= 11;
# se mesmo assim faltar o binding nativo:
(cd node_modules/sqlite3 && npx prebuild-install -r napi)
ADMIN_TOKEN=dev-admin-token SEED_USER_PASSWORD=123 npm start   # 127.0.0.1:3000; porta ocupada: acrescente PORT=3191
```

Outra opção é copiar `.env.example` para `.env`, trocar os placeholders e rodar `export $(grep -v '^#' .env | xargs) && npm start`. Sem `ADMIN_TOKEN`, o app gera um token aleatório a cada boot e o imprime no log (`ADMIN_TOKEN não definido; token gerado para esta execução`). O banco é `:memory:`, então schema e seed são recriados a cada boot.

**Projeto 3 — task-manager-api (Flask-SQLAlchemy, porta 5000)**

```bash
cd task-manager-api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                          # carregado via python-dotenv; ou: export $(grep -v '^#' .env.example | xargs)
.venv/bin/python seed.py                      # recria instance/tasks.db com 3 usuários, 4 categorias, 10 tasks
.venv/bin/python app.py                       # 127.0.0.1:5000; outra porta: PORT=5391 .venv/bin/python app.py
```

As senhas do seed vêm de `SEED_ADMIN_PASSWORD`/`SEED_USER_PASSWORD`/`SEED_MANAGER_PASSWORD` (no `.env.example`: `1234`, `abcd`, `pass`, para `joao@`, `maria@` e `pedro@email.com`). Sem elas, o seed gera e imprime senhas aleatórias.

### Variáveis de ambiente e credenciais

Cada projeto tem um `.env.example` com as chaves: `APP_ENV`, `SECRET_KEY`, `ADMIN_TOKEN`, `HOST`, `PORT`, `FLASK_DEBUG`, `DATABASE_PATH`/`DATABASE_URL`/`DB_PATH`, `CORS_ORIGINS`, `PAYMENT_GATEWAY_KEY`, `LOG_LEVEL`, `TOKEN_MAX_AGE` e as senhas de seed `SEED_*`, conforme o projeto.

- **Token de usuário (projetos 1 e 3):** `POST /login` devolve o campo `token`, assinado com `SECRET_KEY` (`itsdangerous`) e válido por `TOKEN_MAX_AGE` segundos (default 3600). Envie-o em `Authorization: Bearer <token>`. Ele dá acesso aos dados do próprio usuário. Com o token de outro usuário, a resposta é 403.
- **Token de admin (3 projetos):** header `X-Admin-Token`. Nos projetos 1 e 3, o valor de desenvolvimento é `dev-admin-token` (está no `.env.example`). No projeto 2 não há default no código: use o valor passado em `ADMIN_TOKEN` ou o token gerado que aparece no log.
- Fora de `development`/`test` (projeto 1) ou com `APP_ENV=production` (projetos 2 e 3), o boot falha se os segredos estiverem ausentes ou, nos projetos 1 e 3, com os defaults de dev.

### Validar que a refatoração funcionou

Os exemplos abaixo reproduzem chamadas do smoke test independente (seção C), usando as portas padrão.

```bash
# Projeto 1 (com o .env.example exportado)
curl -s localhost:5000/health                                                   # sem secret_key/db_path
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"maria@email.com","senha":"senha123"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w '%{http_code}\n' localhost:5000/usuarios/3             # 401
curl -s -H "Authorization: Bearer $TOKEN" localhost:5000/usuarios/3             # 200, sem campo "senha"
curl -s -H 'X-Admin-Token: dev-admin-token' localhost:5000/usuarios             # 200
curl -s localhost:5000/nao-existe                                               # 404 {"erro":"Rota não encontrada"}

# Projeto 2 (ADMIN_TOKEN=dev-admin-token SEED_USER_PASSWORD=123 npm start)
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Ana","eml":"ana@teste.com","pwd":"x","c_id":1,"card":"4111222233334444"}'   # 200
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Ana","eml":"ana@teste.com","c_id":1,"card":4111}'                           # 400, servidor continua no ar
curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/api/admin/financial-report       # 401
curl -s -H 'X-Admin-Token: dev-admin-token' localhost:3000/api/admin/financial-report    # 200
curl -s -X DELETE -H 'X-Admin-Token: dev-admin-token' localhost:3000/api/users/2         # 200 "Usuário deletado, junto com suas matrículas e pagamentos."
curl -s localhost:3000/api/unknown                                                       # 404 "Rota não encontrada: GET /api/unknown"

# Projeto 3 (seed rodado com o .env.example)
curl -s localhost:5000/tasks/stats                                              # total 10, overdue 2
TOKEN=$(curl -s -X POST localhost:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"joao@email.com","password":"1234"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w '%{http_code}\n' localhost:5000/users                  # 401
curl -s -H "Authorization: Bearer $TOKEN" localhost:5000/users/1                # 200, sem "password"
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:5000/categories/4  # 401
curl -s -H 'X-Admin-Token: dev-admin-token' -X DELETE localhost:5000/categories/4   # 200
```

Para uma validação completa, compare com os arquivos de cada projeto:

- `.refactor-arch/baseline.md`: todas as requisições do baseline, com status e shape (iteração 2 no topo; primeira execução em `iteration-1/`);
- `.refactor-arch/refactor-summary.md`: comparação de endpoints, mudanças aplicadas, credenciais para validar e pendências;
- `.refactor-arch/*.log`: logs do servidor no baseline e após a refatoração.
