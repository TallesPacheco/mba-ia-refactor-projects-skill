================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.14 + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 7 | HIGH: 4 | MEDIUM: 6 | LOW: 4

## Findings

### [CRITICAL] Credenciais / segredos hardcoded (AP-01)
File: app.py:7
File: controllers.py:289
File: database.py:76-78
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` está literal no entry point e o mesmo valor é repetido como literal na resposta do health check. O seed grava credenciais reais em texto puro no código: `("Admin", "admin@loja.com", "admin123", "admin")`, `"123456"`, `"senha123"`.
Impact: qualquer pessoa com acesso ao repositório (ou à rota /health) obtém a chave de assinatura de sessão do Flask e a senha do usuário administrador. Baseline: `GET /health` → 200 com `"secret_key":"minha-chave-super-secreta-123"`; `POST /login` com `admin@loja.com`/`admin123` → 200.
Recommendation: mover SECRET_KEY e demais configurações para um módulo de config lido de variáveis de ambiente (com `.env.example` de valores fictícios); seed de admin com senha vinda de env ou gerada, nunca literal (playbook PB-01)

### [CRITICAL] SQL Injection (AP-02)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166
File: models.py:174, 188, 192, 220, 224, 279-281, 289-299
File: app.py:59-78
Description: todas as queries de models.py são montadas por concatenação de strings com valores vindos do request, ex.: `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` (login) e `" AND (nome LIKE '%" + termo + "%' ..."` (busca). Nenhum placeholder `?` é usado fora do seed. Em app.py, `/admin/query` executa `cursor.execute(query)` com o SQL enviado pelo cliente.
Impact: bypass de autenticação e leitura/alteração arbitrária do banco. Baseline: `POST /login {"email":"admin@loja.com' --","senha":"x"}` → 200 logado como Admin; `GET /produtos/busca?q=x') OR 1=1 -- ` → 200 com todos os produtos; `POST /produtos {"nome":"O'Reilly",...}` → 500 `near "Reilly": syntax error` (nomes legítimos com apóstrofo quebram).
Recommendation: reescrever todas as queries com parâmetros (`cursor.execute("... WHERE id = ?", (id,))`), montar filtros dinâmicos da busca com lista de cláusulas + lista de parâmetros; remover o executor de SQL arbitrário (ver AP-06) (playbook PB-02)

### [CRITICAL] God File / responsabilidades misturadas (AP-03)
File: models.py:1-314
File: app.py:1-88
Description: models.py (314 linhas, maior arquivo) concentra acesso a dados dos três domínios (produtos, usuários, pedidos), serialização manual row→dict e regras de negócio (validação de estoque e cálculo de total em `criar_pedido` linhas 133-169, faixas de desconto em `relatorio_vendas` linhas 256-262). app.py mistura criação do app, configuração literal (linhas 6-9), registro de todas as rotas (11-30) e handlers com SQL inline (`reset_database` 47-57, `executar_query` 59-78).
Impact: não existe camada de serviço nem fronteira entre HTTP, regra e persistência; qualquer mudança em um domínio toca o mesmo arquivo, e regras não podem ser testadas sem banco nem Flask.
Recommendation: dividir em models/repositórios por entidade (produto, usuario, pedido), services com as regras (pedido, relatório), controllers finos e routes/blueprints; app.py vira composition root (playbook PB-03, PB-04)

### [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, 99
File: controllers.py:161, 179, 182, 284-289
Description: `get_todos_usuarios` e `get_usuario_por_id` serializam `"senha": row["senha"]` direto na resposta. O health check devolve `secret_key`, `db_path`, `debug` e `ambiente`. Login/cadastro escrevem o e-mail do usuário em stdout via `print` (PII em log).
Impact: baseline: `GET /usuarios` → 200 com `"senha":"admin123"`, `"123456"`, `"senha123"` de todos os usuários; `GET /usuarios/1` → 200 com senha do admin; `GET /health` → 200 com `secret_key` e `debug:true`.
Recommendation: remover `senha` de toda serialização de usuário; health check retorna apenas status/contagens; logs sem PII (playbook PB-06)

