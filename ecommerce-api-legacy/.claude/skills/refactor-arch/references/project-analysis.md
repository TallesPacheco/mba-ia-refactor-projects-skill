# Análise de Projeto — Heurísticas (Fase 1)

Objetivo: descobrir, **com evidência de arquivo**, a stack, o banco, o domínio, a arquitetura atual, os entry points e as rotas do projeto — e capturar um baseline de runtime antes de qualquer mudança.

Regra de ouro: toda afirmação do resumo da Fase 1 deve vir de um arquivo lido ou de um comando executado. Nunca "chute" versão ou framework.

---

## 1. Escopo: o que contar e o que ignorar

Diretórios/arquivos **sempre excluídos** da análise e da contagem:

```
.git/ .claude/ .refactor-arch/ .venv/ venv/ env/ __pycache__/ .pytest_cache/ .mypy_cache/
node_modules/ dist/ build/ coverage/ .next/ target/ vendor/ bin/ obj/ instance/
*.lock package-lock.json yarn.lock pnpm-lock.yaml poetry.lock Pipfile.lock composer.lock Gemfile.lock go.sum
*.db *.sqlite *.sqlite3 *.log *.min.js .DS_Store
```

Listar arquivos-fonte (ajuste as extensões à linguagem detectada):

```bash
find . -type f \( -name '*.py' -o -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.ts' \
  -o -name '*.go' -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.php' -o -name '*.cs' \) \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/.git/*' \
  -not -path '*/.claude/*' -not -path '*/.refactor-arch/*' -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' -not -path '*/build/*' | sort
```

Contar LOC (linhas totais, é o que o relatório usa como `~L lines of code`):

```bash
<comando find acima> | xargs wc -l | tail -1
```

"Source files" = número de arquivos de código da aplicação (inclui seed/scripts e testes se existirem — informe à parte quantos são testes). Não conte manifestos (`requirements.txt`, `package.json`), `README`, `.http`, `.env*`.

---

## 2. Detecção de linguagem

| Evidência (manifesto) | Linguagem |
|---|---|
| `requirements*.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, `Pipfile` | Python |
| `package.json` (+ `tsconfig.json` → TypeScript) | JavaScript / TypeScript (Node.js) |
| `go.mod` | Go |
| `pom.xml`, `build.gradle(.kts)` | Java / Kotlin |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj`, `*.sln` | C# |
| `Cargo.toml` | Rust |

Sem manifesto: use a extensão predominante (`find . -type f -name '*.*' | sed 's/.*\.//' | sort | uniq -c | sort -rn`). Versão do runtime: `python3 --version`, `node --version`, campo `engines` do `package.json`, `python_requires`, `.python-version`, `.nvmrc`.

---

## 3. Detecção de framework e versão

Procure o framework no manifesto **e** confirme pelo import no código.

| Framework | Manifesto | Import / sinal no código |
|---|---|---|
| Flask | `flask==X` | `from flask import Flask`, `Flask(__name__)` |
| FastAPI | `fastapi` | `FastAPI()`, `@app.get(` |
| Django | `django` | `manage.py`, `settings.py`, `urls.py` |
| Express | `"express"` em `dependencies` | `require('express')`, `express()` |
| NestJS | `@nestjs/core` | `@Controller(`, `@Module(` |
| Fastify / Koa / Hapi | `fastify`, `koa`, `@hapi/hapi` | `fastify()`, `new Koa()` |
| Spring Boot | `spring-boot-starter-*` | `@RestController`, `@SpringBootApplication` |
| Rails | `rails` | `config/routes.rb`, `ApplicationController` |
| Laravel | `laravel/framework` | `routes/web.php`, `routes/api.php` |
| Gin / Echo / Fiber / net/http | `github.com/gin-gonic/gin` etc. | `gin.Default()`, `http.HandleFunc(` |

Versão: prefira a **versão realmente instalada** quando o ambiente existir, pois pins abertos (`>=`) e dependências transitivas podem diferir:

```bash
.venv/bin/pip show flask | grep -i version          # Python
.venv/bin/pip freeze | grep -iE 'flask|sqlalchemy|werkzeug'
node -p "require('./node_modules/express/package.json').version"   # Node
grep -A2 '"node_modules/express"' package-lock.json | grep version
```

Se o pin no manifesto e a versão instalada diferirem, reporte a do manifesto e cite a instalada (ex.: `Flask 3.0.0 (SQLAlchemy 2.x transitivo)`). Versões transitivas importam para APIs deprecated (ex.: SQLAlchemy 2.x torna `Query.get` legado).

"Dependencies" no resumo: liste as dependências **diretas** relevantes além do framework (ORM, CORS, driver de banco, validação, auth). Marque as que estão declaradas mas nunca importadas — isso vira finding de código morto:

```bash
# Python: para cada pacote do requirements, conferir se é importado
grep -rnE '^\s*(import|from)\s+<modulo>' --include='*.py' .
# Node: para cada dependência do package.json
grep -rnE "require\(['\"]<pkg>|from ['\"]<pkg>" --include='*.js' --include='*.ts' . | grep -v node_modules
```

