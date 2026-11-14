# Guidelines da Arquitetura MVC Alvo (Fase 3)

Objetivo: cada arquivo tem **uma** responsabilidade, as dependências apontam numa única direção e o app é montado em um único ponto (composition root). Em uma API, a "View" é a camada de rotas + serialização da resposta (não há HTML).

---

## 1. Camadas e responsabilidades

| Camada | Faz | Não faz |
|---|---|---|
| **Config** (`config/`) | Lê variáveis de ambiente com defaults seguros para dev; expõe objeto/classe de config (por ambiente: dev/test/prod); define porta, host, debug, URL do banco, segredos, origens de CORS | Ler `request`; ter regra de negócio; conter segredos reais como default |
| **Models** (`models/`) | Entidades e acesso a dados: schema/ORM, repositórios com queries **parametrizadas**, mapeamento linha→dict/entidade, transações de baixo nível | Conhecer HTTP (`request`, `res`, status codes, `jsonify`); decidir regra de negócio; ler env direto |
| **Services** (`services/`, opcional) | Regras de negócio complexas e reutilizáveis (checkout, cálculo de desconto, relatório, cascatas, notificações via interface injetada); orquestram vários models numa transação | Conhecer HTTP; montar SQL cru (delegar ao model/repositório) |
| **Controllers** (`controllers/`) | Um método por caso de uso: recebe dados já extraídos do request, valida (via validators/schemas), chama services/models, devolve dados + status ou lança exceção de domínio | SQL; `print`; montar conexões; acessar globais do framework quando evitável (receber dados como argumentos) |
| **Views / Routes** (`views/` ou `routes/`) | Declarar URL + método HTTP, extrair parâmetros do request, chamar o controller, serializar a resposta (JSON) com o status code certo, aplicar middlewares de rota (auth) | Regra de negócio; SQL; try/except genérico (o error handler central cuida) |
| **Middlewares** (`middlewares/`) | Error handler centralizado (exceção → JSON padronizado + log), autenticação/autorização, CORS configurado, logging de requisição | Regra de negócio |
| **Composition root** (entry point / app factory) | `create_app(config)` / `createApp(deps)`: cria app, registra extensões, banco, middlewares, rotas, error handler; o entry point só chama a factory e sobe o servidor | Ter rotas ou lógica inline; efeitos colaterais no import (seed, `create_all`) fora da factory |

Opcional: `validators/` ou `schemas/` (validação de entrada e serialização de saída), `utils/` só para funções puras genéricas (formatação, datas) — nunca regra de negócio escondida.

---

## 2. Regras de dependência

```
entry point → app factory → routes/views → controllers → services → models → db/connection
                    ↘ config, middlewares (usados pela factory e pelas rotas)
```

1. Uma camada só importa camadas **à direita** dela. Models nunca importam controllers/routes; controllers nunca importam routes.
2. `config` pode ser importado por qualquer camada de infraestrutura (db, factory), mas prefira **injetar** valores (parâmetros/construtor) em services e models.
3. Dependências externas (conexão de banco, gateway de pagamento, cliente SMTP, cache) são criadas no composition root e passadas adiante (DI por construtor/factory ou por contexto de requisição como `flask.g`). Nada de `new Client()` dentro de regra de negócio.
4. Nenhum estado mutável de módulo compartilhado entre requisições (caches globais, contadores, conexão única com `check_same_thread=False`).
5. Exceções de domínio (`NotFoundError`, `ValidationError`, `ConflictError`, `UnauthorizedError`) são definidas num módulo neutro (ex.: `errors.py` / `errors/AppError.js`) e mapeadas para HTTP **só** no error handler.

---

## 3. Convenções de nomes

- Um arquivo por entidade/agregado por camada: `models/<entidade>_model.py` | `models/<entidade>.model.js`, `controllers/<entidade>_controller.py` | `controllers/<entidade>.controller.js`, `views/<entidade>_routes.py` | `routes/<entidade>.routes.js`, `services/<caso>_service.py` | `services/<caso>.service.js`.
- Use os nomes de entidade **na língua do código original** (não traduza o domínio).
- Python: `snake_case` para módulos/funções, `PascalCase` para classes, constantes `UPPER_SNAKE`. JS: `camelCase` para funções/variáveis, `PascalCase` para classes, constantes `UPPER_SNAKE`.
- Funções de controller com verbo + entidade: `list_products`, `create_order`, `getFinancialReport`.
- Python: **nunca** crie um pacote `app/` ao lado de um `app.py` existente (conflito de import). Use pacotes na raiz (`config/`, `models/`...) ou um pacote `src/`.

---

## 4. Árvores recomendadas

### 4.1 Python / Flask

