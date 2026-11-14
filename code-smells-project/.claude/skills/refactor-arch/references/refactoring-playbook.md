# Playbook de Refatoração (Fase 3)

Padrões concretos de transformação. Cada padrão (PB-xx) indica os anti-patterns que resolve (AP-xx, ver [anti-patterns-catalog.md](anti-patterns-catalog.md)) e mostra ANTES/DEPOIS. Os exemplos são curtos: adapte nomes ao domínio do projeto, **sem** mudar URLs nem contratos JSON.

Leia primeiro as [Regras de preservação de comportamento](#regras-de-preservação-de-comportamento) no fim deste arquivo.

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
| PB-21 | Token de login assinado e com expiração + guard `require_auth` | AP-24 |
| PB-22 | Proteger listagens/detalhes com PII (auth; dono ou admin) | AP-25 |
| PB-23 | Catch-all 404/405 → error handler central | AP-12 |
| PB-24 | Corrigir mensagens de resposta enganosas | AP-26 |
| PB-25 | Senhas de seed/fixture vindas do ambiente | AP-01 |

---

## PB-01 — Extrair config para variáveis de ambiente (AP-01, AP-07, AP-11)

ANTES (Python)
```python
app.config["SECRET_KEY"] = "changeme-secret-123"
app.run(host="0.0.0.0", port=5000, debug=True)
```
DEPOIS
```python
# config/settings.py
import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "app.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-admin-token")
```
ANTES (JS)
```js
module.exports = { config: { dbPass: "prod-db-pass", paymentKey: "live-payment-key", port: 3000 } };
```
DEPOIS
```js
// src/config/index.js
const config = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  dbPath: process.env.DB_PATH || ':memory:',
  dbPass: process.env.DB_PASS || '',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  secretKey: process.env.SECRET_KEY || 'dev-only-insecure-key',   // assina tokens (PB-21)
  tokenTtl: Number(process.env.TOKEN_TTL) || 3600,
  adminToken: process.env.ADMIN_TOKEN || '',                      // vazio = admin desabilitado
});
module.exports = { config };
```
Regras: defaults servem **só** para dev e não são segredos reais (o valor vazado deve ser considerado comprometido — nunca o reutilize como default). Crie `.env.example` com todas as chaves e valores fictícios. Use `python-dotenv`/`dotenv` apenas se já forem dependências; senão leia o ambiente puro (`os.environ` / `process.env`; em Node ≥ 20.6 há `node --env-file=.env`). Em produção (`APP_ENV=production`), falhe no boot se um segredo obrigatório estiver vazio **ou igual ao default de dev** (o `SECRET_KEY` assina tokens no PB-21; um default público permite forjá-los).

---

## PB-02 — Queries parametrizadas (AP-02)

ANTES (Python)
```python
cursor.execute("SELECT * FROM users WHERE email = '" + email + "' AND active = 1")
cursor.execute("SELECT * FROM products WHERE name LIKE '%" + term + "%'")
```
DEPOIS
```python
cursor.execute("SELECT * FROM users WHERE email = ? AND active = 1", (email,))
cursor.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{term}%",))
```
Filtros dinâmicos: monte só a **estrutura** com strings fixas e os **valores** como parâmetros.
```python
clauses, params = ["1=1"], []
if category:
    clauses.append("category = ?"); params.append(category)
if min_price is not None:
    clauses.append("price >= ?"); params.append(min_price)
rows = conn.execute(f"SELECT * FROM products WHERE {' AND '.join(clauses)}", params).fetchall()
```
ANTES (JS)
```js
db.all(`SELECT * FROM plans WHERE id = ${req.params.id}`);
```
DEPOIS
```js
const plan = await db.get('SELECT * FROM plans WHERE id = ?', [req.params.id]);
```
Nomes de coluna/ordenação vindos do cliente: valide contra uma whitelist (`if (!['name','price'].includes(sort)) ...`), nunca interpole direto.

---

## PB-03 — Quebrar God class em model / controller / route (AP-03)

ANTES (JS, tudo numa classe)
```js
class CoreManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  setupRoutes(app) {
    app.get('/api/plans/:id', (req, res) => {
      this.db.get('SELECT * FROM plans WHERE id = ?', [req.params.id], (err, row) => {
        if (!row) return res.status(404).send('Not found');
        res.json(row);
      });
    });
  }
}
```
DEPOIS
```js
// src/models/plan.model.js
const createPlanModel = (db) => ({
  findById: (id) => db.get('SELECT * FROM plans WHERE id = ?', [id]),
});
module.exports = { createPlanModel };

// src/controllers/plan.controller.js
const { NotFoundError } = require('../errors/AppError');
const createPlanController = ({ planModel }) => ({
  async getById(id) {
    const plan = await planModel.findById(id);
    if (!plan) throw new NotFoundError('Not found');
    return plan;
  },
});
module.exports = { createPlanController };

// src/routes/plan.routes.js
const { Router } = require('express');
const asyncHandler = require('../middlewares/asyncHandler');
module.exports = (controller) => {
  const router = Router();
  router.get('/api/plans/:id', asyncHandler(async (req, res) => {
    res.json(await controller.getById(req.params.id));
  }));
  return router;
};
```
Python equivalente: `models/<entidade>_model.py` (funções/classe com SQL), `controllers/<entidade>_controller.py` (caso de uso), `views/<entidade>_routes.py` (Blueprint). Depois do split, **apague** o arquivo original ou reduza-o ao entry point.

---

## PB-04 — Controller fino + service para regra de negócio (AP-08)

ANTES (Python)
```python
@bp.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    total = 0
    for item in data["items"]:
        product = conn.execute("SELECT price, stock FROM products WHERE id = ?", (item["product_id"],)).fetchone()
        if product["stock"] < item["quantity"]:
            return jsonify({"error": "Estoque insuficiente"}), 400
        total += product["price"] * item["quantity"]
    order_id = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (data["user_id"], total)).lastrowid
    conn.commit()
    return jsonify({"id": order_id, "total": total}), 201
```
DEPOIS
```python
# services/order_service.py
from errors import ValidationError

class OrderService:
    def __init__(self, order_model, product_model):
        self.orders, self.products = order_model, product_model

    def create(self, user_id, items):
        total = 0
        for item in items:
            product = self.products.find_by_id(item["product_id"])
            if product is None or product["stock"] < item["quantity"]:
                raise ValidationError("Estoque insuficiente")
            total += product["price"] * item["quantity"]
        return self.orders.create_with_items(user_id, items, total)  # transação no model (PB-09)

# views/order_routes.py
@bp.route("/orders", methods=["POST"])
def create_order():
    data = validate_order_payload(request.get_json(silent=True))  # PB-11
    order = order_controller.create(data["user_id"], data["items"])
    return jsonify(order), 201
```
Regra: rota = parse + chamada + serialização. Toda decisão de negócio (`if`, cálculos, efeitos colaterais) vive no service/controller.

---

## PB-05 — Hash de senha forte (AP-05)

ANTES (Python)
```python
import hashlib
user.password = hashlib.md5(raw_password.encode()).hexdigest()
ok = user.password == hashlib.md5(raw_password.encode()).hexdigest()
```
DEPOIS
```python
from werkzeug.security import generate_password_hash, check_password_hash
user.password = generate_password_hash(raw_password)          # scrypt/pbkdf2 com salt
ok = check_password_hash(user.password, raw_password)          # comparação em tempo constante
```
Login com SQL: busque por e-mail (parametrizado) e verifique o hash em código — nunca `WHERE senha = ?`.

ANTES (JS)
```js
const weakHash = (p) => Buffer.from(p).toString('base64').substring(0, 10);
```
DEPOIS
```js
const crypto = require('node:crypto');
const { promisify } = require('node:util');
const scrypt = promisify(crypto.scrypt);

async function hashPassword(plain) {
  const salt = crypto.randomBytes(16).toString('hex');
  const key = await scrypt(plain, salt, 64);
  return `scrypt$${salt}$${key.toString('hex')}`;
}
async function verifyPassword(plain, stored) {
  const [scheme, salt, hex] = String(stored).split('$');
  if (scheme !== 'scrypt') return false;
  const key = await scrypt(plain, salt, 64);
  const expected = Buffer.from(hex, 'hex');
  return expected.length === key.length && crypto.timingSafeEqual(expected, key);
}
```
Seed: grave as senhas de seed já com hash; os valores em texto vêm do ambiente (PB-25), nunca literais no script. O validador define essas variáveis com os valores de dev do baseline para que os logins continuem funcionando. Bancos persistentes com hashes antigos: aceite o formato legado no login e regrave com o novo hash (registre em Remaining Known Issues). Senha default quando o campo falta (`password || "123456"`): troque por validação obrigatória **só se** o baseline não depende disso; senão, gere senha aleatória e documente.

---

## PB-06 — Remover dados sensíveis de respostas e logs (AP-04)

ANTES
```python
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}

@app.route("/health")
def health():
    return jsonify({"status": "ok", "secret_key": app.config["SECRET_KEY"], "db_path": DB_PATH})
```
DEPOIS
```python
SENSITIVE_FIELDS = {"password", "senha", "password_hash"}

def to_dict(self):
    return {"id": self.id, "email": self.email}

@app.route("/health")
def health():
    return jsonify({"status": "ok"})   # mantenha as demais chaves não sensíveis do original
```
ANTES (JS)
```js
console.log(`Charging card ${card} with key ${config.paymentGatewayKey}`);
```
DEPOIS
```js
logger.info('Charging card', { cardLast4: String(card).slice(-4) });
```
Em SQL, prefira colunas explícitas (`SELECT id, name, email FROM users`) a `SELECT *` + serialização da linha inteira.

---

## PB-07 — Auth em rotas admin/destrutivas (AP-06)

ANTES (Python)
```python
@app.route("/admin/wipe", methods=["POST"])
def wipe_data(): ...
```
DEPOIS
```python
# middlewares/auth.py
import hmac
from functools import wraps
from flask import current_app, request
from errors import UnauthorizedError

def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "").encode()
        # bytes: compare_digest(str, str) lança TypeError com header não-ASCII (vira 500)
        expected = current_app.config["ADMIN_TOKEN"].encode()
        if not (token and expected and hmac.compare_digest(token, expected)):   # vazio = admin desabilitado
            raise UnauthorizedError("Não autorizado")
        return view(*args, **kwargs)
    return wrapper

@bp.route("/admin/wipe", methods=["POST"])
@require_admin
def wipe_data(): ...
```
ANTES (JS)
```js
app.delete('/api/users/:id', handler);
```
DEPOIS
```js
// src/middlewares/auth.js
const crypto = require('node:crypto');
module.exports = (config) => (req, res, next) => {
  const token = Buffer.from(req.get('X-Admin-Token') || '');
  const expected = Buffer.from(config.adminToken);
  // token/ADMIN_TOKEN vazio = admin desabilitado (dois buffers vazios seriam "iguais")
  if (!expected.length || token.length !== expected.length || !crypto.timingSafeEqual(token, expected)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};
router.delete('/api/users/:id', requireAdmin, asyncHandler(handler));
```
Regras:
- `ADMIN_TOKEN` ausente ou vazio = admin **desabilitado** (sempre 401), nunca aberto.
- Documente no `.env.example` e no bloco da Fase 3 **como o validador obtém o token** (header, variável, valor default de dev) para que o endpoint original continue respondendo 200 quando chamado com credencial.
- Endpoint que executa SQL arbitrário: mantenha a rota (preservação), exija admin e restrinja a uma única instrução `SELECT` somente-leitura; recomende removê-lo em Remaining Known Issues.
- Campo `role`/`is_admin` vindo do corpo em cadastro público: ignore ou exija admin para definir.

---

## PB-08 — Error handler centralizado + exceções de domínio (AP-12)

ANTES (Python)
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
DEPOIS
```python
# errors.py
class AppError(Exception):
    status_code = 500
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code: self.status_code = status_code
class ValidationError(AppError): status_code = 400
class UnauthorizedError(AppError): status_code = 401
class ForbiddenError(AppError): status_code = 403
class NotFoundError(AppError): status_code = 404

# middlewares/error_handler.py
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException
from errors import AppError

logger = logging.getLogger(__name__)
ERROR_KEY = "erro"   # mesma chave de erro usada pelo projeto original

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({ERROR_KEY: err.message}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({ERROR_KEY: err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("Erro não tratado")
        return jsonify({ERROR_KEY: "Erro interno do servidor"}), 500
```
ANTES (JS)
```js
db.all(sql, [], (err, rows) => { res.json(rows); }); // err ignorado
```
DEPOIS
```js
// src/middlewares/asyncHandler.js (Express 4 não captura rejeições de Promise)
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// src/middlewares/errorHandler.js — registrar DEPOIS das rotas
const { AppError } = require('../errors/AppError');
module.exports = (logger) => (err, req, res, next) => {
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON inválido' });
  if (err instanceof AppError) return res.status(err.statusCode).json({ error: err.message });
  logger.error('Erro não tratado', { message: err.message, stack: err.stack });
  res.status(500).json({ error: 'Erro interno do servidor' });
};
```
JS: `src/errors/AppError.js` exporta as mesmas classes (`ValidationError` 400, `UnauthorizedError` 401, `ForbiddenError` 403, `NotFoundError` 404) com `statusCode`. Rotas inexistentes também passam por aqui: ver PB-23.

Mantenha a **chave** e o **formato** de erro que o projeto já usava (`erro`, `error`, `message` ou texto puro) quando o baseline depende dele. Nunca devolva `str(e)`/stack trace ao cliente.

---

## PB-09 — Transação em escritas multi-etapa (AP-10)

ANTES (Python sqlite3)
```python
cur.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))
order_id = cur.lastrowid
for item in items:
    cur.execute("INSERT INTO order_items (order_id, product_id, qty) VALUES (?, ?, ?)", (order_id, item["id"], item["qty"]))
    cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (item["qty"], item["id"]))
conn.commit()
```
DEPOIS
```python
with conn:  # commit no sucesso, rollback em exceção
    order_id = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total)).lastrowid
    for item in items:
        conn.execute("INSERT INTO order_items (order_id, product_id, qty) VALUES (?, ?, ?)", (order_id, item["id"], item["qty"]))
        updated = conn.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (item["qty"], item["id"], item["qty"]),
        ).rowcount
        if updated == 0:
            raise ValidationError("Estoque insuficiente")
```
SQLAlchemy (Flask-SQLAlchemy): faça todos os `add`/`delete` e **um** `commit`; em erro, `rollback`.
```python
try:
    db.session.add(order); db.session.add_all(items)
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```
JS (com o wrapper do PB-12): serialize transações na mesma conexão.
```js
// dentro de createDb(rawDb) — fila por conexão, evita "cannot start a transaction within a transaction"
let queue = Promise.resolve();
function withTransaction(work) {
  const result = queue.then(async () => {
    await run('BEGIN');
    try { const value = await work(); await run('COMMIT'); return value; }
    catch (err) { await run('ROLLBACK'); throw err; }
  });
  queue = result.catch(() => {});
  return result;
}
```
Decida regras (ex.: pagamento aprovado?) **antes** de gravar, para não criar registros órfãos.

---

## PB-10 — Eliminar N+1 (AP-13)

ANTES (Python)
```python
orders = conn.execute("SELECT * FROM orders").fetchall()
for o in orders:
    o_items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (o["id"],)).fetchall()
```
DEPOIS
```python
rows = conn.execute("""
    SELECT o.id AS order_id, o.total, i.product_id, i.qty, p.name AS product_name
    FROM orders o
    LEFT JOIN order_items i ON i.order_id = o.id
    LEFT JOIN products p ON p.id = i.product_id
    ORDER BY o.id
""").fetchall()
orders = {}
for r in rows:
    order = orders.setdefault(r["order_id"], {"id": r["order_id"], "total": r["total"], "items": []})
    if r["product_id"] is not None:
        order["items"].append({"product_id": r["product_id"], "qty": r["qty"], "name": r["product_name"]})
result = list(orders.values())
```
SQLAlchemy: eager loading e agregação no banco.
```python
from sqlalchemy.orm import selectinload
posts = db.session.execute(
    db.select(Post).options(selectinload(Post.user), selectinload(Post.category))
).scalars().all()
counts = dict(db.session.execute(db.select(Post.status, db.func.count()).group_by(Post.status)).all())
```
JS: uma query com `JOIN` + agrupamento em memória com `Map`, ou `WHERE id IN (?, ?, ...)` com placeholders gerados (`ids.map(() => '?').join(',')`). Preserve a **ordem** e as chaves da resposta original (use `ORDER BY` explícito).

---

## PB-11 — Camada de validação de entrada (AP-14)

ANTES (Python)
```python
data = request.get_json()
if data["price"] < 0: ...
```
DEPOIS
```python
# validators/product_validator.py
from errors import ValidationError

def validate_product(data):
    if not isinstance(data, dict):
        raise ValidationError("Corpo JSON obrigatório")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("name é obrigatório")
    price = data.get("price")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
        raise ValidationError("price deve ser número >= 0")
    return {"name": name.strip(), "price": float(price)}

data = validate_product(request.get_json(silent=True))
```
ANTES (JS)
```js
const status = req.body.card.startsWith('4') ? 'PAID' : 'DENIED';
```
DEPOIS
```js
function validateCheckout(body) {
  const errors = [];
  if (!body || typeof body !== 'object') errors.push('body');
  if (typeof body?.card !== 'string' || !/^\d{12,19}$/.test(body.card)) errors.push('card');
  if (!Number.isInteger(Number(body?.plan_id))) errors.push('plan_id');
  if (errors.length) throw new ValidationError(`Campos inválidos: ${errors.join(', ')}`);
  return { ...body, plan_id: Number(body.plan_id) };
}
```
Use libs de validação **já presentes** nas dependências (marshmallow, pydantic, joi, zod) antes de criar validadores manuais. Não rejeite payloads que o baseline aceitava como válidos; reforce só casos que davam 500, crash ou dados absurdos (negativos, tipos errados) — retornando 400/404 em vez de 500.

---

## PB-12 — Callback → async/await com wrapper Promise do sqlite3 (AP-16)

ANTES
```js
db.get('SELECT * FROM plans WHERE id = ?', [planId], (err, plan) => {
  db.get('SELECT * FROM users WHERE email = ?', [email], (err, user) => {
    db.run('INSERT INTO subscriptions (user_id, plan_id) VALUES (?, ?)', [user.id, planId], function (err) {
      res.json({ subscription_id: this.lastID });
    });
  });
});
```
DEPOIS
```js
// src/db/connection.js
const sqlite3 = require('sqlite3');

function createDb(filename) {
  const raw = new sqlite3.Database(filename);
  const run = (sql, params = []) => new Promise((resolve, reject) => {
    raw.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); });
  });
  const get = (sql, params = []) => new Promise((resolve, reject) => raw.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));
  const all = (sql, params = []) => new Promise((resolve, reject) => raw.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));
  const exec = (sql) => new Promise((resolve, reject) => raw.exec(sql, (err) => (err ? reject(err) : resolve())));
  const close = () => new Promise((resolve, reject) => raw.close((err) => (err ? reject(err) : resolve())));
  return { run, get, all, exec, close };
}
module.exports = { createDb };

// uso no service
const plan = await db.get('SELECT * FROM plans WHERE id = ?', [planId]);
const user = await db.get('SELECT * FROM users WHERE email = ?', [email]);
const { lastID } = await db.run('INSERT INTO subscriptions (user_id, plan_id) VALUES (?, ?)', [user.id, planId]);
```
Com banco `:memory:`, **aguarde** schema + seed (`await initSchema(db)`) antes de `app.listen`, e use uma única conexão injetada (uma conexão nova seria um banco vazio).

---

## PB-13 — Substituir APIs deprecated (AP-17)

ANTES (Python)
```python
from datetime import datetime
created_at = db.Column(db.DateTime, default=datetime.utcnow)
post = Post.query.get(post_id)
done = Post.query.filter_by(status="done").count()
```
DEPOIS
```python
from datetime import datetime, timezone

def utcnow():
    # Mantém UTC "naive" para não quebrar comparações com colunas SQLite nem o formato serializado
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at = db.Column(db.DateTime, default=utcnow)
post = db.session.get(Post, post_id)
done = db.session.scalar(db.select(db.func.count()).select_from(Post).where(Post.status == "done"))
```
Atenção: trocar `utcnow()` por `datetime.now(timezone.utc)` puro gera datetime *aware*; comparar com valores *naive* lidos do SQLite lança `TypeError`, e `str()`/`isoformat()` passam a incluir `+00:00` (muda o shape da resposta). Use o helper acima ou converta de forma consistente.

ANTES (JS)
```js
var buf = new Buffer(data);
const parsed = url.parse(req.url);
app.use(bodyParser.json());
res.send(404, 'Not found');
```
DEPOIS
```js
const buf = Buffer.from(data);
const parsed = new URL(req.url, `http://${req.headers.host}`);
app.use(express.json());
res.status(404).send('Not found');
```
Tabela completa de equivalências: seção "APIs deprecated" do catálogo.

---

## PB-14 — Magic numbers → constantes / enums (AP-20)

ANTES
```python
if total > 10000: discount = total * 0.1
elif total > 5000: discount = total * 0.05
if status not in ["pending", "approved", "cancelled"]: ...
```
DEPOIS
```python
# models/constants.py
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"

DISCOUNT_TIERS = ((10000, 0.10), (5000, 0.05))   # (faturamento mínimo, percentual)

def discount_for(total):
    return next((total * rate for threshold, rate in DISCOUNT_TIERS if total > threshold), 0)

if status not in {s.value for s in OrderStatus}: ...
```
JS
```js
const PaymentStatus = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4';
```
Os **valores** continuam idênticos (são contrato com o banco e a API).

---

## PB-15 — Logging no lugar de print / console.log (AP-22)

ANTES
```python
print("Order created: " + str(order_id) + " for " + email)
```
DEPOIS
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Order created id=%s", order_id)   # sem PII
# no create_app: logging.basicConfig(level=app.config["LOG_LEVEL"])
```
JS (sem dependência nova)
```js
// src/utils/logger.js
const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };
const min = LEVELS[process.env.LOG_LEVEL] || LEVELS.info;
const log = (level) => (msg, meta = {}) => {
  if (LEVELS[level] >= min) process.stdout.write(JSON.stringify({ level, msg, ...meta, ts: new Date().toISOString() }) + '\n');
};
module.exports = { debug: log('debug'), info: log('info'), warn: log('warn'), error: log('error') };
```
Notificações simuladas por `print` (e-mail/SMS) viram um serviço injetado (`Notifier.notify(...)`) que loga via logger.

---

## PB-16 — App factory / composition root (AP-07, AP-11)

ANTES (Python)
```python
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route("/items")
def items(): ...

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
```
DEPOIS
```python
# app.py — entry point fino
from flask import Flask
from config.settings import Config
from extensions import db
from middlewares.error_handler import register_error_handlers
from views.item_routes import item_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    register_error_handlers(app)
    app.register_blueprint(item_bp)
    with app.app_context():
        db.create_all()
    return app

app = create_app()   # mantém `flask --app app run` e `from app import app` (seed) funcionando

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
```
JS
```js
// src/app.factory.js
const express = require('express');
function createApp({ db, config, logger }) {
  const app = express();
  app.use(express.json());
  const controllers = buildControllers({ db, config, logger });   // DI explícita
  app.use(require('./routes/checkout.routes')(controllers.checkout));
  app.use(require('./middlewares/errorHandler')(logger));          // por último
  return app;
}
module.exports = { createApp };

// src/app.js — entry point referenciado por "npm start"
const { config } = require('./config');
const { createDb } = require('./db/connection');
const { initSchema } = require('./db/schema');
const { createApp } = require('./app.factory');
const logger = require('./utils/logger');

(async () => {
  const db = createDb(config.dbPath);
  await initSchema(db);
  createApp({ db, config, logger }).listen(config.port, () => logger.info(`Servidor na porta ${config.port}`));
})().catch((err) => { logger.error('Falha no boot', { message: err.message }); process.exit(1); });
```

---

## PB-17 — Conexão por requisição / injeção de dependência (AP-09)

ANTES (Python)
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("app.db", check_same_thread=False)
    return db_connection
```
DEPOIS
```python
# db/connection.py
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())   # CREATE TABLE IF NOT EXISTS + seed idempotente
```
Mantenha `row_factory` e o mesmo tipo de retorno que o código original esperava (`sqlite3.Row` vs tupla). JS: crie a conexão no composition root e passe-a para as factories (`createUserModel(db)`); caches viram objetos injetados com limite/TTL, não variáveis de módulo exportadas.

---

## PB-18 — DRY, código morto e nomes (AP-15, AP-21, AP-23)

ANTES
```python
import os, sys, json
def get_product(id):
    row = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    return {"id": row[0], "name": row[1], "price": row[2]}