---

## 4. Detecção de banco de dados

| Sinal | Banco / acesso |
|---|---|
| `import sqlite3`, `sqlite3.connect(`, `require('sqlite3')`, `better-sqlite3` | SQLite com driver cru |
| `flask_sqlalchemy`, `sqlalchemy`, `SQLALCHEMY_DATABASE_URI` | ORM SQLAlchemy |
| `psycopg`, `pg`, `postgres://`, `postgresql://` | PostgreSQL |
| `pymysql`, `mysqlclient`, `mysql2`, `mysql://` | MySQL |
| `pymongo`, `mongoose`, `mongodb://` | MongoDB |
| `sequelize`, `typeorm`, `prisma`, `knex`, `django.db` | ORM/query builder Node/Django |
| `:memory:` | SQLite em memória (estado zera a cada boot) |

Tabelas:

```bash
grep -rniE 'create table( if not exists)?\s+\w+' --include='*.py' --include='*.js' --include='*.ts' --include='*.sql' . | grep -v node_modules
grep -rnE '__tablename__\s*=|class \w+\((db\.)?Model\)' --include='*.py' .          # SQLAlchemy/Django
grep -rnE 'sequelize\.define\(|@Entity\(|model \w+ \{' --include='*.js' --include='*.ts' --include='*.prisma' .
```

Com SQLAlchemy sem `__tablename__`, o nome da tabela é o nome da classe em snake_case. Anote também: onde o arquivo do banco é criado (caminho relativo ao CWD? `instance/`?), quando o schema é criado (no import? na 1ª requisição? em script de seed?) e se existe seed.

---

## 5. Inferência de domínio

Combine três fontes e descreva em uma linha `<Tipo de sistema> (<entidades principais>)`:

1. Nomes de rotas (`/orders`, `/checkout`, `/tickets`, `/invoices`...).
2. Nomes de tabelas/modelos.
3. README, título do app em logs/mensagens de boot, nomes de funções de negócio (checkout, relatório, notificação).

Exemplos de saída: `E-commerce API (products, orders, customers)`, `Help desk API (tickets, agents, queues)`, `Blog API (posts, authors, tags)`. Use os nomes de entidades **na língua do código**.

---

## 6. Entry point e comando de start

| Stack | Onde procurar |
|---|---|
| Python | `if __name__ == '__main__':`, `app = Flask(`, `create_app(`, `wsgi.py`, `Procfile`, README |
| Node | `"main"` e `"scripts.start"` do `package.json`, `app.listen(`, `server.listen(` |
| Outros | `main()` em Go, `@SpringBootApplication`, `bin/rails server`, `artisan serve` |

Registre: comando de start original (ex.: `python app.py`, `npm start`), **porta**, **host** e **debug** — e se estão hardcoded (`app.run(debug=True, host='0.0.0.0', port=5000)`, `listen(3000)`, `config.port = 3000`). Isso define como subir o baseline sem editar arquivos (seção 9) e quais findings existem (debug/0.0.0.0, porta fixa).

---

## 7. Classificação de arquitetura

| Nível | Sinais | Estratégia na Fase 3 |
|---|---|---|
| **Monolito** | 1–5 arquivos; um arquivo concentra rotas + SQL + regras; classe/arquivo "manager" com tudo; config literal no mesmo arquivo | Split completo (ver `mvc-guidelines.md`, seção Adaptação) |
| **Camadas parciais** | pastas `models/`, `routes/`, `services/`, `utils/` existem, mas: regra de negócio e queries dentro dos handlers; services/utils não usados; sem config, sem app factory, sem error handler | Incremental: preservar camadas boas, inserir controllers/services, config, error handler, app factory |
| **MVC em camadas** | rotas finas, controllers/services com regra, models/repositórios com acesso a dados, config por ambiente, error handler central | Apenas correções pontuais dos findings |

Comandos úteis para medir a mistura de responsabilidades:

```bash
# Arquivos que fazem HTTP e SQL ao mesmo tempo (forte sinal de monolito/handler gordo)
grep -rlE '@app\.route|\.route\(|@\w+\.(get|post|put|delete)\(|router\.|app\.(get|post|put|delete)\(' . \
  --include='*.py' --include='*.js' --include='*.ts' | grep -v node_modules \
  | xargs grep -lE 'execute\(|SELECT |INSERT |UPDATE |DELETE |\.query\.|db\.session|db\.(run|get|all)\('
# Maiores arquivos
<find de arquivos-fonte> | xargs wc -l | sort -rn | head
# Módulos nunca importados (services/utils órfãos)
grep -rn 'import\|require' --include='*.py' --include='*.js' . | grep -v node_modules | grep -c '<nome_modulo>'
```

Descrição no resumo: uma frase com nível + evidência, ex.: `Monolítica — 4 arquivos, rotas/SQL/regras misturados, sem camadas` ou `Camadas parciais — models/routes/services existem, mas regra de negócio nos handlers, sem config nem error handler`.

---

## 8. Enumeração de rotas por framework

Sempre gere a lista **completa** (método + path + handler + arquivo:linha). Ela é a base do baseline e da comparação final.