```
<projeto>/
├── app.py                      # entry point: app = create_app(); if __name__ == "__main__": app.run(host, port, debug da config)
├── config/
│   ├── __init__.py
│   └── settings.py             # class Config / DevConfig / TestConfig lendo os.environ
├── db/  (ou extensions.py)     # conexão por requisição (flask.g + teardown) OU instância db = SQLAlchemy(); init_db(); seed
├── models/
│   ├── __init__.py
│   └── <entidade>_model.py     # queries parametrizadas / classes ORM + to_dict sem campos sensíveis
├── services/                   # opcional: regras complexas
│   └── <caso>_service.py
├── controllers/
│   └── <entidade>_controller.py
├── views/  (ou routes/)
│   └── <entidade>_routes.py    # Blueprints: URL + método + jsonify
├── middlewares/
│   ├── error_handler.py        # register_error_handlers(app)
│   └── auth.py                 # decorator require_admin / login_required
├── errors.py                   # exceções de domínio
├── <script de seed>           # se o projeto original tinha seed (mesmo comando)
├── requirements.txt
└── .env.example
```

`app.py` precisa continuar funcionando com `python app.py` **e** expor `app` em nível de módulo para `flask --app app run`.

### 4.2 Node.js / Express

```
<projeto>/
├── package.json                # "start" continua funcionando (mesmo comando)
├── .env.example
└── src/
    ├── app.js | server.js      # entry point referenciado por "start"/"main": carrega config, chama createApp, listen
    ├── app.factory.js          # createApp({ db, config }) → express app (middlewares, rotas, error handler)
    ├── config/
    │   └── index.js            # process.env com defaults de dev; congelado (Object.freeze)
    ├── db/
    │   ├── connection.js       # abre o banco + wrapper Promise (run/get/all)
    │   └── schema.js           # CREATE TABLE + seed
    ├── models/
    │   └── <entidade>.model.js # repositórios async com placeholders
    ├── services/
    │   └── <caso>.service.js
    ├── controllers/
    │   └── <entidade>.controller.js
    ├── routes/
    │   └── <entidade>.routes.js   # express.Router()
    ├── middlewares/
    │   ├── errorHandler.js     # (err, req, res, next)
    │   └── auth.js
    └── errors/
        └── AppError.js
```

Se o entry atual (`"start": "node src/app.js"`) for mantido como nome, ele vira o entry point fino — não precisa mudar o `package.json`. Se mudar, atualize `start` e `main` juntos e verifique `npm start`.

### 4.3 Genérica (qualquer stack)

```
<raiz>/
├── <entry point>               # só monta e sobe
├── config/
├── models/  (+ repositories/)
├── services/                   # opcional
├── controllers/
├── views/ | routes/ | handlers/
├── middlewares/
├── errors/
└── .env.example
```

Go: `cmd/<app>/main.go`, `internal/{config,models,services,controllers,routes,middleware}`. Spring: `config/`, `model|entity/`, `repository/`, `service/`, `controller/`, `exception/` com `@ControllerAdvice`.

---

## 5. Adaptação ao nível de arquitetura atual

### 5.1 Monolito → split completo

1. Criar `config/` e mover todos os literais de config/segredos (PB-01).
2. Extrair conexão/schema/seed para `db/` (PB-17), com transações onde houver escrita multi-etapa (PB-09).
3. Extrair models/repositórios por entidade, já com queries parametrizadas (PB-02) e serialização sem campos sensíveis (PB-06).
4. Extrair services para regras de negócio pesadas (PB-04).
5. Criar controllers finos e views/routes por entidade, **preservando URLs, métodos e shapes** (regras no playbook).
6. Criar error handler central (PB-08), auth nas rotas admin/destrutivas (PB-07), factory/composition root (PB-16).
7. Apagar o(s) arquivo(s) monolítico(s) original(is) quando tudo foi migrado (ou reduzi-los ao entry point fino). Nada de módulo antigo importável com código duplicado.

### 5.2 Camadas parciais → incremental

1. **Preserve** as camadas que já funcionam (ex.: modelos ORM existentes, blueprints com as URLs certas). Não reescreva por estética.
2. Insira `controllers/` (e `services/` quando a regra for pesada) entre routes e models: mova a regra de negócio dos handlers para lá; routes ficam só com parse → controller → resposta.
3. Aproveite código existente não usado (helpers de validação, constantes, métodos de domínio/serialização já escritos) como fonte única; apague o que continuar sem uso.
4. Adicione `config/` + app factory (`create_app`) e remova efeitos colaterais de import (ex.: `create_all()` em nível de módulo → dentro da factory).
5. Adicione error handler central e substitua `except:` genéricos por exceções de domínio.
6. Mova código para o lugar certo (ex.: CRUD de uma entidade dentro do blueprint de outra → blueprint próprio **com o mesmo prefixo de URL**).
7. Corrija APIs deprecated (PB-13) dentro dos arquivos tocados e no restante.

### 5.3 Já em camadas

Somente os findings pontuais; não mova arquivos sem motivo.

### 5.4 Invariantes em qualquer nível

- **Nunca** renomeie URLs públicas, métodos HTTP, nomes de campos do JSON de entrada/saída nem query params.
- O comando de start original continua funcionando (ex.: `python app.py`, `npm start`), assim como o seed.
- Um único entry point claro; nenhum arquivo antigo com rotas duplicadas registrado em paralelo.