def list_products():
    return [{"id": r[0], "name": r[1], "price": r[2]} for r in conn.execute("SELECT * FROM products")]
```
DEPOIS
```python
def row_to_product(row):
    return {"id": row["id"], "name": row["name"], "price": row["price"]}

def get_product(product_id):
    row = conn.execute("SELECT id, name, price FROM products WHERE id = ?", (product_id,)).fetchone()
    return row_to_product(row) if row else None

def list_products():
    return [row_to_product(r) for r in conn.execute("SELECT id, name, price FROM products")]
```
Remova imports/funções/módulos sem uso (confirme com grep que nada os importa). Renomeie variáveis internas crípticas (`u`, `cc`, `cur2`), **não** os campos do contrato HTTP (campos abreviados do JSON continuam como estão).

---

## PB-19 — Configurar CORS e middlewares (AP-18)

ANTES
```python
CORS(app)
```
DEPOIS
```python
CORS(app, origins=app.config["CORS_ORIGINS"])   # lista vinda do env, ex.: "http://localhost:3000"
```
JS: `app.use(cors({ origin: config.corsOrigins }))`. Ordem no Express: parsers → CORS/log → rotas → 404 → error handler.

---

## PB-20 — Integridade referencial (AP-19)

ANTES
```python
for post in user.posts:
    db.session.delete(post)
