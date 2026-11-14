# Catálogo de Anti-Patterns (Fase 2)

Use este catálogo para varrer **todos** os arquivos-fonte. Para cada entrada: rode os sinais de detecção (grep), **leia** os trechos encontrados para confirmar (grep gera falso positivo) e registre `arquivo:linha` exatos com `grep -n` / `nl -ba`. Cada entrada aponta para o padrão de correção em [refactoring-playbook.md](refactoring-playbook.md).

## Escala de severidade

- **CRITICAL**: Falhas graves de arquitetura ou segurança que impedem o funcionamento correto, expõem dados sensíveis (ex: credenciais hardcoded, SQL Injection) ou violam completamente a separação de responsabilidades (ex: "God Class" contendo banco de dados, lógicas complexas e roteamento no mesmo arquivo).
- **HIGH**: Fortes violações do padrão MVC ou princípios SOLID que dificultam muito a manutenção e testes (ex: lógicas de negócio pesadas presas dentro de Controllers, forte acoplamento sem Injeção de Dependência, ou uso de estado global mutável em toda a aplicação).
- **MEDIUM**: Problemas de padronização, duplicação de código ou gargalos de performance moderada (ex: Queries N+1 no banco de dados, uso inadequado de middlewares, validações ausentes nas rotas).
- **LOW**: Melhorias de legibilidade, nomenclatura de variáveis ruins, ou "magic numbers" soltos pelo código.

Ajuste de severidade: a severidade abaixo é o padrão. Suba um nível quando houver evidência de impacto maior (ex.: falta de validação que **derruba o processo** → HIGH; endpoint sem auth que **executa SQL arbitrário** → CRITICAL). Nunca rebaixe um item de segurança comprovado.

## Índice

| ID | Anti-pattern | Severidade | Playbook |
|---|---|---|---|
| AP-01 | Credenciais / segredos hardcoded (inclui senhas de seed/fixture) | CRITICAL | PB-01, PB-25 |
| AP-02 | SQL Injection (concatenação / f-string / template literal) | CRITICAL | PB-02 |
| AP-03 | God Class / God File | CRITICAL | PB-03 |
| AP-04 | Exposição de dados sensíveis | CRITICAL | PB-06 |
| AP-05 | Hash de senha fraco, caseiro ou ausente | CRITICAL | PB-05 |
| AP-06 | Endpoints administrativos/destrutivos sem autenticação/autorização | CRITICAL | PB-07 |
| AP-07 | Debug ligado / bind em 0.0.0.0 no entry point | CRITICAL | PB-01, PB-16 |
| AP-08 | Regra de negócio dentro de rotas/controllers | HIGH | PB-04 |
| AP-09 | Estado global mutável / conexão compartilhada sem DI | HIGH | PB-17 |
| AP-10 | Escritas multi-etapa sem transação | HIGH | PB-09 |
| AP-11 | Sem módulo de config / app factory; efeitos colaterais no import | HIGH | PB-01, PB-16 |
| AP-12 | Erros engolidos, `except` genérico, sem error handler central (inclui 404 de rota inexistente), stack trace vazado | MEDIUM | PB-08, PB-23 |
| AP-13 | Queries N+1 / agregação em memória | MEDIUM | PB-10 |
| AP-14 | Validação de entrada ausente | MEDIUM | PB-11 |
| AP-15 | Código duplicado | MEDIUM | PB-18 |
| AP-16 | Callback hell | MEDIUM | PB-12 |
| AP-17 | APIs deprecated | MEDIUM | PB-13 |
| AP-18 | Middleware mal configurado (CORS aberto, sem middleware de auth/erro) | MEDIUM | PB-19 |
| AP-19 | Integridade referencial ausente / cascata manual | MEDIUM | PB-20 |
| AP-20 | Magic numbers / strings | LOW | PB-14 |
| AP-21 | Nomenclatura ruim / sombreamento de builtins | LOW | PB-18 |
| AP-22 | `print` / `console.log` como logging | LOW | PB-15 |
| AP-23 | Imports não usados / código morto / dependências não usadas | LOW | PB-18 |
| AP-24 | Token de autenticação previsível / não assinado / nunca verificado | CRITICAL | PB-21 |
| AP-25 | PII listada em endpoint sem autenticação | HIGH | PB-22 |
| AP-26 | Mensagem de resposta que contradiz o comportamento real | LOW | PB-24 |

Totais por severidade: **CRITICAL 8** (AP-01…07, AP-24) · **HIGH 5** (AP-08…11, AP-25) · **MEDIUM 8** (AP-12…19) · **LOW 5** (AP-20…23, AP-26) — **26 entradas**. Os IDs AP-24+ foram acrescentados depois; no relatório, ordene por severidade e, dentro dela, por ID.

Convenção dos comandos: `SRC` = lista de arquivos-fonte da Fase 1. Ex.: `grep -nE '<regex>' $SRC` ou `grep -rnE '<regex>' --include='*.py' . --exclude-dir={.venv,node_modules,.claude,.refactor-arch}`.

---

## AP-01 — Credenciais / segredos hardcoded · CRITICAL