### [CRITICAL] Senha armazenada sem hash (AP-05)
File: database.py:31
File: models.py:109-111, 126-129
Description: a coluna `senha TEXT` guarda a senha em texto puro: `criar_usuario` insere o valor recebido diretamente e `login_usuario` compara a senha em claro dentro do SQL (`AND senha = '" + senha + "'`). Nenhuma lib de hash (`werkzeug.security`, bcrypt, argon2) é usada no projeto.
Impact: vazamento do banco (trivial via AP-02/AP-06) expõe as senhas reais de todos os clientes. Baseline: `POST /admin/query {"sql":"SELECT id, email, senha FROM usuarios"}` → 200 com as 4 senhas em claro.
Recommendation: `werkzeug.security.generate_password_hash` no cadastro e no seed, `check_password_hash` no login (buscar por e-mail com parâmetro e verificar o hash em Python) (playbook PB-05)

### [CRITICAL] Endpoints administrativos/destrutivos sem autenticação (AP-06)
File: app.py:47-57, 59-78
File: app.py:14-16, 18-19, 24, 26, 28
Description: `POST /admin/reset-db` apaga as 4 tabelas e `POST /admin/query` executa qualquer SQL enviado no corpo — ambos sem qualquer autenticação. Também não há auth em criação/edição/deleção de produtos, listagem de usuários, listagem de todos os pedidos, mudança de status de pedido nem no relatório financeiro. Não existe `before_request`/decorator de auth; o login não emite token e o campo `tipo` ("admin") nunca é verificado.
Impact: qualquer cliente anônimo destrói ou lê o banco inteiro. Baseline: `POST /admin/reset-db` → 200 e `GET /health` em seguida mostra `counts` todos 0; `POST /admin/query` → 200 com e-mails e senhas.
Recommendation: manter as rotas, mas exigir credencial de admin (ex.: header `X-Admin-Token` lido de env) em `/admin/*` e nas rotas de escrita/relatório; restringir `/admin/query` (somente leitura com auth, ou desativado por config) (playbook PB-07)

### [CRITICAL] Debug ligado / bind em 0.0.0.0 (AP-07)
File: app.py:8, 88
File: controllers.py:286
Description: `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)` com host, porta e debug literais; o health check se anuncia como `"ambiente": "producao"` com debug ligado.
Impact: com `python app.py` (start documentado no README), o debugger interativo do Werkzeug fica acessível em todas as interfaces de rede, permitindo execução remota de código; porta não configurável (o baseline precisou subir via `flask --app app run --port 5101` para contornar).
Recommendation: debug/host/porta vindos de config/env com padrão seguro (`debug=False`, `127.0.0.1`), lidos no composition root (playbook PB-01, PB-16)

### [HIGH] Regra de negócio fora da camada de serviço (AP-08)
File: models.py:133-169, 256-262
File: controllers.py:28-54, 208-210, 242-250, 264-292
File: app.py:47-78
Description: a criação de pedido (verificação de estoque, cálculo do total, baixa de estoque) e as faixas de desconto do relatório estão no model; validações de produto, a lista de status válidos e as "notificações" (e-mail/SMS/push simulados por `print`) estão nos controllers; `health_check` e as rotas admin executam SQL direto no handler. A regra "cancelado → devolver estoque" existe só como `print` (controllers.py:250) e nunca é aplicada.
Impact: regras espalhadas entre camadas, impossíveis de testar isoladamente e já inconsistentes (cancelamento não devolve estoque).
Recommendation: criar services (`pedido_service`, `relatorio_service`, `produto_service`) com as regras e notificações; controllers apenas traduzem HTTP ↔ service; models só persistem (playbook PB-04)

