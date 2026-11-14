================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.14.3 + Flask 3.1.1
Files:   40 analyzed | ~1120 lines of code

## Summary
CRITICAL: 2 | HIGH: 3 | MEDIUM: 2 | LOW: 3

## Findings

### [CRITICAL] Credenciais de seed e fallbacks literais de segredo (AP-01)
File: db/schema.py:61-65
File: config/settings.py:11, 16, 22-23
Description: `SEED_USUARIOS` (db/schema.py:62-64) contém os hashes scrypt de três contas fixas, entre elas `admin@loja.com` com `tipo = "admin"`. Os hashes são de senhas conhecidas e publicadas no `refactor-summary.md` da execução anterior (`admin123`, `123456`, `senha123`) — pré-computar o hash não muda o fato de que a credencial inteira vive no repositório. Em paralelo, `config/settings.py:11` e `:16` definem fallbacks literais para os dois segredos da aplicação (`SECRET_KEY = "dev-only-insecure-key"`, `ADMIN_TOKEN = "dev-admin-token"`), e `Config.validate()` só exige as variáveis de ambiente quando `APP_ENV == "production"` (`config/settings.py:22-23`). Com `APP_ENV` ausente ou com qualquer outro valor (`staging`, `prod`, `homolog`), o boot aceita silenciosamente os valores de desenvolvimento.
Impact: qualquer pessoa com acesso ao repositório autentica como administrador da loja em qualquer instalação que rode o seed — baseline #20: `POST /login {"email":"admin@loja.com","senha":"admin123"}` → 200 com `tipo:"admin"`. E qualquer implantação que esqueça `APP_ENV=production` fica com `X-Admin-Token: dev-admin-token` válido, liberando as 9 rotas administrativas (baseline #12, #54, #60) para qualquer cliente que conheça o default.
Recommendation: gerar as senhas de seed em runtime (`secrets.token_urlsafe`) quando a variável de ambiente correspondente não existir e imprimi-las uma única vez no console, sem nenhum fallback literal; remover os hashes de `db/schema.py`. Tornar `SECRET_KEY` e `ADMIN_TOKEN` obrigatórios por padrão, com o modo permissivo explícito (`APP_ENV == "development"`) em vez do modo estrito explícito. (playbook PB-01, PB-25)

