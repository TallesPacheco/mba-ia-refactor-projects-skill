# Baseline — code-smells-project
Boot: `.venv/bin/flask --app app run --host 127.0.0.1 --port 5101` (porta 5101; comando original `python app.py` tem host 0.0.0.0/porta 5000/debug=True hardcoded em app.py:88, por isso subiu via CLI sem editar) | Seed: automático na 1ª chamada de `get_db()` (database.py:7-86) — cria `loja.db` no CWD com 10 produtos e 3 usuários.
Versões: Python 3.14.3 / Flask 3.1.1 (Werkzeug 3.1.9) / flask-cors 5.0.1 / sqlite3 (stdlib)
Recriar estado inicial: `rm -f loja.db` (gitignored, criado por este baseline e apagado ao final) e subir o app; a 1ª requisição recria schema + seed.

Requisições executadas na ordem abaixo, banco recém-criado (IDs refletem essa ordem).

| # | Método | Path | Payload | Status | Shape da resposta (chaves de topo / tipo) |
|---|---|---|---|---|---|
| 1 | GET | / | - | 200 | {mensagem, versao, endpoints{produtos,usuarios,pedidos,login,relatorios,health}} |
| 2 | GET | /health | - | 200 | {status:"ok", database, counts{produtos:10,usuarios:3,pedidos:0}, versao, ambiente, db_path, debug:true, secret_key:"minha-chave-super-secreta-123"} |
| 3 | GET | /produtos | - | 200 | {dados:[{id,nome,descricao,preco,estoque,categoria,ativo,criado_em}] (10), sucesso} |
| 4 | GET | /produtos/1 | - | 200 | {dados:{id,nome,descricao,preco,estoque,categoria,ativo,criado_em}, sucesso} |
| 5 | GET | /produtos/999 | - | 404 | {erro:"Produto não encontrado", sucesso:false} |
| 6 | GET | /produtos/busca?q=gamer | - | 200 | {dados:[produto] (3), total:3, sucesso} |
| 7 | GET | /produtos/busca?categoria=moveis&preco_min=100&preco_max=2000 | - | 200 | {dados:[produto] (1), total:1, sucesso} |
| 8 | GET | /produtos/busca?q=' OR 1=1-- | - | 500 | {erro:"incomplete input"} (mensagem SQLite vazada) |
| 9 | GET | /produtos/busca?q=x') OR 1=1 --  | - | 200 | {dados:[todos os 10], ...} — SQL injection confirmada |
| 10 | GET | /usuarios | - | 200 | {dados:[{id,nome,email,senha,tipo,criado_em}] (3), sucesso} — **senha em texto puro** |
| 11 | GET | /usuarios/1 | - | 200 | {dados:{id,nome,email,senha,tipo,criado_em}, sucesso} — senha "admin123" |
| 12 | GET | /usuarios/999 | - | 404 | {erro:"Usuário não encontrado"} (sem `sucesso`) |
| 13 | GET | /pedidos | - | 200 | {dados:[], sucesso} |
| 14 | GET | /pedidos/usuario/2 | - | 200 | {dados:[], sucesso} |
| 15 | GET | /relatorios/vendas | - | 200 | {dados:{total_pedidos,faturamento_bruto,desconto_aplicavel,faturamento_liquido,pedidos_pendentes,pedidos_aprovados,pedidos_cancelados,ticket_medio}, sucesso} (tudo 0) |
| 16 | POST | /login | {"email":"admin@loja.com","senha":"admin123"} | 200 | {dados:{id,nome,email,tipo}, sucesso, mensagem:"Login OK"} |
| 17 | POST | /login | {"email":"admin@loja.com","senha":"errada"} | 401 | {erro:"Email ou senha inválidos", sucesso:false} |
| 18 | POST | /login | {"email":"admin@loja.com' --","senha":"x"} | 200 | login como Admin sem senha — SQL injection / bypass de auth |
| 19 | POST | /login | {} | 400 | {erro:"Email e senha são obrigatórios"} |
| 20 | POST | /login | (sem body / sem Content-Type) | 500 | {erro:"415 Unsupported Media Type: ..."} |
| 21 | POST | /produtos | {"nome":"Livro Python","descricao":"Livro","preco":99.9,"estoque":5,"categoria":"livros"} | 201 | {dados:{id:11}, sucesso, mensagem:"Produto criado"} |
| 22 | POST | /produtos | {"nome":"X"} | 400 | {erro:"Preço é obrigatório"} |
| 23 | POST | /produtos | {"nome":"Bad","preco":1,"estoque":1,"categoria":"xyz"} | 400 | {erro:"Categoria inválida. Válidas: [...]"} |
| 24 | POST | /produtos | {"nome":"Neg","preco":-1,"estoque":1} | 400 | {erro:"Preço não pode ser negativo"} |
| 25 | POST | /produtos | {"nome":"O'Reilly","preco":1,"estoque":1} | 500 | {erro:"near \"Reilly\": syntax error"} — apóstrofo quebra SQL concatenado |
| 26 | POST | /usuarios | {"nome":"Teste","email":"teste@email.com","senha":"abc123"} | 201 | {dados:{id:4}, sucesso} |
| 27 | POST | /usuarios | {"nome":"Teste"} | 400 | {erro:"Nome, email e senha são obrigatórios"} |
| 28 | POST | /pedidos | {"usuario_id":2,"itens":[{"produto_id":1,"quantidade":1},{"produto_id":2,"quantidade":2}]} | 201 | {dados:{pedido_id:1,total:6179.79}, sucesso, mensagem:"Pedido criado com sucesso"} |
| 29 | POST | /pedidos | {"usuario_id":2,"itens":[{"produto_id":999,"quantidade":1}]} | 400 | {erro:"Produto 999 não encontrado", sucesso:false} |
| 30 | POST | /pedidos | {"usuario_id":2,"itens":[{"produto_id":6,"quantidade":100}]} | 400 | {erro:"Estoque insuficiente para Cadeira Gamer", sucesso:false} |
| 31 | POST | /pedidos | {"usuario_id":2,"itens":[]} | 400 | {erro:"Pedido deve ter pelo menos 1 item"} |
| 32 | POST | /pedidos | {"usuario_id":999,"itens":[{"produto_id":2,"quantidade":1}]} | 201 | {dados:{pedido_id:2,total:89.9}, ...} — usuário inexistente aceito |
| 33 | GET | /pedidos | - | 200 | {dados:[{id,usuario_id,status,total,criado_em,itens:[{produto_id,produto_nome,quantidade,preco_unitario}]}] (2), sucesso} |
| 34 | GET | /pedidos/usuario/2 | - | 200 | {dados:[pedido] (1), sucesso} |
| 35 | GET | /relatorios/vendas | - | 200 | total_pedidos:2, faturamento_bruto:6269.69, desconto_aplicavel:313.48 (5%), faturamento_liquido:5956.21, pedidos_pendentes:2, ticket_medio:3134.84 |
| 36 | GET | /produtos/1 | - | 200 | estoque 10 → 9 após pedido |
| 37 | PUT | /produtos/11 | {"nome":"Livro Python 2","descricao":"Livro","preco":89.9,"estoque":4,"categoria":"livros"} | 200 | {sucesso, mensagem:"Produto atualizado"} |
| 38 | PUT | /produtos/999 | {"nome":"x","preco":1,"estoque":1} | 404 | {erro:"Produto não encontrado"} |
| 39 | PUT | /produtos/11 | {"nome":"x"} | 400 | {erro:"Preço é obrigatório"} |
| 40 | PUT | /produtos/11 | {"nome":"y","preco":1,"estoque":1,"categoria":"invalida"} | 200 | {sucesso, mensagem} — categoria não validada no PUT (diverge do POST) |
| 41 | PUT | /pedidos/1/status | {"status":"aprovado"} | 200 | {sucesso, mensagem:"Status atualizado"} |
| 42 | PUT | /pedidos/1/status | {"status":"foo"} | 400 | {erro:"Status inválido"} |
| 43 | PUT | /pedidos/999/status | {"status":"aprovado"} | 200 | {sucesso, mensagem} — pedido inexistente retorna 200 |
| 44 | DELETE | /produtos/999 | - | 404 | {erro:"Produto não encontrado"} |
| 45 | POST | /admin/query | {"sql":"SELECT id, email, senha FROM usuarios"} | 200 | {dados:[{id,email,senha}] (4), sucesso} — SQL arbitrário sem auth, expõe senhas |
| 46 | POST | /admin/query | {} | 400 | {erro:"Query não informada"} |
| 47 | POST | /admin/query | {"sql":"SELEC x"} | 500 | {erro:"near \"SELEC\": syntax error"} |
| 48 | GET | /health | - | 200 | counts{produtos:11,usuarios:4,pedidos:2} |
| 49 | POST | /admin/reset-db | - | 200 | {mensagem:"Banco de dados resetado", sucesso:true} — sem auth, apaga as 4 tabelas |
| 50 | GET | /health | - | 200 | counts{produtos:0,usuarios:0,pedidos:0} |
| 51 | POST | /produtos | {"nome":"Temp","preco":1,"estoque":1} | 201 | {dados:{id:12}, ...} (após reset; AUTOINCREMENT continua) |
| 52 | DELETE | /produtos/12 | - | 200 | {sucesso, mensagem:"Produto deletado"} |
| 53 | DELETE | /produtos/12 | - | 404 | {erro:"Produto não encontrado"} |
| 54 | GET | /nao-existe | - | 404 | página HTML padrão do Werkzeug |

