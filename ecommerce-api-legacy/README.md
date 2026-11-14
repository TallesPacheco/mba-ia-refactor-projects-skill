# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Exemplos de requisições estão em `api.http`.

## Configuração

Variáveis de ambiente (veja `.env.example`): `PORT` (default 3000), `HOST` (default 127.0.0.1), `DB_PATH` (default `:memory:`), `ADMIN_TOKEN`, `SEED_USER_PASSWORD`, `PAYMENT_GATEWAY_KEY`, `LOG_LEVEL`, `APP_ENV`.

Nenhum segredo tem default no código. `ADMIN_TOKEN` e `SEED_USER_PASSWORD`, quando não definidos fora de produção, são **gerados aleatoriamente a cada boot** e registrados no log (nível `warn`); com `APP_ENV=production`, a ausência de `ADMIN_TOKEN`/`PAYMENT_GATEWAY_KEY` falha no boot e a do `SEED_USER_PASSWORD` impede o seed.

### Autenticação

As rotas `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem o header `X-Admin-Token` com o valor de `ADMIN_TOKEN`. Sem o header, ou com valor errado, a resposta é 401.

```bash
ADMIN_TOKEN=um-token-seu npm start
curl -H 'X-Admin-Token: um-token-seu' http://localhost:3000/api/admin/financial-report
```

Sem `ADMIN_TOKEN` no ambiente, pegue o token sorteado na linha de log `ADMIN_TOKEN não definido; token gerado para esta execução`.

## Contrato do checkout

`POST /api/checkout` usa nomes de campo abreviados por compatibilidade com clientes existentes:

| Campo | Significado | Tipo |
|---|---|---|
| `usr` | nome do aluno (não é username) | string não vazia |
| `eml` | e-mail do aluno | string não vazia |
| `pwd` | senha (opcional; ausente = senha aleatória) | string |
| `c_id` | id do curso | número ou string numérica |
| `card` | número do cartão (prefixo `4` aprova no gateway simulado) | string não vazia |

Respostas de erro da API são texto puro (`Bad Request`, `Curso não encontrado`, `Pagamento recusado`, `Não autorizado`); rotas inexistentes respondem 404 e métodos não suportados 405, no mesmo formato.

## Estrutura

`src/app.js` (entry point) → `src/app.factory.js` (composition root) → `routes/` → `controllers/` → `services/` → `models/` → `db/`, com `config/`, `middlewares/`, `errors/`, `validators/` e `utils/`.
