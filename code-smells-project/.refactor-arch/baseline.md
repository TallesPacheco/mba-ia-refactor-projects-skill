# Baseline — code-smells-project (execução 2 — código já refatorado)

Boot: `PORT=5201 .venv/bin/python app.py` (comando de start original `python app.py`; host/porta/debug vêm da config via env — `config/settings.py:12-14`) | Seed: automático no boot (`app.py:27` → `db/connection.py:38-41` → `db/schema.py:68-87`), cria `loja.db` no CWD com 10 produtos e 3 usuários (senhas já em hash scrypt).
Versões: Python 3.14.3 / Flask 3.1.1 (Werkzeug 3.1.9, click 8.5.1, Jinja2 3.1.6, itsdangerous 2.2.0) / flask-cors 5.0.1 / sqlite3 (stdlib).
Recriar estado inicial: `rm -f loja.db` (gitignored; criado por este baseline e apagado ao final) e subir o app — o boot recria schema + seed.
Credencial de admin usada: header `X-Admin-Token: dev-admin-token` (default de dev em `config/settings.py:16`). 9 rotas exigem esse header (`grep -rn "@require_admin" views/` → 9 ocorrências).

Rotas registradas (`.venv/bin/flask --app app routes`): 19 rotas da aplicação + `static`.

Requisições executadas na ordem abaixo, banco recém-criado (IDs refletem essa ordem). Itens 8, 9 e 9b foram executados numa 2ª subida (porta 5202, banco reseedado) porque exigiam URL-encoding.