### [HIGH] Conexão global compartilhada sem DI (AP-09)
File: database.py:4-11
File: models.py:1
File: controllers.py:3
Description: `db_connection = None` em nível de módulo, `global db_connection` e `sqlite3.connect(db_path, check_same_thread=False)` — uma única conexão reutilizada por todas as threads/requisições; cada função chama `get_db()` diretamente (sem injeção).
Impact: o servidor multi-thread do Werkzeug compartilha o mesmo objeto de conexão/transação entre requisições concorrentes (commits de uma requisição efetivam escritas parciais de outra); impossível trocar o banco em testes.
Recommendation: conexão por requisição em `flask.g` com `teardown_appcontext`, caminho do banco vindo de config, repositórios recebendo a conexão (playbook PB-17)

### [HIGH] Escritas multi-etapa sem transação (AP-10)
File: models.py:133-169
File: app.py:51-55
Description: `criar_pedido` faz SELECT de estoque, INSERT em `pedidos`, N INSERTs em `itens_pedido` e N UPDATEs de estoque com um único `commit()` no fim e sem `rollback` em caso de erro. A checagem `produto["estoque"] < item["quantidade"]` (linha 144) é separada do `UPDATE produtos SET estoque = estoque - ...` (linhas 163-166), sem condição `WHERE estoque >= ?`.
Impact: exceção no meio do loop deixa o pedido parcial pendente na conexão global, que é efetivado pelo próximo `commit()` de qualquer outra requisição (pedido sem itens / estoque baixado pela metade); pedidos concorrentes podem vender acima do estoque (condição de corrida).
Recommendation: envolver o fluxo em transação explícita (`with conn:` / BEGIN…COMMIT com rollback) e baixar estoque com UPDATE condicional verificando linhas afetadas (playbook PB-09)

### [HIGH] Sem módulo de config / app factory; efeitos colaterais na 1ª chamada (AP-11)
File: app.py:6-9
File: database.py:5, 7-86
Description: `app = Flask(__name__)` global com config literal, sem `create_app()`, sem `config.py`/settings e nenhuma leitura de `os.environ` no projeto; o caminho `"loja.db"` é fixo (relativo ao CWD) e `get_db()` cria schema e roda seed na primeira chamada de qualquer função.
Impact: impossível instanciar o app com outra config (teste, outro banco, produção); o banco é criado onde quer que o processo seja iniciado.
Recommendation: módulo `config/settings.py` lendo env, `create_app(config)` como composition root, init de schema/seed explícito na factory; manter `app = create_app()` em app.py para `python app.py` e `flask --app app run` continuarem funcionando (playbook PB-01, PB-16)

### [MEDIUM] Erros engolidos / sem error handler central / mensagem interna vazada (AP-12)
File: controllers.py:10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291
File: app.py:77-78
Description: 17 blocos `except Exception as e:` idênticos devolvem `jsonify({"erro": str(e)}), 500`; não há `errorhandler`/`register_error_handler`. Erros 404/415 fora desses blocos saem em HTML do Werkzeug (formato misto).
Impact: mensagens internas do SQLite e do Flask chegam ao cliente. Baseline: `GET /produtos/busca?q=' OR 1=1--` → 500 `{"erro":"incomplete input"}`; `POST /login` sem Content-Type → 500 `{"erro":"415 Unsupported Media Type: ..."}`; `POST /admin/query` sem Content-Type → 415 HTML; `GET /nao-existe` → 404 HTML.
Recommendation: exceções de domínio + error handler central que mantém a chave `erro` e o formato JSON, retornando mensagem genérica em 500 e logando o detalhe (playbook PB-08)