**Descrição:** chaves secretas, senhas de banco/SMTP, tokens de API ou chaves de gateway escritos como literais no código-fonte.

**Sinais de detecção**
- Python: `grep -niE "(secret|passw|pwd|senha|token|api_?key|private_?key|smtp_?(user|pass))\w*\s*[=:]\s*['\"][^'\"]{3,}['\"]"`
- JS/TS: `grep -niE "(secret|pass|pwd|token|key|apiKey|dbUser|smtp)\w*\s*[:=]\s*['\"\`][^'\"\`]{3,}"`
- Neutro: `SECRET_KEY = '...'`, `app.config['SECRET_KEY'] = '...'`, objetos `config = { dbPass: '...' }`, prefixos `pk_live_`, `sk_live_`, `AKIA`, URLs `scheme://user:pass@host`.
- **Seed / fixtures / scripts:** varra também `seed*`, `fixtures*`, `scripts/`, `init_db*`, migrations e blocos de schema+seed dentro de `db/`/models. Senhas literais de contas iniciais (`password="admin123"`, `generate_password_hash("123456")`, `hashPassword('secret')`, `INSERT INTO ... VALUES (..., 'senha123')`) e senhas default (`password or "123456"`, `|| 'changeme'`) contam como AP-01 — registre no mesmo finding. Fallback literal em leitura de env (`os.environ.get("SEED_ADMIN_PASSWORD", "admin123")`) **continua sendo** AP-01.
  - `grep -rniE "(password|passwd|senha|pwd)\w*\s*[=:(]\s*['\"][^'\"]{3,}['\"]|hash\w*\(\s*['\"][^'\"]+['\"]" --include='seed*' --include='*fixture*' --include='init*' .` e leia os blocos `INSERT` de usuários/contas no seed.
- Falso positivo: nomes de campo (`'password': fields.Str()`), leitura de env **sem** default literal (`os.environ.get('SECRET_KEY')`), senha gerada com `secrets`/`crypto.randomBytes` (PB-25).

**Exemplo**
```python
app.config["SECRET_KEY"] = "changeme-secret-123"
```
```js
module.exports = { dbPass: "prod-db-pass", paymentKey: "live-payment-key" };
```
**Correção:** PB-01 (config/segredos) + PB-25 (senhas de seed/fixture).

---

## AP-02 — SQL Injection · CRITICAL

**Descrição:** SQL montado com valores externos por concatenação, f-string, `%`/`.format()` ou template literal.

**Sinais de detecção**
- Python: `grep -nE "execute\(\s*f['\"]|execute\([^)]*(\+|%|\.format\()|['\"](SELECT|INSERT|UPDATE|DELETE)[^'\"]*['\"]\s*\+|\+\s*['\"]\s*(WHERE|AND|OR|VALUES|SET)\b"`
- Também: `grep -nE "text\(\s*f['\"]"` (SQLAlchemy `text()` com f-string).
- JS/TS: ``grep -nE "\`\s*(SELECT|INSERT|UPDATE|DELETE)[^\`]*\\\$\{|['\"](SELECT|INSERT|UPDATE|DELETE)[^'\"]*['\"]\s*\+"``
- Neutro: SQL é string montada em vez de usar placeholders (`?`, `%s`, `:nome`, `$1`). Endpoint que executa SQL recebido do cliente é o caso extremo (registre também AP-06).
- Confirmação em runtime (opcional, só em baseline): um valor com aspa simples (`O'Reilly`) gerando erro de sintaxe SQL.

**Exemplo**
```python
cursor.execute("SELECT * FROM users WHERE email = '" + email + "'")
```
```js
db.all(`SELECT * FROM users WHERE name LIKE '%${term}%'`);
```
**Correção:** PB-02.

---

## AP-03 — God Class / God File · CRITICAL

**Descrição:** uma classe ou arquivo concentra conexão de banco, schema/seed, roteamento HTTP e regras de negócio de vários domínios.

**Sinais de detecção**
- Neutro: arquivo > ~250 linhas **ou** classe com > ~10 métodos que mistura ≥ 3 responsabilidades entre: rotas, SQL/ORM, regra de negócio, serialização, config.
- Comando: `wc -l $SRC | sort -rn | head` e, nos maiores, `grep -cE "route|router\.|app\.(get|post|put|delete)"` + `grep -cE "execute\(|SELECT|INSERT|db\.(run|get|all)\(|session\."`.
- Python: `grep -nE "^class |^def |@app\.route"` no arquivo, para ver domínios misturados.
- JS: `grep -nE "class \w+|new sqlite3\.Database|CREATE TABLE|app\.(get|post|put|delete)\("` no mesmo arquivo.
- Nomes típicos: `*Manager`, `utils` com regra de negócio, `models` único com todos os domínios + regras.

**Exemplo**
```js
class CoreManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seed */ }
  setupRoutes(app) { app.post('/checkout', (req, res) => { /* SQL + pagamento + resposta */ }); }
}
```
**Correção:** PB-03 (split) + PB-04 (services).

---

## AP-04 — Exposição de dados sensíveis · CRITICAL

**Descrição:** senha/hash/token retornado em JSON, segredos ou config interna em endpoint de health/info, dados de cartão/PII/segredos escritos em log.