| # | Método | Path | Payload / header | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | / | - | 200 | {mensagem, versao:"1.0.0", endpoints{produtos,usuarios,pedidos,login,relatorios,health}} |
| 2 | GET | /health | - | 200 | {status:"ok", database:"connected", counts{produtos:10,usuarios:3,pedidos:0}, versao, ambiente:"development"} — sem secret_key/db_path/debug |
| 3 | GET | /produtos | - | 200 | {dados:[{id,nome,descricao,preco,estoque,categoria,ativo,criado_em}] (10), sucesso} |
| 4 | GET | /produtos/1 | - | 200 | {dados:{produto}, sucesso} |
| 5 | GET | /produtos/999 | - | 404 | {erro:"Produto não encontrado", sucesso:false} |
| 6 | GET | /produtos/busca?q=gamer | - | 200 | {dados:[produto] (3), total:3, sucesso} |
| 7 | GET | /produtos/busca?categoria=moveis&preco_min=100&preco_max=2000 | - | 200 | {dados:[produto] (1), total:1, sucesso} |
| 8 | GET | /produtos/busca | q=`' OR 1=1--` (urlencoded) | 200 | {dados:[], total:0, sucesso} — injeção não funciona, nenhum erro SQL vazado |
| 9 | GET | /produtos/busca | q=`x') OR 1=1 --` (urlencoded) | 200 | {dados:[], total:0, sucesso} — injeção não funciona |
| 9b | GET | /produtos/busca?preco_min=0&preco_max=100 | - | 200 | {dados:[produto] (preço ≤ 100), total, sucesso} — `preco_min=0` é descartado (0 é falsy, `models/produto_model.py:44`); sem efeito prático neste dataset |
| 10 | GET | /produtos/busca?preco_min=abc | - | 400 | {erro:"preco_min inválido"} |
| 11 | GET | /usuarios | sem token | 401 | {erro:"Não autorizado"} |
| 12 | GET | /usuarios | `X-Admin-Token` | 200 | {dados:[{id,nome,email,tipo,criado_em}] (3), sucesso} — sem campo `senha` |
| 13 | GET | /usuarios/1 | sem token | 200 | {dados:{id,nome,email,tipo,criado_em}, sucesso} — **rota pública com PII** |
| 14 | GET | /usuarios/999 | - | 404 | {erro:"Usuário não encontrado"} (sem `sucesso`) |
| 15 | GET | /pedidos | sem token | 401 | {erro:"Não autorizado"} |
| 16 | GET | /pedidos | `X-Admin-Token` | 200 | {dados:[], sucesso} |
| 17 | GET | /pedidos/usuario/2 | sem token | 200 | {dados:[], sucesso} — **rota pública** |
| 18 | GET | /relatorios/vendas | sem token | 401 | {erro:"Não autorizado"} |
| 19 | GET | /relatorios/vendas | `X-Admin-Token` | 200 | {dados:{total_pedidos,faturamento_bruto,desconto_aplicavel,faturamento_liquido,pedidos_pendentes,pedidos_aprovados,pedidos_cancelados,ticket_medio}, sucesso} (tudo 0) |
| 20 | POST | /login | {"email":"admin@loja.com","senha":"admin123"} | 200 | {dados:{id,nome,email,tipo}, sucesso, mensagem:"Login OK"} — **nenhum token/sessão devolvido** |
| 21 | POST | /login | senha errada | 401 | {erro:"Email ou senha inválidos", sucesso:false} |
| 22 | POST | /login | {"email":"admin@loja.com' --","senha":"x"} | 401 | {erro:"Email ou senha inválidos", sucesso:false} — bypass por SQLi não funciona |
| 23 | POST | /login | {} | 400 | {erro:"Email e senha são obrigatórios"} |
| 24 | POST | /login | (sem body / sem Content-Type) | 400 | {erro:"Email e senha são obrigatórios"} |
| 25 | POST | /produtos | válido, sem token | 401 | {erro:"Não autorizado"} |
| 26 | POST | /produtos | válido, `X-Admin-Token` | 201 | {dados:{id:11}, sucesso, mensagem:"Produto criado"} |
| 27 | POST | /produtos | {"nome":"X"} | 400 | {erro:"Preço é obrigatório"} |
| 28 | POST | /produtos | categoria "xyz" | 400 | {erro:"Categoria inválida. Válidas: [...]"} |
| 29 | POST | /produtos | preco -1 | 400 | {erro:"Preço não pode ser negativo"} |
| 30 | POST | /produtos | nome "O'Reilly" | 201 | {dados:{id:12}, sucesso} — apóstrofo não quebra o SQL |
| 31 | POST | /usuarios | {"nome":"Teste","email":"teste@email.com","senha":"abc123"} | 201 | {dados:{id:4}, sucesso} |
| 32 | POST | /usuarios | mesmo e-mail repetido | 409 | {erro:"Email já cadastrado"} |
| 33 | POST | /usuarios | {"nome":"Teste"} | 400 | {erro:"Nome, email e senha são obrigatórios"} |
| 34 | POST | /pedidos | usuario_id 2, 2 itens — **sem autenticação** | 201 | {dados:{pedido_id:1,total:6179.79}, sucesso, mensagem:"Pedido criado com sucesso"} |
| 35 | POST | /pedidos | produto 999 | 400 | {erro:"Produto 999 não encontrado", sucesso:false} |
| 36 | POST | /pedidos | quantidade 100 (estoque 8) | 400 | {erro:"Estoque insuficiente para Cadeira Gamer", sucesso:false} |
| 37 | POST | /pedidos | itens [] | 400 | {erro:"Pedido deve ter pelo menos 1 item"} |
| 38 | POST | /pedidos | usuario_id 999 | 400 | {erro:"Usuário não encontrado", sucesso:false} |
| 39 | GET | /pedidos | `X-Admin-Token` | 200 | {dados:[{id,usuario_id,status,total,criado_em,itens:[{produto_id,produto_nome,quantidade,preco_unitario}]}] (1), sucesso} |
| 40 | GET | /pedidos/usuario/2 | sem token | 200 | {dados:[pedido] (1), sucesso} — pedido completo de outro usuário, sem auth |
| 41 | GET | /relatorios/vendas | `X-Admin-Token` | 200 | total_pedidos:1, faturamento_bruto:6179.79, desconto_aplicavel:308.99 (5%), faturamento_liquido:5870.80, pedidos_pendentes:1, ticket_medio:6179.79 |
| 42 | GET | /produtos/1 | - | 200 | estoque 10 → 9 após o pedido |
| 43 | PUT | /produtos/11 | válido, sem token | 401 | {erro:"Não autorizado"} |
| 44 | PUT | /produtos/11 | válido, `X-Admin-Token` | 200 | {sucesso, mensagem:"Produto atualizado"} |
| 45 | PUT | /produtos/999 | `X-Admin-Token` | 404 | {erro:"Produto não encontrado"} |
| 46 | PUT | /produtos/11 | {"nome":"x"} | 400 | {erro:"Preço é obrigatório"} |
| 47 | PUT | /produtos/11 | categoria "invalida" | 400 | {erro:"Categoria inválida. Válidas: [...]"} |
| 48 | PUT | /pedidos/1/status | sem token | 401 | {erro:"Não autorizado"} |
| 49 | PUT | /pedidos/1/status | {"status":"aprovado"} + token | 200 | {sucesso, mensagem:"Status atualizado"} |
| 50 | PUT | /pedidos/1/status | {"status":"foo"} + token | 400 | {erro:"Status inválido"} |
| 51 | PUT | /pedidos/999/status | token | 404 | {erro:"Pedido não encontrado"} |
| 52 | DELETE | /produtos/999 | token | 404 | {erro:"Produto não encontrado"} |
| 53 | POST | /admin/query | SELECT, sem token | 401 | {erro:"Não autorizado"} |
| 54 | POST | /admin/query | {"sql":"SELECT id, email, senha FROM usuarios"} + token | 200 | {dados:[{id,email,senha}] (4), sucesso} — **hashes de senha retornados** |
| 55 | POST | /admin/query | {} + token | 400 | {erro:"Query não informada"} |
| 56 | POST | /admin/query | {"sql":"SELEC x"} + token | 400 | {erro:"Apenas consultas SELECT são permitidas"} |
| 57 | POST | /admin/query | {"sql":"DELETE FROM produtos"} + token | 400 | {erro:"Apenas consultas SELECT são permitidas"} |
| 58 | GET | /health | - | 200 | counts{produtos:12,usuarios:4,pedidos:1} |
| 59 | POST | /admin/reset-db | sem token | 401 | {erro:"Não autorizado"} |
| 60 | POST | /admin/reset-db | token | 200 | {mensagem:"Banco de dados resetado", sucesso:true} |
| 61 | GET | /health | - | 200 | counts{produtos:0,usuarios:0,pedidos:0} |
| 62 | POST | /produtos | {"nome":"Temp","preco":1,"estoque":1} + token | 201 | {dados:{id:13}, sucesso} (AUTOINCREMENT continua após o reset) |
| 63 | DELETE | /produtos/13 | token | 200 | {sucesso, mensagem:"Produto deletado"} |
| 64 | DELETE | /produtos/13 | token | 404 | {erro:"Produto não encontrado"} |
| 65 | GET | /__rota-inexistente__ | - | 404 | `application/json` — {erro:"The requested URL was not found on the server. ..."} |
| 66 | DELETE | /produtos | - | 405 | `application/json` — {erro:"The method is not allowed for the requested URL."} |