db.session.delete(user)
```
DEPOIS
```python
class User(db.Model):
    posts = db.relationship("Post", backref="user", cascade="all, delete-orphan")

db.session.delete(user); db.session.commit()
```
SQL cru: `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` + `PRAGMA foreign_keys = ON` em cada conexão SQLite. Mudanças de schema em banco já existente exigem recriar/migrar — se o banco é gerado pelo seed, rode o seed de novo; senão, registre como Remaining Known Issue em vez de quebrar dados.

---

## PB-21 — Token de login assinado e com expiração + `require_auth` (AP-24)

Mantenha o **nome** do campo (ex.: `"token"`) e o **tipo** (string) da resposta de login; muda só o **valor**. O token passa a ser assinado com HMAC sobre o `SECRET_KEY` (PB-01) e expira. O header de admin do PB-07 (`X-Admin-Token`) continua valendo para rotas admin.

ANTES (Python)
```python
return jsonify({"token": f"token-{user['id']}", "id": user["id"]})
```
DEPOIS (`itsdangerous` já vem com o Flask — nenhuma dependência nova)
```python
# middlewares/auth.py
import hmac
from functools import wraps
from flask import current_app, g, request
from itsdangerous import BadData, URLSafeTimedSerializer
from errors import UnauthorizedError

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="auth-token")