### [MEDIUM] Queries N+1 / agregação com várias queries (AP-13)
File: models.py:186-199, 218-231
File: models.py:139-141, 154-156
File: models.py:239-254
File: controllers.py:269-274
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 query de pedidos + 1 por pedido (itens) + 1 por item (nome do produto); `criar_pedido` busca o mesmo produto duas vezes por item; `relatorio_vendas` faz 5 queries separadas (COUNT, SUM e 3 COUNT por status) em vez de um `GROUP BY`.
Impact: número de queries cresce linearmente com pedidos × itens (`GET /pedidos`), degradando com o volume.
Recommendation: JOIN `itens_pedido` × `produtos` com `WHERE pedido_id IN (...)` agrupando em Python; relatório com `SELECT status, COUNT(*), SUM(total) ... GROUP BY status`; reaproveitar o produto já lido no pedido (playbook PB-10)

### [MEDIUM] Validação de entrada ausente (AP-14)
File: controllers.py:37-50, 81-90, 118-121, 153-158, 169-171, 195-201, 239-242
File: models.py:139-146, 275-283
Description: `preco`/`estoque` não têm tipo verificado (`preco < 0` com string → TypeError → 500); o PUT de produto não valida categoria nem tamanho do nome (divergente do POST); `float(preco_min)` sem tratamento; `request.get_json()` pode ser `None` e `dados.get(...)` em login/status quebra; itens do pedido não têm `quantidade` validada (quantidade negativa passa no teste de estoque e aumenta o estoque via `estoque - (-n)`), nem existência de `usuario_id`; e-mail sem formato; atualização de status não verifica se o pedido existe.
Impact: baseline: `PUT /produtos/11` com `"categoria":"invalida"` → 200; `POST /pedidos` com `usuario_id: 999` (inexistente) → 201; `PUT /pedidos/999/status` → 200 para pedido inexistente; `POST /login` sem body JSON → 500.
Recommendation: validadores por recurso (presença, tipo numérico, faixa, quantidade > 0, categoria/status em constantes, e-mail) compartilhados entre POST e PUT, retornando 400/404 no formato `{"erro": ...}` atual (playbook PB-11)

### [MEDIUM] Código duplicado (AP-15)
File: models.py:12-21, 31-40, 304-313
File: models.py:79-86, 95-102
File: models.py:171-201, 203-233
File: controllers.py:28-50, 72-90
Description: o mapeamento row→dict de produto é copiado 3 vezes e o de usuário 2 vezes; `get_pedidos_usuario` e `get_todos_pedidos` são idênticos exceto pelo WHERE; as validações de produto de `criar_produto` e `atualizar_produto` foram copiadas e já divergem (PUT não valida categoria nem tamanho do nome).
Impact: correções precisam ser feitas em vários lugares e as cópias já estão inconsistentes (ver AP-14).
Recommendation: funções únicas de serialização por entidade, uma função de listagem de pedidos com filtro opcional e um validador de produto compartilhado (playbook PB-18)

### [MEDIUM] CORS aberto para qualquer origem (AP-18)
File: app.py:9
Description: `CORS(app)` sem `origins`, liberando todas as rotas — inclusive `/admin/reset-db` e `/admin/query` — para qualquer origem; não há camada de middleware para auth nem para erros.
Impact: qualquer site aberto no navegador de um usuário pode chamar a API (e os endpoints destrutivos) e ler as respostas.
Recommendation: origens permitidas vindas de config (`CORS(app, origins=settings.CORS_ORIGINS)`), registrado na app factory junto com os middlewares de auth/erro (playbook PB-19)

### [MEDIUM] Integridade referencial ausente (AP-19)
File: database.py:14-53
File: models.py:65-70, 196, 228
File: app.py:51-54
Description: nenhuma tabela declara `FOREIGN KEY`, `UNIQUE` ou `NOT NULL` (`pedidos.usuario_id`, `itens_pedido.pedido_id/produto_id` soltos, `usuarios.email` sem UNIQUE) e não há `PRAGMA foreign_keys = ON`. Deletar um produto deixa itens de pedido órfãos — o código já contorna com o fallback `"Desconhecido"`; o reset apaga as tabelas em ordem manual.
Impact: baseline: `POST /pedidos` com `usuario_id: 999` → 201 (pedido para usuário inexistente); e-mails duplicados podem ser cadastrados, tornando o login ambíguo.
Recommendation: constraints no schema (FK, UNIQUE em email, NOT NULL), `PRAGMA foreign_keys = ON` por conexão e checagem de existência no service antes de criar pedido (playbook PB-20)