Observações:

- Log (`.refactor-arch/baseline-server.log`, rodado com `PYTHONWARNINGS=default`): nenhum traceback, nenhuma exceção, nenhum `DeprecationWarning`. Apenas o aviso padrão do servidor de desenvolvimento do Werkzeug e o `WARNING ... BANCO DE DADOS RESETADO` do `/admin/reset-db`. Logs de aplicação não contêm PII (apenas ids).
- Nenhum segredo aparece em resposta: `/health` não expõe mais `secret_key`/`db_path`/`debug`; `/usuarios*` não expõe `senha`.
- 9 rotas exigem `X-Admin-Token`; todas devolvem `401 {"erro":"Não autorizado"}` sem o header.
- **Autorização ausente em 4 rotas**: `GET /usuarios/<id>` (#13), `GET /pedidos/usuario/<id>` (#40) e `POST /pedidos` (#34) são públicas e operam sobre dados de qualquer usuário informado por ID. `POST /login` (#20) não devolve token nem sessão, então não existe credencial de usuário comum para proteger essas rotas.
- `POST /admin/query` continua executando SQL arbitrário (restrito a um SELECT em conexão read-only) e devolve os hashes de senha (#54).
- Após `POST /admin/reset-db`, o banco fica vazio e o seed **não** roda de novo até o próximo boot (verificado: reinício na porta 5202 reseedou 10 produtos / 3 usuários, com novos IDs por causa do AUTOINCREMENT).
- Erros 404/405 já saem em JSON pelo handler central, mas com a descrição em inglês do Werkzeug (`err.description`, `middlewares/error_handler.py:21`), enquanto o resto da API responde em português.
- `loja.db` criado durante o baseline foi apagado ao final (estado inicial = sem banco). Servidores das portas 5201 e 5202 encerrados (`lsof` vazio).