def issue_token(user_id):
    return _serializer().dumps({"sub": user_id})

def verify_token(token):
    try:   # BadData cobre BadSignature, SignatureExpired e BadPayload
        data = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except BadData:
        return None
    return data.get("sub")

def is_admin_request():
    given = request.headers.get("X-Admin-Token", "").encode()
    expected = current_app.config["ADMIN_TOKEN"].encode()
    return bool(given and expected) and hmac.compare_digest(given, expected)

def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        g.is_admin = is_admin_request()
        g.user_id = None if g.is_admin else verify_token(header.removeprefix("Bearer ").strip())
        if not g.is_admin and g.user_id is None:
            raise UnauthorizedError("Não autorizado")
        return view(*args, **kwargs)
    return wrapper

# login (controller/view): mesmo shape, valor assinado
return jsonify({"token": issue_token(user["id"]), "id": user["id"]})
```
`config/settings.py`: `TOKEN_MAX_AGE = int(os.environ.get("TOKEN_MAX_AGE", "3600"))`.

ANTES (JS)
```js
res.json({ token: 'fake-jwt-' + user.id });
```
DEPOIS (`node:crypto`, sem dependência nova)
```js
// src/utils/token.js
const crypto = require('node:crypto');
const sign = (data, secret) => crypto.createHmac('sha256', secret).update(data).digest('base64url');