### [LOW] Magic numbers / strings (AP-20)
File: models.py:247, 250, 253, 257-262
File: controllers.py:47-52, 242, 285
File: app.py:36, 85, 88
File: database.py:5
Description: faixas de desconto `10000/5000/1000` com `0.1/0.05/0.02`, limites de nome `2`/`200`, lista literal de categorias e de status, status `'pendente'/'aprovado'/'cancelado'` repetidos em SQL, versão `"1.0.0"` duplicada, porta `5000` e `"loja.db"` literais.
Impact: regras de negócio escondidas em literais repetidos; mudar uma faixa ou status exige caçar ocorrências.
Recommendation: módulo de constantes (`STATUS_PEDIDO`, `CATEGORIAS_VALIDAS`, `FAIXAS_DESCONTO`, `APP_VERSION`) e valores de infraestrutura na config (playbook PB-14)

### [LOW] Nomenclatura ruim / sombreamento de builtin (AP-21)
File: controllers.py:14, 56, 64, 98, 136, 160
File: models.py:24, 54, 65, 89, 187-193, 219-225
Description: parâmetros e variáveis chamados `id` sombreiam o builtin `id()`; cursores `cursor2`/`cursor3` e `prod` são nomes sem significado.
Impact: leitura mais difícil e risco de bug ao usar o builtin dentro dessas funções.
Recommendation: renomear internamente para `produto_id`, `usuario_id`, `novo_id`, `itens_cursor` etc., mantendo os nomes de parâmetros de rota/contrato HTTP intactos (playbook PB-18)

### [LOW] `print` como logging (AP-22)
File: app.py:56, 83-86
File: controllers.py:8, 11, 57, 61, 106, 208-210, 219, 248, 250
Description: 19 chamadas `print()` sem nível nem formatação, incluindo notificações simuladas ("ENVIANDO EMAIL/SMS/PUSH", "NOTIFICAÇÃO"). (Os prints com e-mail do usuário estão registrados em AP-04.)
Impact: sem níveis/timestamps; no baseline, sob `nohup`, a saída ficou bufferizada e nada desses prints apareceu em `.refactor-arch/baseline-server.log`.
Recommendation: `logging.getLogger(__name__)` com níveis (info/warning/exception) configurado na app factory; notificações como serviço próprio que loga (playbook PB-15)

### [LOW] Imports não usados (AP-23)
File: database.py:2
File: models.py:2
Description: `import os` em database.py e `import sqlite3` em models.py nunca são usados (confirmado por análise AST: nenhum nome referenciado). Todas as dependências do requirements (`flask`, `flask-cors`) são importadas.
Impact: ruído e falsa impressão de dependência entre módulos.
Recommendation: remover os imports mortos durante o split em camadas (playbook PB-18)

Deprecated APIs: nenhuma ocorrência encontrada (greps: utcnow/utcfromtimestamp, .query.get, Model.query., get_or_404/first_or_404, before_first_request, JSONEncoder/json_encoder, _app_ctx_stack/_request_ctx_stack, attachment_filename, hashlib md5/sha1/sha256, ext.declarative, engine.execute/execute("SQL") — este último casou apenas `cursor.execute` do sqlite3 stdlib, que não é API deprecated —, type(x) ==; baseline rodado com PYTHONWARNINGS=default sem DeprecationWarning no log)
Verificados sem ocorrência: AP-16 (callback hell — não se aplica, código síncrono)

================================
Total: 21 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