Observações:
- Log (`.refactor-arch/baseline-server.log`): nenhum traceback, nenhum DeprecationWarning (rodado com `PYTHONWARNINGS=default`); apenas o aviso padrão "development server". Saída dos `print()` não apareceu no log (stdout bufferizado sob nohup), logo não há log útil.
- Uma 1ª rodada (`.refactor-arch/baseline-server.run0.log`) foi invalidada por erro de quoting do header no zsh; mostrou que POST/PUT sem `Content-Type: application/json` retornam 500 com `{"erro":"415 Unsupported Media Type: ..."}` (exceção do Flask capturada pelo `except Exception`), exceto `/admin/query`, que retorna 415 HTML (sem try ao redor de `get_json`).
- Dados sensíveis: `/health` expõe `secret_key` e `debug`; `/usuarios` e `/usuarios/<id>` expõem `senha` em texto puro; senhas armazenadas sem hash.
- SQL injection confirmada em `/login` (bypass) e `/produtos/busca`; erros SQLite vazados em respostas 500.
- `/pedidos` aceita `usuario_id` inexistente; `PUT /pedidos/<id>/status` retorna 200 para pedido inexistente; status "cancelado" não devolve estoque (só print).
- Via CLI, Flask reporta "Debug mode: off"; com `python app.py`, debug=True + host 0.0.0.0 (Werkzeug debugger exposto).
- `loja.db` criado no CWD durante o baseline foi apagado ao final (estado inicial = sem banco).