function issueToken(sub, { secret, ttlSeconds = 3600 }) {
  const exp = Math.floor(Date.now() / 1000) + ttlSeconds;
  const payload = Buffer.from(JSON.stringify({ sub, exp })).toString('base64url');
  return `${payload}.${sign(payload, secret)}`;
}

function verifyToken(token, { secret }) {
  const [payload, sig] = String(token || '').split('.');
  if (!payload || !sig) return null;
  const expected = Buffer.from(sign(payload, secret));
  const given = Buffer.from(sig);
  if (expected.length !== given.length || !crypto.timingSafeEqual(expected, given)) return null;
  try {
    const { sub, exp } = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    return typeof exp === 'number' && exp > Date.now() / 1000 ? sub : null;
  } catch { return null; }
}
module.exports = { issueToken, verifyToken };

// src/middlewares/requireAuth.js
const crypto = require('node:crypto');
const { verifyToken } = require('../utils/token');
const { UnauthorizedError } = require('../errors/AppError');
module.exports = (config) => (req, res, next) => {
  const admin = Buffer.from(req.get('X-Admin-Token') || '');
  const expected = Buffer.from(config.adminToken);
  req.isAdmin = expected.length > 0 && admin.length === expected.length && crypto.timingSafeEqual(admin, expected);
  const bearer = (req.get('Authorization') || '').replace(/^Bearer\s+/i, '');
  req.userId = req.isAdmin ? null : verifyToken(bearer, { secret: config.secretKey });
  if (!req.isAdmin && req.userId == null) return next(new UnauthorizedError('Unauthorized'));
  next();
};