**Sinais de detecção**
- Python: `grep -nE "['\"](password|senha|pass|password_hash|secret_key|token)['\"]\s*:"` em funções `to_dict`/serializers/respostas; `grep -nE "print\(.*(senha|password|email|card|cartao|token)"`.
- JS/TS: `grep -nE "console\.(log|info|error)\(.*(card|cc|pan|password|pass|key|token|secret)"`; `res\.json\(\w+\)` devolvendo a linha inteira do banco (`SELECT *` de usuários).
- Neutro: health/status endpoint que devolve `secret_key`, `db_path`, `debug`, variáveis de ambiente; respostas de usuários com campo de senha; `SELECT *` de tabela de usuários serializado direto.
- Runtime: conferir no baseline se alguma resposta contém chaves `password`/`senha`/`secret`.
- Fronteira: campos que **nunca** deveriam sair (senha, hash, segredo, token de terceiros, cartão) → AP-04. PII legítima (e-mail, telefone, documento, endereço) devolvida **sem auth** → AP-25.
- Falso positivo: script de seed que imprime **uma vez** a senha gerada aleatoriamente quando a variável de ambiente não foi definida (PB-25).

**Exemplo**
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
```js
console.log(`Charging card ${card} with key ${config.paymentKey}`);
```
**Correção:** PB-06.

---

## AP-05 — Hash de senha fraco, caseiro ou ausente · CRITICAL

**Descrição:** senha guardada em texto puro, com MD5/SHA1/SHA256 sem salt, Base64 ou algoritmo inventado; comparação com `==`; senha default (`"123456"`) quando o campo falta.

**Sinais de detecção**
- Python: `grep -nE "hashlib\.(md5|sha1|sha256)\(|base64\.b64encode\(.*(pass|senha)|==\s*\w*(password|senha)"`; colunas `senha TEXT`/`password` gravadas direto do request.
- JS/TS: `grep -nE "createHash\(['\"](md5|sha1|sha256)['\"]\)|Buffer\.from\([^)]*\)\.toString\(['\"]base64['\"]\)|\|\|\s*['\"]\d{3,}['\"]"`; funções com nome `crypto`/`hash`/`encrypt` que fazem loops/substrings.
- Neutro: ausência de `bcrypt`, `argon2`, `scrypt`, `pbkdf2`, `werkzeug.security`, `crypto.scrypt` em projeto que tem login/usuários.

**Exemplo**
```python
self.password = hashlib.md5(raw_password.encode()).hexdigest()
```
```js
const hash = Buffer.from(rawPassword).toString('base64').substring(0, 10);
```
**Correção:** PB-05.

---

## AP-06 — Endpoints administrativos/destrutivos sem auth · CRITICAL

**Descrição:** rotas `/admin/*`, reset de banco, execução de SQL, DELETE de usuários, promoção de papel (`role=admin`) ou relatórios financeiros acessíveis anonimamente. Token de login previsível/não verificado → AP-24; listagem de PII sem auth → AP-25.

**Sinais de detecção**
- Python: `grep -nE "route\(['\"][^'\"]*(admin|reset|query|delete|report)" ` e `grep -nE "methods=\[[^]]*DELETE"`; depois `grep -rnE "login_required|jwt_required|requires_auth|before_request|role_required" .` (ausência = finding).
- JS/TS: `grep -nE "(app|router)\.(delete|post|put|get)\(['\"][^'\"]*(admin|users/:|reset)"`; ausência de middleware (`authenticate`, `verifyToken`, `requireAdmin`, `passport`) entre path e handler.
- Neutro: campo `role` aceito do corpo em cadastro público, método `is_admin()` existente mas nunca usado.
- Severidade: CRITICAL se executa SQL/código arbitrário, reseta/apaga dados ou expõe relatórios financeiros/administrativos; HIGH se só falta auth em CRUD comum. Leitura de PII sem auth é AP-25 (não duplique).

**Exemplo**
```python
@app.route("/admin/sql", methods=["POST"])
def admin_query():
    return jsonify(db.execute(request.json["sql"]).fetchall())
```
**Correção:** PB-07 (e remover endpoints de SQL arbitrário).

---

## AP-07 — Debug ligado / bind em 0.0.0.0 · CRITICAL

**Descrição:** servidor iniciado com debugger interativo e/ou escutando em todas as interfaces, com porta fixa no código.

**Sinais de detecção**
- Python: `grep -nE "debug\s*=\s*True|DEBUG\s*=\s*True|host\s*=\s*['\"]0\.0\.0\.0|app\.run\("`
- JS/TS: `grep -nE "\.listen\(\s*\d{2,5}|port\s*:\s*\d{2,5}|NODE_ENV\s*[!=]==?\s*['\"]development"` sem `process.env.PORT`.
- Neutro: `debug`/`host`/`port` literais no entry point, health dizendo `"ambiente": "producao"` com debug ligado.