| Framework | Comando / grep |
|---|---|
| Flask | `.venv/bin/flask --app <modulo> routes` (mais confiável: inclui blueprints e prefixos). Grep: `grep -rnE '@\w+\.route\(|add_url_rule\(|Blueprint\(' --include='*.py' .` |
| FastAPI | `grep -rnE '@(app|router)\.(get|post|put|patch|delete)\(|APIRouter\(|include_router\(' --include='*.py' .` |
| Django | `grep -rnE 'path\(|re_path\(' */urls.py`; `python manage.py show_urls` (django-extensions) |
| Express | `grep -rnE '(app|router)\.(get|post|put|patch|delete|all|use)\(' --include='*.js' --include='*.ts' . \| grep -v node_modules` — some prefixos de `app.use('/prefix', router)` |
| NestJS | `grep -rnE '@Controller\(|@(Get|Post|Put|Patch|Delete)\(' --include='*.ts' src` |
| Spring | `grep -rnE '@(RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping)' --include='*.java' --include='*.kt' .` |
| Rails | `bin/rails routes` |
| Laravel | `php artisan route:list` |
| Go (net/http, gin, echo, chi) | `grep -rnE '\.(GET|POST|PUT|DELETE|Handle|HandleFunc)\(' --include='*.go' .` |

Para Flask, `methods=` ausente significa `GET` (+ `HEAD`/`OPTIONS`). Para blueprints, componha `url_prefix` + rota.

---

## 9. Baseline de runtime (antes de qualquer mudança)

O baseline é o **oráculo** da Fase 3. Só são permitidas escritas em `.refactor-arch/` e instalações de dependências.

### 9.1 Ambiente isolado

```bash
# Python
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # ou: pip install -e . / poetry install
# Node
npm install            # ou npm ci se houver lockfile
```

Problemas conhecidos:

- **sqlite3 (Node) sem binding nativo** (`Could not locate the bindings file`, install script bloqueado): `cd node_modules/sqlite3 && npx prebuild-install -r napi` (não edite `package.json`). Alternativa: `npm rebuild sqlite3`.
- Pins antigos que não compilam no Python atual: tente instalar; se falhar, registre o erro e use a versão compatível mais próxima **só no venv**, anotando no baseline.
- Dependências declaradas mas não usadas instalam normalmente; anote para o finding de código morto.

### 9.2 Subir o app sem editar arquivos

1. Escolha uma porta livre: `lsof -nP -iTCP:<porta> -sTCP:LISTEN` (vazio = livre). Se a padrão estiver ocupada, use outra (ex.: 5001, 3001...).
2. Se porta/host/debug estão hardcoded, **não edite**; contorne:
   - Flask: `.venv/bin/flask --app <modulo> run --host 127.0.0.1 --port <porta>` (o bloco `__main__` não roda — veja se ele fazia init de DB/seed; se fizer, rode o init equivalente via `python -c` ou dispare a 1ª requisição).
   - FastAPI: `.venv/bin/uvicorn <modulo>:app --port <porta>`.
   - Node com porta em objeto de config exportado: `node -e "require('./<config>').<obj>.port=<porta>; require('./<entry>')"`. Se ler `process.env.PORT`: `PORT=<porta> npm start`.
3. Rode em background e salve o log: `... > .refactor-arch/baseline-server.log 2>&1 &` e guarde o PID.
4. Aguarde o boot (`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:<porta>/` em loop curto).
5. Bancos criados na 1ª requisição ou por script de seed: rode o seed antes (ex.: `python <script_de_seed>`, `npm run seed`) se o README mandar; apague bancos SQLite gerados **somente** se forem gitignored e você mesmo os criou, para baseline reprodutível.

### 9.3 Exercitar todas as rotas

Para cada rota: ao menos uma requisição válida (caminho feliz) e, quando barato, uma inválida (404 de id inexistente, 400 de payload faltando). Use os payloads do README, de arquivos `.http`/Postman ou inferidos do handler.

```bash
curl -s -X POST http://127.0.0.1:<porta>/<rota> -H 'Content-Type: application/json' \
  -d '{"campo":"valor"}' -w '\nHTTP %{http_code}\n'
```

Ordem: leituras primeiro, depois criações, atualizações e por fim deleções/resets (para não destruir dados que outras rotas usam). Endpoints destrutivos globais (reset de banco, SQL arbitrário): chame por último ou com payload inofensivo, e registre.

### 9.4 Formato de `.refactor-arch/baseline.md`

```markdown
# Baseline — <projeto>
Boot: `<comando exato>` (porta <p>) | Seed: `<comando ou "automático na 1ª requisição">`
Versões: <runtime> / <framework> / <libs relevantes>
| # | Método | Path | Payload | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | /items | - | 200 | lista de {id,nome,preco,...} (10 itens) |
Observações: warnings de deprecação no log, crashes, comportamentos suspeitos (ex.: dado sensível na resposta).
```

Encerre o servidor do baseline (`kill <PID>`; confirme com `lsof`) antes de seguir para a Fase 2.