// login: mesmo campo/tipo
res.json({ token: issueToken(user.id, { secret: config.secretKey, ttlSeconds: config.tokenTtl }) });
```
Regras:
- Erro de auth sai pelo error handler central, no formato de erro do projeto (PB-08).
- `.env.example`: `SECRET_KEY`, `TOKEN_MAX_AGE`/`TOKEN_TTL`, `ADMIN_TOKEN`. Em produção, recuse `SECRET_KEY` vazio ou default (PB-01).
- Documente no bloco da Fase 3: "faça `POST <rota de login>` com as credenciais do seed e envie `Authorization: Bearer <token>`; rotas admin aceitam `X-Admin-Token`".
- Se havia um JWT de verdade mas sem verificação, mantenha o formato (lib existente) e só adicione o verify no guard.

---

## PB-22 — Proteger listagens/detalhes com PII (AP-25)

Mudança **aditiva e na direção segura**: path, método, parâmetros e shape da resposta 200 continuam iguais; sem credencial passa a responder 401. Requer o guard do PB-21.

ANTES (Python)
```python
@bp.route("/accounts", methods=["GET"])
def list_accounts(): ...

@bp.route("/accounts/<int:account_id>", methods=["GET"])
def get_account(account_id): ...
```
DEPOIS
```python
from flask import g
from errors import ForbiddenError
from middlewares.auth import require_auth