**Exemplo**
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```
**Correção:** PB-01 + PB-16.

---

## AP-08 — Regra de negócio em rotas/controllers · HIGH

**Descrição:** handlers HTTP que validam, calculam, consultam o banco, fazem commit, disparam notificações e serializam — tudo inline. Inclui "camada" `services/` existente mas não usada.

**Sinais de detecção**
- Neutro: handler com > ~30 linhas; handler contendo SQL/ORM (`execute(`, `.query.`, `db.session`, `db.run(`) **e** cálculos/decisões (`if total >`, descontos, status, contagens).
- Python: `grep -nE "db\.session\.(add|commit|delete)|\.query\.|execute\(" routes/*.py controllers*.py app.py` (ajuste os paths).
- JS: `grep -nE "db\.(run|get|all)\(" ` em arquivos que também contêm `router.`/`app.post(`.
- Services/utils órfãos: para cada módulo em `services/`/`utils/`, `grep -rn "<modulo>" --include=*.py --include=*.js .` sem resultado fora do próprio arquivo.

**Exemplo**
```python
@bp.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    total = 0
    for item in data["items"]:
        product = db.execute("SELECT price, stock FROM products WHERE id=?", (item["id"],)).fetchone()
        if product["stock"] < item["qty"]: return jsonify(error="sem estoque"), 400
        total += product["price"] * item["qty"]
    # ... INSERTs, baixa de estoque, notificações, resposta
```
**Correção:** PB-04.

---

## AP-09 — Estado global mutável / conexão compartilhada sem DI · HIGH

**Descrição:** conexão de banco global única reutilizada entre threads/requisições, caches/contadores de módulo mutáveis e exportados, dependências instanciadas dentro das classes (sem injeção).

**Sinais de detecção**
- Python: `grep -nE "^\s*global\s+\w+|check_same_thread\s*=\s*False|^[a-z_]+\s*=\s*(None|\{\}|\[\]|0)\s*$"`; `smtplib.SMTP(`/clientes criados dentro de métodos.
- JS/TS: `grep -nE "^(let|var)\s+\w+\s*=\s*(\{\}|\[\]|0|null)|module\.exports\s*=.*(cache|state|total)|new sqlite3\.Database\(|new \w+Client\("` dentro de construtores/módulos de negócio.
- Neutro: função `get_db()` que cria conexão global + schema + seed; objetos de cache de módulo sem limite; variáveis exportadas que nunca são lidas.

**Exemplo**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("app.db", check_same_thread=False)
    return db_connection
```
**Correção:** PB-17.

---

## AP-10 — Escritas multi-etapa sem transação · HIGH

**Descrição:** fluxo "verifica → insere A → insere B → atualiza C" sem `BEGIN/COMMIT/ROLLBACK`; falha no meio deixa dados parciais (cabeçalho sem itens, assinatura sem pagamento, conta órfã).

**Sinais de detecção**
- Neutro: função com ≥ 2 `INSERT`/`UPDATE`/`DELETE` (ou `session.add` + `commit` múltiplos) sem `BEGIN`, `with conn:`, `session.begin()`, `db.serialize`+`BEGIN`, `transaction(`.
- Python: `grep -nE "INSERT|UPDATE|DELETE|session\.(add|delete)|\.commit\(\)"` e conferir agrupamento por função; múltiplos `commit()` no mesmo handler.
- JS: callbacks `db.run('INSERT` aninhados; `grep -nE "BEGIN|COMMIT|ROLLBACK"` vazio.
- Também: leitura de estoque/saldo seguida de update sem condição (`UPDATE ... WHERE stock >= ?`) → condição de corrida.

**Exemplo**
```js
db.run('INSERT INTO subscriptions ...', [], function () {
  db.run('INSERT INTO payments ...', [this.lastID], () => {
    db.run('INSERT INTO audit_logs ...'); // erro ignorado, sem rollback
  });
});
```
**Correção:** PB-09.

---

## AP-11 — Sem config / app factory; efeitos colaterais no import · HIGH

**Descrição:** app criado como global de módulo com config inline, `create_all()`/schema/seed executados no import, impossível criar app de teste com outra config.

**Sinais de detecção**
- Python: ausência de `create_app(` e de `config.py`/`settings.py`; `grep -nE "^app\s*=\s*Flask\(|^db\.create_all\(\)|app\.config\[['\"]\w+['\"]\]\s*=\s*['\"]"`; `with app.app_context():` em nível de módulo.
- JS/TS: ausência de `config/` e `process.env`; `grep -rn "process\.env" src | wc -l` = 0; módulo que conecta ao banco e chama `listen` no import.
- Neutro: `python-dotenv`/`dotenv` instalado e não usado.

**Exemplo**
```python
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db.init_app(app)
with app.app_context():
    db.create_all()   # roda em qualquer import, inclusive em testes/seed
```
**Correção:** PB-01 + PB-16.

---

## AP-12 — Erros engolidos / sem error handler central / stack trace vazado · MEDIUM

**Descrição:** `except:` nu, `except Exception` que devolve `str(e)` ao cliente, callbacks que ignoram `err`, ausência de handler global (erros 4xx/5xx saem em HTML com stack trace), exceção não capturada que derruba o processo.

**Sinais de detecção**
- Python: `grep -nE "except\s*:|except Exception( as \w+)?:"`; `grep -nE "str\(e\)"`; ausência de `errorhandler(`/`register_error_handler(`.
- JS/TS: `grep -nE "function\s*\(err[^)]*\)\s*\{|\(err[^)]*\)\s*=>"` e conferir se `err` é checado; ausência de `app.use\(\s*\(err,\s*req,\s*res,\s*next\)`; `.catch(() => {})`.
- Neutro: cada handler com seu próprio try/except repetido; 404 retornado para erro de banco; respostas de erro em formatos mistos (texto vs JSON).
- **Rota inexistente fora do handler central:** API JSON/texto que responde a path desconhecido com a página HTML padrão do framework (`Cannot GET /x` do Express; página `404 Not Found` do Werkzeug).
  - Runtime (baseline): `curl -s -o /dev/null -w '%{http_code} %{content_type}\n' http://127.0.0.1:<p>/__rota-inexistente__` → `404 text/html` numa API que responde JSON/texto = finding. Repita com método não suportado numa rota existente (405).
  - Express: `grep -rnE "app\.use\(\s*\(\s*req\s*,\s*res(\s*,\s*next)?\s*\)\s*=>|NotFound" src` vazio (sem middleware catch-all registrado **depois** dos routers e **antes** do error middleware).
  - Flask: `grep -rnE "errorhandler\((404|405|HTTPException|NotFound)|register_error_handler\((404|HTTPException)" .` vazio. Atenção: `@bp.errorhandler(404)` em Blueprint **não** captura URLs que não casam com nenhuma rota — o handler precisa estar no app.
- Severidade HIGH se o erro **derruba o processo** (exceção em callback assíncrono sem try/catch).

**Exemplo**
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
```js
db.all(sql, [], (err, rows) => { res.json(rows.length); }); // err ignorado
```
**Correção:** PB-08 (+ PB-23 para 404/405 de rota inexistente).

---

## AP-13 — Queries N+1 / agregação em memória · MEDIUM

**Descrição:** uma query para a lista e mais uma por item (e por subitem); contagens feitas carregando tudo em Python/JS; vários `COUNT` separados em vez de `GROUP BY`.

**Sinais de detecção**
- Python: `grep -nE -A6 "^\s*for \w+ in " | grep -E "execute\(|\.query\.|session\.(get|execute)|\.get\("`; acesso a relacionamento lazy em loop (`len(user.orders)`); muitos `.count()` seguidos.
- JS: `grep -nE -A6 "forEach|for \(|\.map\(" | grep -E "db\.(get|all)\("`; contadores manuais (`pending--`, `if (pending === 0)`).
- Neutro: número de queries cresce com o número de linhas retornadas.

**Exemplo**
```python
for order in orders:
    items = db.execute("SELECT * FROM items WHERE order_id = ?", (order["id"],)).fetchall()
```
**Correção:** PB-10.

---

## AP-14 — Validação de entrada ausente · MEDIUM

**Descrição:** campos do request usados sem checar presença, tipo, faixa e formato; `float()/int()` sem tratamento; corpo `null`; recurso inexistente retornando 200.

**Sinais de detecção**
- Python: `grep -nE "request\.(json|get_json\(\))\[|data\[['\"]\w+['\"]\]|(int|float)\(request\.args|dados\.get\(|data\.get\("` e verificar se existe checagem antes.
- JS/TS: `grep -nE "req\.body\.\w+|req\.params\.\w+|req\.query\.\w+"` usados direto em SQL/lógica, `.startsWith(`/`.toFixed(` em campos não validados.
- Neutro: comparações numéricas com valor possivelmente string (`preco < 0`), quantidade negativa aceita, e-mail sem formato, libs de validação (marshmallow, pydantic, joi, zod) instaladas e não usadas.

**Exemplo**
```js
const status = req.body.card.startsWith('4') ? 'PAID' : 'DENIED'; // card numérico derruba o processo
```
**Correção:** PB-11.

---

## AP-15 — Código duplicado · MEDIUM

**Descrição:** blocos copiados (row→dict, serialização manual, regra de atraso/desconto, validações, listas de status) que já divergem entre si.

**Sinais de detecção**
- Ferramentas: `npx jscpd --min-lines 5 <dirs>` (qualquer linguagem) ou `pylint --disable=all --enable=duplicate-code`.
- Grep: mesma lista literal em vários lugares `grep -rnE "\[['\"](pending|active|done|closed)" `; mesma regex de e-mail repetida; funções `to_dict` existentes mas serialização manual nas rotas.
- Neutro: helper/método pronto (`is_expired`, `validate_*`) nunca chamado enquanto a lógica é reescrita inline.

**Correção:** PB-18.

---

## AP-16 — Callback hell · MEDIUM

**Descrição:** fluxo assíncrono por callbacks aninhados (≥ 3 níveis), contadores manuais para sincronizar, `self = this` para acessar `this.lastID`.

**Sinais de detecção**
- JS/TS: `grep -nE "\.(run|get|all|each)\(.*(function\s*\(|\(err[^)]*\)\s*=>)"` e conferir indentação; `grep -nE "let self = this|const self = this|pending\w*--"`.
- Python (equivalente): callbacks aninhados em libs assíncronas antigas; raro.

**Exemplo**
```js
db.get(q1, [a], (e1, r1) => { db.get(q2, [b], (e2, r2) => { db.run(q3, [], function (e3) { res.json({ id: this.lastID }); }); }); });
```
**Correção:** PB-12.

---

## AP-17 — APIs deprecated · MEDIUM

**Descrição:** uso de APIs obsoletas/removidas da linguagem, framework ou ORM. Reporte **um finding agregado** "Deprecated APIs" listando cada API com suas linhas. Veja a tabela completa na seção [APIs deprecated](#apis-deprecated). Se a versão instalada já removeu a API (quebra em runtime), suba para HIGH.

**Correção:** PB-13.

---

## AP-18 — Middleware mal configurado · MEDIUM

**Descrição:** CORS liberado para qualquer origem (inclusive rotas admin), ausência de camada de middleware para auth/erros/logging, middlewares registrados em ordem errada (error handler antes das rotas no Express).

**Sinais de detecção**
- Python: `grep -nE "CORS\(app\)\s*$|origins\s*=\s*['\"]\*"`.
- JS/TS: `grep -nE "cors\(\)|origin:\s*['\"]\*|app\.use\(cors"`; error middleware `app.use((err, ...` registrado antes de `app.use(router)`.

**Correção:** PB-19.

---

## AP-19 — Integridade referencial ausente / cascata manual · MEDIUM

**Descrição:** schema sem `FOREIGN KEY`/`UNIQUE`/`NOT NULL`; deleção que deixa filhos órfãos; cascata feita com loop manual na rota; SQLite sem `PRAGMA foreign_keys = ON`.

**Sinais de detecção**
- `grep -niE "create table" -A12 | grep -ciE "foreign key|references|unique"` = 0.
- Python ORM: `ForeignKey(` sem `ondelete`, `relationship(` sem `cascade`; loops `for child in parent.children: db.session.delete(child)`.
- JS: `DELETE FROM users` sem tratar tabelas filhas; mensagens do tipo "dados relacionados mantidos".

**Correção:** PB-20.

---

## AP-20 — Magic numbers / strings · LOW

**Descrição:** literais de domínio sem nome (faixas de desconto, limites de tamanho, status, papéis, prefixo de cartão, porta, versão) espalhados e repetidos.

**Sinais de detecção**
- Python/JS: `grep -nE "[<>]=?\s*[0-9]{2,}|\*\s*0\.[0-9]+|==\s*['\"][a-z_]+['\"]|startsWith\(['\"][0-9]"`; listas literais de categorias/status em `if x not in [...]`.
- Neutro: constantes já definidas em `utils/`/`constants` mas não usadas.

**Exemplo**
```python
if total > 10000: discount = total * 0.1
```
**Correção:** PB-14.

---

## AP-21 — Nomenclatura ruim / sombreamento · LOW

**Descrição:** variáveis de 1–2 letras ou abreviações crípticas (`u`, `e`, `p`, `cc`, `cur2`, `p1..p5`), nomes genéricos (`Manager`, `data`, `result`), parâmetros que sombreiam builtins (`id`, `type`, `list`).

**Sinais de detecção**
- Python: `grep -nE "def \w+\([^)]*\b(id|type|list|dict|input)\b|\b[a-z][0-9]?\s*=\s*"`.
- JS/TS: `grep -nE "\b(let|const|var)\s+[a-z]{1,2}\b\s*="`.
- Campos de API crípticos (`nm`, `em`, `pw`, `x_id`): registre, mas **não renomeie contrato HTTP** (ver regras de preservação no playbook).

**Correção:** PB-18.

---

## AP-22 — `print` / `console.log` como logging · LOW

**Descrição:** logs sem nível/formatação via `print`/`console.log`, muitas vezes simulando notificações. Se o log contém dado sensível, registre também AP-04.

**Sinais de detecção**
- Python: `grep -nE "^\s*print\("`
- JS/TS: `grep -nE "console\.(log|info|warn|error|debug)\("`
- Falso positivo: saída de CLI de scripts de seed/manutenção (ex.: senha gerada impressa uma vez, PB-25) — não é logging da aplicação.

**Correção:** PB-15.

---

## AP-23 — Imports não usados / código morto / dependências não usadas · LOW

**Descrição:** imports sem uso, funções/classes/módulos nunca chamados, variáveis exportadas e nunca lidas, pacotes no manifesto que nenhum arquivo importa.

**Sinais de detecção**
- Python: `.venv/bin/python -m pyflakes $SRC` ou `ruff check --select F401,F841 .` (se disponível, sem instalar no projeto: `pipx run ruff ...`); manual: para cada `import x`, `grep -c "\bx\." arquivo`.
- JS/TS: `npx eslint --no-eslintrc --rule '{"no-unused-vars":"error"}' src` (se disponível); manual: para cada nome em `require`/`import`, contar usos.
- Dependências: ver `project-analysis.md` seção 3.

**Correção:** PB-18.

---

## AP-24 — Token de autenticação previsível / não assinado · CRITICAL

**Descrição:** login devolve token montado por concatenação ou codificação reversível (`'fake-jwt'`, `'token-' + id`, `f"token-{id}"`, Base64 do id/e-mail, UUID guardado em memória e nunca conferido) ou token que **nenhuma rota verifica**. Qualquer cliente forja o token de outro usuário → bypass de auth / personificação.

**Sinais de detecção**
- Python: `grep -rnE "(fake|dummy|mock)[-_]?(jwt|token)|f['\"]token-\{|['\"]token-['\"]\s*\+|b64encode\(\s*(str\(|f['\"])|uuid4\(\)" --include='*.py' .`
- JS/TS: ``grep -rnE "(fake|dummy|mock)[-_]?(jwt|token)|['\"]token-['\"]\s*\+|\`token-\$\{|Buffer\.from\(\s*String\([^)]*\)\s*\)\.toString\(['\"]base64|randomUUID\(\)" src``
- Consumidor ausente: `grep -rnE "verify_token|verifyToken|jwt\.(decode|verify)|serializer\.loads|\.loads\(\s*token|headers\.get\(['\"]Authorization|req\.(get|header)\(['\"]Authorization|headers\.authorization" --include='*.py' --include='*.js' .` sem resultado = token emitido e nunca validado (CORS `allow_headers` não conta).
- Neutro: token sem assinatura (HMAC/JWT) nem expiração; mesmo token para o mesmo usuário em todo login; token que contém o id em claro sem MAC.
- Runtime (baseline): faça login duas vezes e compare o campo de token; registre o formato observado (ex.: `"token": "token-1"`).
- Falso positivo: JWT/`itsdangerous` com segredo vindo de config **e** verificado por middleware/decorator.

**Exemplo**
```python
return jsonify({"token": f"token-{user['id']}"})
```
```js
res.json({ token: 'fake-jwt-' + user.id });
```
**Correção:** PB-21.

---

## AP-25 — PII listada em endpoint sem autenticação · HIGH

**Descrição:** rotas de listagem/detalhe de contas/pessoas/clientes que devolvem e-mail, telefone, documento (CPF/CNPJ/SSN), endereço ou data de nascimento a qualquer cliente anônimo. Permite enumeração e scraping de dados pessoais. Suba para **CRITICAL** se a resposta também incluir credenciais/hash/token (registre a parte de credencial em AP-04).

**Sinais de detecção**
- Enumeração: use a tabela de rotas da Fase 1; marque `GET` de coleção e `GET /<recurso>/<id>` cujo recurso tem campos pessoais.
- Campos serializados: `grep -rnE "['\"](email|e_mail|phone|telefone|celular|cpf|cnpj|document|documento|ssn|address|endereco|birth|nascimento)['\"]" --include='*.py' --include='*.js' .` em `to_dict`/serializers/`SELECT` e respostas.
- Guard ausente: na definição da rota, nenhum decorator/middleware de auth (`login_required`, `require_auth`, `jwt_required`, `authenticate`, `requireAuth`, `passport.authenticate`) e nenhum `before_request`/`router.use(auth)` cobrindo o prefixo.
- Runtime (baseline): `curl` anônimo na listagem retorna 200 com campos pessoais.

**Exemplo**
```python
@bp.route("/accounts", methods=["GET"])
def list_accounts():
    return jsonify([a.to_dict() for a in Account.query.all()])   # inclui email/phone, sem auth
```
**Correção:** PB-22 (com PB-21 para o token).

---

## AP-26 — Mensagem de resposta que contradiz o comportamento real · LOW

**Descrição:** strings literais de resposta/log que descrevem efeito colateral inexistente ou estado falso: "não implementado"/"TODO" em rota que funciona, "e-mail enviado" sem envio, "dados relacionados mantidos (podem ficar inconsistentes)" depois que a cascata foi corrigida, "pagamento processado" quando nada é gravado. Confunde clientes e operadores. Suba para **MEDIUM** se a mensagem induz decisão errada sobre integridade, segurança ou dinheiro.

**Sinais de detecção**
- `grep -rniE "(message|mensagem|msg|detail|status)['\"]?\s*[:=,]\s*['\"][^'\"]*(todo|n[aã]o implementad|not implemented|mantid|inconsistent|[oó]rf[aã]|simulad|fake|tempor[aá]ri|em breve|enviad|sent)" --include='*.py' --include='*.js' .`
- Leitura dirigida: para cada string literal de sucesso/erro em handlers, confira se o código realmente faz o que ela diz (envia, apaga, preserva, cobra). Repita a checagem **depois** da Fase 3: correções podem tornar mensagens antigas falsas.

**Exemplo**
```python
db.session.delete(parent); db.session.commit()   # cascade já remove os filhos
return jsonify({"mensagem": "Registro removido; itens relacionados mantidos"}), 200
```
**Correção:** PB-24.

---

## APIs deprecated

Rode **todos** os greps relevantes para a stack. Cada ocorrência confirmada entra no finding agregado "Deprecated APIs" (AP-17) com `arquivo:linha`. Se nada for encontrado, registre no relatório a linha `Deprecated APIs: nenhuma ocorrência (greps executados: ...)`.

### Python / Flask / SQLAlchemy

| API deprecated | Equivalente moderno | Grep de detecção |
|---|---|---|
| `datetime.utcnow()` / `datetime.utcfromtimestamp()` (deprecated no Python 3.12) | `datetime.now(timezone.utc)` / `datetime.fromtimestamp(ts, timezone.utc)` | `grep -nE "utcnow\(\)|utcfromtimestamp\("` |
| `Model.query.get(id)` (legado no SQLAlchemy 2.x) | `db.session.get(Model, id)` ou `db.get_or_404(Model, id)` | `grep -nE "\.query\.get\("` |
| `Model.query.filter_by(...).all()/first()/count()` (Query API legada) | `db.session.execute(db.select(Model).filter_by(...)).scalars().all()`, `db.session.scalar(db.select(db.func.count()).select_from(Model))` | `grep -nE "\b[A-Z]\w*\.query\."` |
| `Model.query.get_or_404` / `first_or_404` | `db.get_or_404(Model, id)` / `db.first_or_404(db.select(...))` | `grep -nE "query\.(get|first)_or_404"` |
| `@app.before_first_request` (removido no Flask 2.3) | executar dentro de `create_app()` com `app.app_context()` ou comando CLI | `grep -nE "before_first_request"` |
| `flask.json.JSONEncoder` / `app.json_encoder` (removidos no Flask 2.3) | `app.json = CustomJSONProvider(app)` (`flask.json.provider.DefaultJSONProvider`) | `grep -nE "JSONEncoder|json_encoder"` |
| `flask._app_ctx_stack` / `_request_ctx_stack` | `flask.g`, `current_app` | `grep -nE "_app_ctx_stack|_request_ctx_stack"` |
| `send_file(..., attachment_filename=)` | `download_name=` | `grep -nE "attachment_filename"` |
| `hashlib.md5` / `sha1` / `sha256` para senhas | `werkzeug.security.generate_password_hash`/`check_password_hash`, `bcrypt`, `argon2-cffi` | `grep -nE "hashlib\.(md5|sha1|sha256)"` |
| `declarative_base()` de `sqlalchemy.ext.declarative` | `sqlalchemy.orm.DeclarativeBase` | `grep -nE "ext\.declarative"` |
| `engine.execute()` / `session.execute("SQL cru")` sem `text()` | `conn.execute(text(...), params)` | `grep -nE "engine\.execute\(|execute\(['\"](SELECT|INSERT|UPDATE|DELETE)"` |
| `type(x) == list` | `isinstance(x, list)` | `grep -nE "type\(\w+\)\s*==" ` |

### Node.js / Express

| API deprecated | Equivalente moderno | Grep de detecção |
|---|---|---|
| `new Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` | `grep -nE "new Buffer\("` |
| `crypto.createCipher` / `createDecipher` | `crypto.createCipheriv` / `createDecipheriv` com IV aleatório | `grep -nE "createCipher\(|createDecipher\("` |
| `url.parse(str)` | `new URL(str, base)` | `grep -nE "url\.parse\("` |
| pacote `body-parser` | `express.json()` / `express.urlencoded({ extended: true })` (Express ≥ 4.16) | `grep -nE "body-parser|bodyParser\."` |
| API callback do `sqlite3` (`db.run/get/all(sql, params, cb)`) | wrapper com Promise (`util.promisify` / função `run/get/all` async) ou `better-sqlite3`/`sqlite` | `grep -nE "\.(run|get|all|each)\(.*(function\s*\(|=>)"` (use `.*`: o SQL costuma conter `)`, então `[^)]*` não casa) |
| `var` | `const` / `let` | `grep -nE "^\s*var\s"` |
| `fs.exists()` | `fs.existsSync()` ou `fs.promises.access()` | `grep -nE "fs\.exists\("` |
| `req.param('x')` (removido no Express 5) | `req.params.x` / `req.query.x` / `req.body.x` | `grep -nE "req\.param\("` |
| `res.send(status, body)` / `res.json(status, body)` (removido no Express 5) | `res.status(status).send(body)` / `.json(body)` | `grep -nE "res\.(send|json)\(\s*[0-9]{3}\s*,"` |
| `res.sendfile()` | `res.sendFile()` | `grep -nE "res\.sendfile\("` |
| `app.del()` | `app.delete()` | `grep -nE "app\.del\("` |
| `require('querystring')` | `URLSearchParams` | `grep -nE "require\(['\"]querystring"` |
| `util.isArray` / `util.isString` etc. | `Array.isArray` / `typeof` | `grep -nE "util\.is[A-Z]"` |
| `crypto.createHash('md5'/'sha1')` para senhas | `crypto.scrypt` com salt aleatório, `bcrypt`, `argon2` | `grep -nE "createHash\(['\"](md5|sha1)"` |

### Outras stacks (referência rápida)

| Stack | Deprecated → moderno |
|---|---|
| Django | `url()` → `path()/re_path()`; `ugettext` → `gettext` |
| Java/Spring | `WebSecurityConfigurerAdapter` → bean `SecurityFilterChain`; `new Date()` → `java.time` |
| Go | `ioutil.*` → `io`/`os` |
| PHP | `mysql_*` → PDO com prepared statements; `md5()` para senha → `password_hash()` |
