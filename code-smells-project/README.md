# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
export $(grep -v '^#' .env.example | xargs)   # defaults de desenvolvimento (opcional)
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado no primeiro boot,
já com produtos e usuários de exemplo. `flask --app app run` também funciona (a factory
`create_app()` é descoberta automaticamente).

## Configuração

Todas as variáveis estão documentadas em `.env.example`. O projeto lê o ambiente direto
(`os.environ`) — **não** existe carregamento de arquivo `.env`; exporte as variáveis no shell.

Com `APP_ENV=development` (default) os valores de desenvolvimento bastam. Com qualquer outro
valor, o boot falha se `SECRET_KEY` ou `ADMIN_TOKEN` não forem definidos com valores próprios.

## Autenticação

A API tem dois tipos de credencial:

| Credencial | Header | Como obter | Dá acesso a |
|---|---|---|---|
| Token de usuário | `Authorization: Bearer <token>` | `POST /login` devolve o campo `token` (assinado com `SECRET_KEY`, expira em `TOKEN_MAX_AGE` segundos) | Os próprios dados: `POST /pedidos`, `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` |
| Token de administrador | `X-Admin-Token: <ADMIN_TOKEN>` | Variável de ambiente `ADMIN_TOKEN` (default de dev: `dev-admin-token`) | Tudo acima, sem restrição de dono, mais as rotas administrativas |

Rotas que exigem `X-Admin-Token`: `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`,
`POST|PUT|DELETE /produtos`, `GET /relatorios/vendas`, `POST /admin/query`, `POST /admin/reset-db`.

Rotas públicas: `GET /`, `GET /health`, `GET /produtos*`, `POST /usuarios`, `POST /login`.

Exemplo:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
curl -s http://127.0.0.1:5000/usuarios/1 -H "Authorization: Bearer $TOKEN"
curl -s http://127.0.0.1:5000/usuarios   -H 'X-Admin-Token: dev-admin-token'
```

## Seed

As contas iniciais são criadas no primeiro boot com as senhas de `SEED_ADMIN_PASSWORD`,
`SEED_JOAO_PASSWORD` e `SEED_MARIA_PASSWORD`. Sem essas variáveis, o seed gera senhas
aleatórias e as registra uma única vez no log do servidor. Para recriar o estado inicial:
apague `loja.db` e suba a aplicação de novo.