@bp.route("/accounts", methods=["GET"])
@require_auth                       # token assinado válido ou X-Admin-Token
def list_accounts(): ...

@bp.route("/accounts/<int:account_id>", methods=["GET"])
@require_auth
def get_account(account_id):
    if not g.is_admin and g.user_id != account_id:   # dono ou admin
        raise ForbiddenError("Acesso negado")
    ...
```
JS
```js
router.get('/api/accounts', requireAuth, asyncHandler(controller.list));
router.get('/api/accounts/:id', requireAuth, asyncHandler(async (req, res) => {
  if (!req.isAdmin && String(req.userId) !== String(req.params.id)) throw new ForbiddenError('Forbidden');
  res.json(await controller.getById(req.params.id));
}));
```
Regras:
- Listagem completa: qualquer usuário autenticado ou admin (não restrinja mais do que isso sem solicitação explícita; registre em Remaining Known Issues se o ideal for só admin).
- Rotas de cadastro e login continuam públicas.
- Na validação, obtenha o token chamando o login primeiro (ou use `X-Admin-Token`) e compare com o baseline; confirme também 401 sem credencial e 403 para id de outro usuário.

---

## PB-23 — Catch-all 404/405 → error handler central (AP-12)

ANTES (Express): sem middleware final → `GET /x` devolve HTML `Cannot GET /x`.
DEPOIS
```js
// src/app.factory.js — ordem: parsers → rotas → 404 → error handler
app.use(routes);
app.use((req, res, next) => next(new NotFoundError(`Rota não encontrada: ${req.method} ${req.path}`)));
app.use(errorHandler(logger));
```
O error handler responde no **formato já usado** pela API: se ela responde erros em texto puro, `res.status(err.statusCode).type('text/plain').send(err.message)`; se JSON, `res.status(err.statusCode).json({ <chave do projeto>: err.message })`.

ANTES (Flask): sem handler → página HTML `404 Not Found` do Werkzeug.
DEPOIS (registrado no **app**, não em Blueprint — `bp.errorhandler(404)` não vê URLs sem rota)
```python
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(HTTPException)       # cobre 404, 405, 400 do parser JSON...
    def handle_http(err):
        return jsonify({ERROR_KEY: err.description}), err.code
```
Validação: `curl -s -i http://127.0.0.1:<p>/__rota-inexistente__` → 404 com o `Content-Type` da API (JSON/texto), nunca `text/html`. Registre na tabela de endpoints como mudança na direção segura (formato padronizado).

---

## PB-24 — Corrigir mensagens de resposta enganosas (AP-26)

Permitido **somente** quando a mensagem descreve um comportamento falso depois do refactor (ou já falso antes). Mantenha status code, tipo da resposta, chaves e shape; troque só o texto.