### [CRITICAL] Login não estabelece sessão: nenhuma rota consegue autorizar por usuário (AP-24)
File: views/usuario_routes.py:26-29
File: controllers/usuario_controller.py:24-26
File: services/usuario_service.py:25-31
File: middlewares/auth.py:11-20
Description: `POST /login` autentica a senha corretamente (scrypt via `check_password_hash`) e devolve apenas `{"dados": {id, nome, email, tipo}}` — nenhum token, cookie de sessão ou identificador assinado. O único mecanismo de autorização do projeto é `require_admin` (`middlewares/auth.py:11-20`), que compara um token **estático e compartilhado** vindo do header `X-Admin-Token` com `config["ADMIN_TOKEN"]`; ele identifica "um administrador qualquer", nunca um usuário. Greps confirmam que não existe emissor nem verificador de credencial de usuário: `grep -rnE "verify_token|jwt\.(decode|verify)|serializer\.loads|headers\.get\(['\"]Authorization" --include='*.py' .` → vazio; `grep -rniE "itsdangerous|jwt|uuid4\(\)" --include='*.py' .` → vazio (apesar de `itsdangerous` 2.2.0 já estar instalado como dependência do Flask).
Impact: a autenticação é decorativa. Como não há identidade de chamador, toda rota que opera sobre dados de um usuário precisa escolher entre ficar aberta (é o que acontece hoje — ver AP-25 e AP-06) ou exigir o token de admin, que não pode ser distribuído a clientes. O token de admin também é único, sem expiração, sem rotação e sem rastro de quem o usou. Não há qualquer limite de tentativas em `POST /login` (baseline #21 e #22: falhas sucessivas respondem 401 na mesma velocidade), o que torna o endpoint um alvo direto de força bruta.
Recommendation: emitir no login um token assinado com `SECRET_KEY` e expiração (`itsdangerous.URLSafeTimedSerializer`, já disponível; ou JWT), criar um decorator `require_auth` que leia `Authorization: Bearer <token>`, valide a assinatura e exponha o usuário corrente, e um `require_self_or_admin` para as rotas por ID. Preservar o shape atual da resposta de login acrescentando a chave `token`. Acrescentar throttling por IP/e-mail no login. (playbook PB-21)

### [HIGH] Rotas de escrita e de leitura arbitrária sem autorização adequada (AP-06)
File: views/pedido_routes.py:9-12
File: views/admin_routes.py:16-20
File: controllers/admin_controller.py:16-29
File: models/admin_model.py:9-11
Description: dois problemas distintos de autorização sobraram. (1) `POST /pedidos` não tem nenhum decorator de auth e recebe o dono do pedido no corpo (`usuario_id`); o validador só confere que o ID existe (`services/pedido_service.py:27-28`). (2) `POST /admin/query` continua sendo um executor de SQL fornecido pelo cliente: `controllers/admin_controller.py:22` exige apenas que a string comece com `SELECT`, e `models/admin_model.py:10` entrega essa string crua ao `execute()`. As mitigações existentes (token de admin, conexão read-only, uma instrução por chamada) impedem escrita, mas não restringem o que pode ser lido.
Impact: qualquer cliente anônimo cria pedidos em nome de qualquer usuário e baixa o estoque real dos produtos — baseline #34: `POST /pedidos` sem credencial → 201, e baseline #42 confirma o estoque do produto 1 caindo de 10 para 9. Isso permite poluir o histórico de terceiros e esgotar o estoque do catálogo sem autenticação. Em `/admin/query`, qualquer portador do token estático de admin lê a base inteira, inclusive a coluna de senhas — baseline #54 devolveu os quatro hashes scrypt completos, que podem ser quebrados offline (as senhas do seed são fracas, ver AP-01).
Recommendation: exigir autenticação de usuário em `POST /pedidos` e derivar `usuario_id` do token em vez de aceitá-lo do corpo (admin pode continuar informando o dono). Remover `/admin/query` ou, se o contrato precisa ser preservado, restringi-lo a uma allowlist de consultas nomeadas e bloquear colunas de credencial. (playbook PB-07)

### [HIGH] App instanciado no import: schema e seed rodam em qualquer importação (AP-11)
File: app.py:34
File: db/connection.py:38-41
File: db/schema.py:68-87
File: config/settings.py:9-18
Description: `app.py:34` executa `app = create_app()` em nível de módulo. `create_app` chama `connection.init_app(app)` (`app.py:27`), que abre um `app_context` e roda `init_schema(get_db())` (`db/connection.py:40-41`) — ou seja, `CREATE TABLE` + `seed()` (`db/schema.py:68-72`). Importar `app` por qualquer motivo cria o arquivo `loja.db` no diretório corrente e o popula. Verificado nesta sessão: `.venv/bin/flask --app app routes`, um comando de inspeção que não sobe servidor, criou `loja.db`. Além disso, `Config` lê o ambiente no corpo da classe (`config/settings.py:9-18`), portanto os valores são congelados no import do módulo.
Impact: impossível importar a aplicação para teste, inspeção ou script sem efeito colateral em disco; impossível instanciar `create_app(TestConfig)` com outro banco sem que o banco default já tenha sido criado pela linha 34; variáveis de ambiente definidas depois do import são ignoradas. A existência da factory não resolve nada enquanto a instância default for construída no import.
Recommendation: manter `create_app()` mas adiar a criação da instância de módulo (por exemplo, expor uma factory registrada via `FLASK_APP=app:create_app` e construir o app apenas sob `if __name__ == "__main__"`), ou no mínimo mover `init_schema` para um comando CLI (`flask init-db`) chamado explicitamente pelo boot. Transformar `Config` em instância construída dentro de `create_app()` para que o ambiente seja lido no momento da criação. (playbook PB-16, PB-01)

### [HIGH] PII acessível sem autenticação por enumeração de ID (AP-25)
File: views/usuario_routes.py:15-17
File: views/pedido_routes.py:21-23
File: models/usuario_model.py:3, 22-24
Description: `GET /usuarios/<int:id>` e `GET /pedidos/usuario/<int:usuario_id>` não têm decorator de auth (as vizinhas `GET /usuarios` e `GET /pedidos` têm `@require_admin`). A primeira devolve `id, nome, email, tipo, criado_em` (`USUARIO_COLUNAS_PUBLICAS`, models/usuario_model.py:3); a segunda devolve o histórico completo de pedidos de um usuário arbitrário, com itens, quantidades, preços e totais. Não existe `before_request` ou `blueprint.before_request` cobrindo esses prefixos (`grep -rnE "before_request" --include='*.py' .` → vazio).
Impact: um cliente anônimo percorre `/usuarios/1..N` e extrai o cadastro inteiro — baseline #13: `GET /usuarios/1` sem header → 200 com `admin@loja.com` e `tipo:"admin"`, o que também identifica qual conta atacar. Baseline #40: `GET /pedidos/usuario/2` sem header → 200 com o pedido completo de outro usuário (R$ 6.179,79, itens e preços). É scraping de dados pessoais e de comportamento de compra sem nenhuma barreira, e o `@require_admin` nas rotas de listagem vira ilusão de proteção, já que o mesmo dado sai pelo detalhe.
Recommendation: proteger as duas rotas com o `require_auth` descrito em AP-24 e autorizar somente o próprio usuário ou um administrador (`require_self_or_admin`), devolvendo 403 para dono diferente e 404 para ID inexistente. (playbook PB-22, com PB-21 para o token)

### [MEDIUM] Validação de entrada incompleta (AP-14)
File: validators/usuario_validator.py:4-18
File: models/produto_model.py:44, 47
Description: (1) `validar_cadastro` aceita qualquer senha não vazia: as únicas checagens são presença (`:10`) e tipo texto (`:12`). Não há tamanho mínimo, nem limite máximo — uma senha de um caractere é aceita e hasheada, e uma string de megabytes vai direto para `generate_password_hash` (scrypt), consumindo CPU do processo. Nenhum outro ponto do código valida senha (`grep -n "senha" validators/usuario_validator.py` cobre todas as ocorrências). (2) `models/produto_model.py:44` e `:47` filtram por truthiness (`if preco_min:`) em vez de `is not None`, então `preco_min=0` e `preco_max=0` são descartados silenciosamente — o validador (`validators/produto_validator.py:49-56`) já converteu o valor para `float`, de modo que `0` chega como filtro legítimo e é ignorado. Confirmado no baseline #9b.
Impact: contas criadas pela API ficam com senhas triviais apesar do hash forte, enfraquecendo exatamente a proteção que o scrypt deveria dar; e a busca por produtos responde 200 com um resultado diferente do pedido quando o filtro é `0`, sem sinalizar nada ao cliente.
Recommendation: acrescentar tamanho mínimo e máximo de senha em `validar_cadastro` (rejeitando com o mesmo formato de erro 400 já usado) e trocar as condições de filtro por `if preco_min is not None:` / `if preco_max is not None:`. (playbook PB-11)

### [MEDIUM] Integridade referencial e índices incompletos no schema (AP-19)
File: db/schema.py:33-34, 36-43
File: models/admin_model.py:1-6
Description: `itens_pedido.produto_id` é `INTEGER NOT NULL` sem `REFERENCES produtos(id)` (db/schema.py:39), decisão registrada no comentário das linhas 33-34 para preservar o histórico quando um produto é apagado. O efeito colateral é que nada impede inserir um `produto_id` que nunca existiu. Além disso, nenhuma das chaves estrangeiras tem índice de apoio: `grep -n "CREATE INDEX" db/schema.py` → vazio, enquanto `pedidos.usuario_id` e `itens_pedido.pedido_id` são usados como critério de junção e filtro em `_SELECT_PEDIDOS_COM_ITENS` (models/pedido_model.py:3-10, 37). Por fim, `admin_model.resetar` (models/admin_model.py:1-6) apaga as quatro tabelas em cascata manual, duplicando o `ON DELETE CASCADE` já declarado no schema.
Impact: linhas de `itens_pedido` podem apontar para produtos inexistentes e aparecem na API como `"produto_nome": "Desconhecido"` (models/pedido_model.py:27) sem que seja possível distinguir "produto apagado" de "ID inválido gravado por engano". A listagem de pedidos faz varredura completa das tabelas filhas a cada chamada, custo que cresce linearmente com o histórico. A cascata manual repete regra que o banco já garante e precisará ser mantida em sincronia a cada nova tabela.
Recommendation: manter a ausência de FK se a preservação do histórico é requisito, mas documentá-la no schema como decisão explícita e validar `produto_id` contra `produtos` na escrita (o service já busca os produtos em `services/pedido_service.py:17`); criar `CREATE INDEX IF NOT EXISTS` para `pedidos(usuario_id)` e `itens_pedido(pedido_id)`; reduzir `resetar` a `DELETE FROM produtos` + `DELETE FROM usuarios`, deixando a cascata para o banco. (playbook PB-20)

### [LOW] Parâmetro de rota sombreia o builtin `id` (AP-21)
File: views/produto_routes.py:21, 34, 41
File: views/usuario_routes.py:16
Description: quatro handlers recebem o parâmetro chamado `id` (`def buscar_produto(id)`, `def atualizar_produto(id)`, `def deletar_produto(id)`, `def buscar_usuario(id)`), sombreando o builtin dentro do corpo da função. O nome vem do placeholder `<int:id>` nas regras de rota (views/produto_routes.py:20, 32, 39; views/usuario_routes.py:15). Os demais handlers do projeto já usam nomes explícitos (`<int:pedido_id>`, `<int:usuario_id>` em views/pedido_routes.py:21, 26).
Impact: inconsistência interna e risco de confusão em manutenção; nenhum efeito em runtime hoje, já que os corpos são de uma linha e não usam `id()`.
Recommendation: renomear o placeholder para `<int:produto_id>` / `<int:usuario_id>` e o parâmetro correspondente. A URL pública não muda (`/produtos/5` continua `/produtos/5`), então o contrato HTTP é preservado. (playbook PB-18)

### [LOW] Caminho de autenticação por senha em texto puro sem produtor vivo (AP-23)
File: services/usuario_service.py:11, 34-42
File: models/usuario_model.py:52-54
Description: `_senha_confere` trata como válido um valor armazenado que não comece com `scrypt:`/`pbkdf2:`, comparando-o diretamente com a senha enviada e regravando o hash (`services/usuario_service.py:39-41`). Nenhum código do projeto grava senha em texto: `usuario_model.criar` só é chamado por `usuario_service.cadastrar`, que sempre passa `generate_password_hash(senha)` (services/usuario_service.py:18), e o seed já traz hashes (db/schema.py:62-64). O ramo existe apenas para um `loja.db` anterior à refatoração — arquivo gitignored (`.gitignore`: `*.db`) e inexistente no repositório. `usuario_model.atualizar_senha` (models/usuario_model.py:52-54) só é usada por esse ramo.
Impact: código sem produtor vivo que permanece como superfície permanente de comparação não-hash: qualquer futuro algoritmo cujo prefixo não esteja em `_HASH_PREFIXES` (`argon2:`, por exemplo) cai silenciosamente na comparação de texto puro em vez de falhar. Também mantém duas funções sem uso real.
Recommendation: decidir e documentar a janela de migração; expirado o prazo, remover o ramo e `atualizar_senha`, fazendo `_senha_confere` retornar `False` para qualquer formato desconhecido. Enquanto o ramo existir, inverter a lógica para uma allowlist que rejeita (em vez de aceitar em texto puro) o que não reconhece. (playbook PB-18)

### [LOW] Documentação e mensagens que não correspondem ao comportamento real (AP-26)
File: .env.example:1
File: README.md:1-13
File: middlewares/error_handler.py:21
Description: (1) `.env.example:1` instrui "Copie para .env (ou exporte no shell)", mas nenhum arquivo carrega `.env`: `grep -rniE "dotenv" --include='*.py' .` → vazio, e `requirements.txt` tem apenas `flask` e `flask-cors`. Só a segunda metade da instrução (exportar no shell) funciona. (2) `README.md` descreve o projeto inteiro em 13 linhas e não menciona `X-Admin-Token` nem nenhuma das variáveis do `.env.example`; quem segue o README recebe 401 em 9 das 19 rotas. (3) `middlewares/error_handler.py:21` repassa `err.description` do Werkzeug, de modo que os erros de framework saem em inglês numa API cujas demais mensagens são em português — baseline #65: `{"erro":"The requested URL was not found on the server. ..."}`; baseline #66: `{"erro":"The method is not allowed for the requested URL."}`.
Impact: a instrução do `.env.example` leva o operador a crer que criou configuração quando os defaults de desenvolvimento continuam valendo — exatamente o cenário que torna o AP-01 explorável. O README não permite exercitar a API como ela existe hoje. As mensagens em inglês quebram a consistência do contrato de erro para clientes que exibem `erro` ao usuário final.
Recommendation: adicionar `python-dotenv` e carregá-lo em `create_app()`, ou corrigir o texto do `.env.example` para instruir apenas a exportação no shell; documentar no README o header de admin, as variáveis de ambiente e o comando de boot; mapear 404 e 405 para mensagens próprias em português no handler central, mantendo os mesmos códigos de status. (playbook PB-24)

Deprecated APIs: nenhuma ocorrência encontrada (greps executados: `utcnow\(\)`, `utcfromtimestamp\(`, `\.query\.get\(`, `before_first_request`, `JSONEncoder`, `json_encoder`, `_app_ctx_stack`, `_request_ctx_stack`, `attachment_filename`, `hashlib\.(md5|sha1|sha256)`, `ext\.declarative`, `engine\.execute\(`, `type\(\w+\)\s*==`). O log do baseline rodou com `PYTHONWARNINGS=default` e não registrou nenhum `DeprecationWarning`.

Verificados sem ocorrência: AP-02 (todo valor externo passa por placeholder `?`; as f-strings de SQL em models/produto_model.py:18,23,32,50 e models/usuario_model.py:18,23 interpolam apenas constantes de colunas e placeholders gerados — baseline #8, #9 e #22 confirmam que a injeção não funciona), AP-03 (maior arquivo: db/schema.py com 87 linhas), AP-04 (nenhuma senha, hash ou segredo em resposta de usuário ou em `/health`; logs só com IDs), AP-05 (scrypt via `werkzeug.security`), AP-07 (`app.run` em app.py:38 lê host/port/debug da config; defaults 127.0.0.1 e debug off), AP-08 (regra de negócio em `services/`; controllers e views finos), AP-09 (conexão por requisição em `flask.g`, sem `global` nem `check_same_thread=False`), AP-10 (`PedidoService.criar` usa `with self.conn:` com baixa condicional `WHERE estoque >= ?` e checagem de `rowcount`), AP-12 (handler central registrado em app.py:30; nenhum `except` genérico nem `str(e)`; 404 e 405 já saem em JSON), AP-13 (pedidos em 1 `LEFT JOIN`, produtos em 1 `IN`, relatório em 1 agregação), AP-15 (`row_to_*` e validadores únicos por recurso), AP-16 (não se aplica a Flask síncrono), AP-18 (CORS restrito a `CORS_ORIGINS` em app.py:25), AP-20 (constantes de domínio em models/constants.py), AP-22 (nenhum `print`; `logging` em toda a aplicação), dependências declaradas e não importadas (nenhuma).

## Previous Remaining Known Issues
- "Token de admin: enviar o header `X-Admin-Token` ... com `APP_ENV=production` o boot falha se faltarem" → **parcialmente resolvido** (AP-01) — o header funciona (baseline #11 → 401, #12 → 200) e `Config.validate()` existe (config/settings.py:20-27), mas só dispara com a string exata `production` (config/settings.py:22), deixando o fallback `dev-admin-token` ativo em qualquer outro ambiente.
- "Usuários de seed (só dev): admin@loja.com/admin123 ... senhas fracas e conhecidas" → **persiste** (AP-01) — db/schema.py:62-64; baseline #20 autentica como admin com `admin123`.
- "O login não emite token nem sessão. Por isso GET /usuarios/<id> e GET /pedidos/usuario/<id> continuam públicos" → **persiste** (AP-24, AP-25) — views/usuario_routes.py:26-29 (login sem token), views/usuario_routes.py:15-17 e views/pedido_routes.py:21-23 (rotas sem decorator); baseline #13 e #40 retornam 200 sem credencial.
- "O /admin/query foi mantido ... permite ler os hashes de senha" → **persiste** (AP-06) — views/admin_routes.py:16-20, controllers/admin_controller.py:22-26, models/admin_model.py:9-11; baseline #54 devolveu os quatro hashes scrypt.
- "`itens_pedido.produto_id` ficou sem FK de propósito" → **persiste por decisão** (AP-19) — db/schema.py:33-34, 39; mantido no relatório como item de integridade, com recomendação compatível com a decisão original.
- "Um `loja.db` antigo não é migrado ... senhas em texto puro são aceitas uma vez e regravadas" → **persiste por decisão** (AP-23) — services/usuario_service.py:34-42; nenhum produtor de senha em texto existe no código atual.
- "Cancelar um pedido ainda não devolve estoque" → **persiste por decisão de negócio** — services/pedido_service.py:48-49 chama apenas `notifier.pedido_cancelado`, e services/notification_service.py:17-18 só registra no log, sem afirmar devolução de estoque. Não vira finding: o comportamento é o do baseline original e nenhuma mensagem o contradiz.
- "O CORS agora só aceita as origens de CORS_ORIGINS" → **resolvido / por design** — app.py:25 e config/settings.py:17; é configuração documentada, não defeito em aberto.
- "Nomes de campos e parâmetros do contrato (`<int:id>`, chaves em português) foram mantidos" → **parcialmente resolvido** (AP-21) — as chaves JSON devem mesmo ser preservadas, mas o placeholder `<int:id>` (views/produto_routes.py:20, 32, 39; views/usuario_routes.py:15) pode ser renomeado sem alterar a URL pública.

================================
Total: 10 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