ANTES
```python
return jsonify({"mensagem": "Registro removido; itens relacionados mantidos"}), 200   # cascade já remove
```
DEPOIS
```python
return jsonify({"mensagem": "Registro removido"}), 200
```
```js
// ANTES: res.status(200).send('Notificação enviada (TODO: implementar envio)');
res.status(200).send('Notificação registrada');
```
Regras: registre cada troca `antigo → novo` em Changes Applied e na coluna Obs da tabela de endpoints (Shape `≈`). Se a mensagem descreve algo que o código deveria fazer e não faz, prefira manter a mensagem e registrar em Remaining Known Issues — não invente feature.

---

## PB-25 — Senhas de seed/fixture vindas do ambiente (AP-01)

ANTES
```python
admin = Account(email="admin@example.com", password=generate_password_hash("admin123"))
```
DEPOIS (Python)
```python
# seed.py
import os
import secrets

def seed_password(env_var):
    value = os.environ.get(env_var)
    if value:
        return value
    if os.environ.get("APP_ENV") == "production":
        raise SystemExit(f"{env_var} é obrigatório em produção")
    value = secrets.token_urlsafe(12)
    print(f"[seed] {env_var} não definido; senha gerada para esta execução: {value}")
    return value

admin = Account(email="admin@example.com", password=generate_password_hash(seed_password("SEED_ADMIN_PASSWORD")))
```
DEPOIS (JS — seed costuma rodar no boot, então use o logger)
```js
const crypto = require('node:crypto');
function seedPassword(envVar, logger) {
  if (process.env[envVar]) return process.env[envVar];
  if (process.env.APP_ENV === 'production') throw new Error(`${envVar} é obrigatório em produção`);
  const value = crypto.randomBytes(12).toString('base64url');
  logger.warn(`[seed] ${envVar} não definido; senha gerada para esta execução: ${value}`);
  return value;
}
```
Regras:
- **Nunca** use fallback literal (`os.environ.get("SEED_ADMIN_PASSWORD", "admin123")`, `|| 'admin123'`): continua sendo AP-01 e o re-grep da Fase 3 deve pegá-lo.
- `python-dotenv`/`dotenv` leem `.env`, **não** `.env.example`. Por isso, sem a variável definida, o seed em dev precisa funcionar sozinho (senha aleatória impressa uma vez), sem quebrar o comando original.
- Uma variável por conta inicial (`SEED_ADMIN_PASSWORD`, `SEED_USER_PASSWORD`, ...), listadas no `.env.example` com os valores de dev do baseline e o comentário "apenas desenvolvimento".
- Reprodutibilidade: na validação da Fase 3, o validador exporta essas variáveis com os valores de dev do baseline antes de rodar seed/boot, para que os logins do baseline continuem válidos.
- Em produção (`APP_ENV=production`) o seed recusa rodar sem as variáveis explícitas.

---

## Regras de preservação de comportamento

1. **Rotas:** todo path + método HTTP do baseline continua existindo, com os mesmos parâmetros (path, query, corpo) e o mesmo prefixo de blueprint/router.
2. **Respostas válidas:** para requisições válidas, mesmo status code e mesmo *shape* JSON (chaves, tipos, aninhamento, ordem de listas quando determinística, formato de datas). Mensagens de sucesso textuais também — **exceto** mensagens que descrevem comportamento falso após o refactor (PB-24): troque só o texto, mantenha status/tipo/shape e registre `antigo → novo`.
3. **Mudanças só na direção segura:** permitido (e documentado na coluna Obs da tabela de endpoints):
   - remover campos sensíveis da resposta (senha, hash, segredos, config interna);
   - exigir auth em rotas admin/destrutivas — **desde que** o token/chave de dev esteja documentado (`.env.example` + bloco da Fase 3) e o validador consiga chamar o endpoint com sucesso enviando a credencial;
   - transformar 500/crash por entrada inválida em 400/404/422;
   - restringir endpoint perigoso (SQL arbitrário → somente SELECT para admin);
   - exigir auth em endpoints que listam/detalham PII (PB-22) — mudança aditiva: com credencial válida, mesmo status e shape; documente como obter o token (login primeiro ou `X-Admin-Token`);
   - trocar o **valor** do token de login por um token assinado (PB-21), mantendo nome do campo e tipo (string); documente o header (`Authorization: Bearer <token>`);
   - responder rotas inexistentes/métodos não suportados pelo error handler central (PB-23) em vez de HTML padrão.
4. **Seed e dados iniciais:** o script/rotina de seed continua funcionando com o mesmo comando e produz os mesmos registros (senhas com hash; valores em texto vindos do env — PB-25 — e definidos pelo validador com os valores de dev do baseline para que os logins continuem válidos).
5. **Start:** o comando original (`python app.py`, `npm start`, `flask --app app run`) continua subindo o app; porta default inalterada (configurável por env).
6. **Formato de erro:** mantenha a chave/formato de erro original quando clientes dependem dele; padronize apenas o que antes saía em HTML/stack trace.
7. **Sem renomear contrato:** nomes de campos JSON de entrada/saída e de query params não mudam, mesmo que sejam ruins (registre em Remaining Known Issues).
8. **Sem features novas:** não adicione endpoints, paginação obrigatória ou campos novos além do necessário para segurança.
