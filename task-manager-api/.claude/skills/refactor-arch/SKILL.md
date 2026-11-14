---
name: refactor-arch
description: Use when the user asks to audit, analyze or refactor a legacy backend codebase (any stack — Python/Flask, Node/Express, etc.) into a layered MVC architecture, or invokes /refactor-arch. Executa 3 fases sequenciais - análise da stack e baseline de runtime, auditoria de anti-patterns com relatório por severidade (e pausa obrigatória para confirmação), e refatoração para MVC com validação de boot e de endpoints.
---

# refactor-arch — Auditoria e refatoração arquitetural para MVC

## Propósito

Transformar um backend legado em uma arquitetura MVC (Models, Views/Routes, Controllers + config, middlewares e composition root) **sem quebrar o comportamento observável**. A skill é agnóstica de stack: todo conhecimento específico está nos arquivos de referência.

## Entradas

- Executada a partir da **raiz do projeto** a auditar (`/refactor-arch`).
- Argumento opcional: caminho do projeto (`/refactor-arch ./outro-projeto`). Se presente (`$ARGUMENTS`), use-o como raiz; senão, use o diretório atual.
- Toda saída persistida da skill fica em `<raiz>/.refactor-arch/` (crie a pasta). Nunca escreva fora da raiz do projeto.

## Arquivos de referência (leia no momento indicado, não antes)

| Fase | Arquivo | Para quê |
|---|---|---|
| 1 | [references/project-analysis.md](references/project-analysis.md) | Detectar linguagem, framework, banco, domínio, arquitetura, rotas; subir o baseline |
| 1, 2, 3 | [references/report-template.md](references/report-template.md) | Formatos exatos dos blocos de saída das 3 fases |
| 2 | [references/anti-patterns-catalog.md](references/anti-patterns-catalog.md) | Anti-patterns (AP-xx), severidades, greps de detecção, APIs deprecated |
| 3 | [references/mvc-guidelines.md](references/mvc-guidelines.md) | Arquitetura alvo, regras de dependência, árvores por stack, adaptação |
| 3 | [references/refactoring-playbook.md](references/refactoring-playbook.md) | Transformações (PB-xx) antes/depois e regras de preservação de comportamento |

As fases são **sequenciais**. Não pule nem reordene. Use uma lista de tarefas (TodoWrite) com um item por passo abaixo.

---

## FASE 1 — Análise

Leia agora `references/project-analysis.md` e a seção 1 de `references/report-template.md`.

0. **Modo re-execução.** Antes de escrever qualquer coisa em `.refactor-arch/`: se a pasta já existe de uma execução anterior, mova **só os arquivos de topo** (`find .refactor-arch -maxdepth 1 -type f`) para `.refactor-arch/iteration-<n>/` (n = próximo inteiro livre; nunca mova pastas `iteration-*` existentes). Evidência anterior nunca é sobrescrita. Se o projeto já foi refatorado, guarde a seção "Remaining Known Issues" do `refactor-summary.md` anterior: a Fase 2 deve verificar cada item.
1. **Inventário.** Liste os arquivos-fonte e conte linhas com os comandos da seção 1 da referência (excluindo `.venv`, `node_modules`, `.claude`, `.refactor-arch`, lockfiles, bancos gerados). Leia **integralmente** cada arquivo-fonte (projetos legados são pequenos; se houver > 40 arquivos, leia todos os de rotas/models/entry e amostre o resto).
2. **Stack.** Detecte linguagem, framework + versão e dependências diretas pelos manifestos e confirme pelos imports. Marque dependências declaradas e não importadas.
3. **Banco.** Identifique driver/ORM, arquivo/URL de conexão, tabelas (greps de `CREATE TABLE`/modelos), quando o schema é criado e se existe seed.
4. **Domínio e arquitetura.** Infira o domínio (rotas + tabelas + README). Classifique: Monolítica / Camadas parciais / MVC em camadas, com evidência.
5. **Entry point e rotas.** Registre o comando de start original, porta, host e debug (e se estão hardcoded). Enumere **todas** as rotas (método + path + handler + arquivo:linha) com o método da seção 8 da referência.
6. **Baseline de runtime (oráculo da Fase 3).**
   1. Instale dependências em ambiente isolado (`python3 -m venv .venv` + `pip install -r ...`; `npm install`). Se o binding nativo do `sqlite3` (Node) faltar: `cd node_modules/sqlite3 && npx prebuild-install -r napi`.
   2. Escolha porta livre (`lsof -nP -iTCP:<porta> -sTCP:LISTEN`). Se porta/debug estão hardcoded, suba via CLI do framework ou wrapper (`flask --app <mod> run --host 127.0.0.1 --port <p>`; `node -e "require('./<cfg>').<obj>.port=<p>; require('./<entry>')"`) — **sem editar arquivos**.
   3. Rode seed se o projeto exigir; lembre que alguns bancos só são criados na 1ª requisição.
   4. Suba em background com log em `.refactor-arch/baseline-server.log`; chame **todas** as rotas com `curl` (leituras → criações → atualizações → deleções/resets por último), incluindo um caso inválido barato por recurso, um path inexistente (`/__rota-inexistente__`: anote status + `Content-Type`) e, se houver login, o formato do token devolvido (login 2×).
   5. Salve `.refactor-arch/baseline.md` no formato da seção 9.4 (comando de boot, versões, tabela método/path/payload/status/shape, observações como warnings de deprecação, crashes e vazamentos).
   6. **Pare o servidor** (`kill <PID>`; confirme com `lsof`). Se você criou um banco SQLite gitignored durante o baseline, anote como recriá-lo.
7. **Imprima** o bloco `PHASE 1: PROJECT ANALYSIS` exatamente no formato do template, seguido de entry point, nº de rotas e caminho do baseline, e salve o mesmo conteúdo em `.refactor-arch/phase1-analysis.md`.

Escritas permitidas na Fase 1: somente `.refactor-arch/` e instalações (`.venv/`, `node_modules/`). Nenhum arquivo do projeto é alterado.

---

## FASE 2 — Auditoria

Leia agora `references/anti-patterns-catalog.md` (inteiro, incluindo a seção "APIs deprecated") e a seção 2 de `references/report-template.md`.

1. **Varredura sistemática.** Para **cada** entrada AP-01…AP-26, rode os sinais de detecção (greps) sobre todos os arquivos-fonte. Depois, **leia** cada ocorrência para confirmar — grep sozinho não é evidência.
2. **Leitura dirigida.** Além dos greps, releia cada arquivo procurando o que grep não pega: regra de negócio em handlers, falta de transação, N+1 em loops, falta de auth em rotas destrutivas e em listagens com PII, tokens nunca verificados, mensagens de resposta que não condizem com o código, senhas literais no seed, módulos nunca importados, duplicação. Em modo re-execução, verifique cada item de "Remaining Known Issues" anterior e registre no bloco `Previous Remaining Known Issues` do template.
3. **APIs deprecated.** Rode todos os greps da tabela da stack detectada; cruze com warnings vistos no log do baseline. Agregue num único finding AP-17.
4. **Evidência de runtime.** Associe achados ao baseline (ex.: senha na resposta, 500 com mensagem SQL, crash do processo).
5. **Linhas exatas.** Antes de escrever o relatório, confirme **toda** referência `arquivo:linha` com `grep -n` ou `nl -ba arquivo | sed -n 'a,bp'` nesta sessão. Nunca de memória.
6. **Severidade.** Use a escala do catálogo; aplique as regras de ajuste (subir quando houver impacto comprovado maior).
7. **Relatório.** Monte o `ARCHITECTURE AUDIT REPORT` exatamente no template: Summary, findings ordenados CRITICAL → HIGH → MEDIUM → LOW, cada um com `File`, `Description`, `Impact`, `Recommendation (playbook PB-xx)`, e `Total`. Confira que Summary e Total batem com os blocos.
8. **Persistência.** Salve em `.refactor-arch/audit-report.md`, terminando com a linha do gate (passo 10). Se existir `../reports/` (raiz do repositório), diga ao usuário que o relatório pode ser copiado para lá — não escolha nome nem copie por conta própria.
9. **Imprima** o relatório completo.
10. **GATE OBRIGATÓRIO.** Imprima exatamente a linha abaixo e **encerre o turno**. Não execute mais nenhuma ferramenta.

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

- Resposta `y`/`sim`/`yes` → Fase 3.
- Resposta `n` ou qualquer coisa ambígua → pare. Não altere nada. Informe onde estão o baseline e o relatório.

### Nunca pule o gate

Antes da confirmação, **nenhum** arquivo do projeto pode ser criado, editado, movido ou apagado (só `.refactor-arch/`, `.venv/`, `node_modules/`).

| Racionalização | Realidade |
|---|---|
| "O usuário pediu para rodar tudo de uma vez" | Ainda assim pergunte. O gate é parte do contrato da skill. |
| "É uma mudança pequena / óbvia" | Pequena ou não, é modificação. Pergunte. |
| "Vou só criar a pasta `config/` adiantado" | Criar arquivo no projeto é modificação. Pergunte. |
| "Estou em modo automático / sem usuário olhando" | Pare no gate e encerre o turno. |
| "Já sei que a resposta será sim" | Você não sabe. Pergunte. |
| "Vou corrigir só a falha crítica de segurança antes" | Reporte-a como CRITICAL e pergunte. |

Red flags — se pensar nisso, pare: "enquanto espero, já adianto…", "vou só testar uma correção…", "o usuário não vai se importar…".

---

## FASE 3 — Refatoração (somente após `y`)

Leia agora `references/mvc-guidelines.md`, `references/refactoring-playbook.md` (incluindo "Regras de preservação de comportamento") e a seção 3 de `references/report-template.md`.

### 3.1 Planejar

1. Escolha a estratégia pelo nível de arquitetura da Fase 1 (`mvc-guidelines.md` seção 5): **monolito → split completo**; **camadas parciais → incremental** (preserve o que funciona, insira controllers/services, config, error handler, app factory, mova código fora do lugar).
2. Desenhe a árvore alvo usando a árvore da stack (seção 4) e os nomes de entidade do próprio código. Mapeie cada finding → padrão PB-xx → arquivos afetados.
3. Decida antecipadamente: como o start original continuará funcionando, onde ficam schema/seed, qual header/token de admin será usado (se PB-07 se aplica) e qual chave de erro o projeto já usa.

### 3.2 Executar (prioridade CRITICAL → HIGH → MEDIUM → LOW)

1. Config e segredos (PB-01) + `.env.example` com todas as chaves e valores fictícios.
2. Camada de dados: conexão/DI (PB-17), queries parametrizadas (PB-02), transações (PB-09), wrapper async (PB-12), N+1 (PB-10), integridade (PB-20).
3. Segurança: hash de senha + seed com hash e senhas do env (PB-05, PB-25), remoção de dados sensíveis (PB-06), auth em rotas admin/destrutivas (PB-07), token de login assinado + `require_auth` (PB-21), auth em listagens com PII (PB-22).
4. Camadas: models → services (regra pesada) → controllers → views/routes (PB-03, PB-04), validação (PB-11).
5. Transversal: error handler central + exceções de domínio (PB-08), catch-all 404/405 (PB-23), app factory/composition root (PB-16), CORS (PB-19), logging (PB-15).
6. Qualidade: APIs deprecated (PB-13), constantes (PB-14), DRY/código morto/nomes internos (PB-18), mensagens enganosas (PB-24 — reveja as strings após as correções).
7. **Limpeza:** apague arquivos totalmente migrados (monolito antigo, utilitários mortos). Nenhum módulo antigo pode continuar importável com rotas/SQL duplicados. Mantenha **um** entry point claro e o comando de start original funcionando (`python app.py`, `npm start`, `flask --app app run`).
8. Atualize manifestos só se adicionar dependência realmente necessária (prefira stdlib/framework já instalado) e reinstale no ambiente isolado.

Respeite sempre as regras de preservação: mesmos paths, métodos, parâmetros, shapes e status para requisições válidas; mudanças só na direção segura e documentadas.

### 3.3 Validar (loop de até 3 iterações)

1. Restaure o estado inicial de dados (rode o seed; recrie o banco gitignored criado no baseline) para que IDs batam com o baseline. Se senhas de seed passaram a vir do env (PB-25), **exporte-as** com os valores de dev do baseline (documentados no `.env.example`) antes do seed e do boot.
2. Suba a aplicação com o **comando de start original** (ou equivalente com porta livre via env, ex.: `PORT=<p> npm start`, `PORT=<p> python app.py`), em background, log em `.refactor-arch/refactor-server.log`. Verifique: processo vivo, sem traceback/erro no log.
3. Repita **cada** requisição do `baseline.md` e compare status + shape. Para rotas com auth nova, obtenha a credencial chamando o login (`Authorization: Bearer <token>`) ou usando o header de admin documentado; confirme também 401/403 sem ela. Repita o path inexistente: 404 no formato da API, não HTML.
4. Re-rode os greps do catálogo para todos os findings CRITICAL e HIGH do relatório; nenhum sinal confirmado deve restar. Confirme também a ausência de imports para arquivos removidos (`grep -rn "<modulo_antigo>"`).
5. Se algo falhar: diagnostique pela mensagem real (log/curl), corrija, e volte ao passo 1. Máximo 3 iterações; o que restar vai para "Remaining Known Issues" com ✗ no checklist.
6. **Pare todos os servidores** que você iniciou (`kill <PID>`; confirme com `lsof`).

### 3.4 Concluir

1. Gere a árvore real (`find`/`tree` sem `.venv`, `node_modules`, `.claude`, `.refactor-arch`, `__pycache__`).
2. Imprima o bloco `PHASE 3: REFACTORING COMPLETE` no formato do template: New Project Structure, Changes Applied, Validation (✓/✗ baseados em comandos executados), Endpoint Comparison (antes/depois) e Remaining Known Issues — incluindo como obter o token de admin e o token de login, e quais variáveis de seed o validador precisa exportar.
3. Salve o bloco em `.refactor-arch/refactor-summary.md`.
4. Não faça commit (a menos que o usuário peça).

---

## Quick reference

| Fase | Ler | Produz | Termina com |
|---|---|---|---|
| 1 Análise | project-analysis.md, report-template.md §1 | `.refactor-arch/baseline.md` + bloco PHASE 1 | servidor do baseline parado |
| 2 Auditoria | anti-patterns-catalog.md, report-template.md §2 | `.refactor-arch/audit-report.md` + relatório impresso | `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e fim do turno |
| 3 Refatoração | mvc-guidelines.md, refactoring-playbook.md, report-template.md §3 | código MVC, `.env.example`, `.refactor-arch/refactor-summary.md` | validação ✓, servidores parados |

| Situação | Ação |
|---|---|
| Porta ocupada | `lsof -nP -iTCP:<p> -sTCP:LISTEN`; use outra porta via CLI/env/wrapper |
| Porta/debug hardcoded no baseline | subir via CLI do framework ou wrapper, sem editar |
| `sqlite3` Node sem binding (npm ≥ 11 bloqueia install scripts) | `npm install-scripts approve sqlite3` (grava `allowScripts` no package.json) ou `cd node_modules/sqlite3 && npx prebuild-install -r napi` |
| Banco criado só na 1ª requisição | faça uma requisição de leitura antes de comparar dados |
| Banco `:memory:` | aguarde schema+seed antes do `listen`; uma única conexão injetada |
| Projeto já tem camadas | estratégia incremental; não reescreva o que funciona |
| Auth nova em rota original | documente header + token de dev; valide com e sem credencial |
| `.refactor-arch/` já existe | modo re-execução: mova arquivos de topo para `iteration-<n>/` |
| Seed lê senhas do env | exporte os valores de dev do baseline antes de seed/boot na validação |

## Common mistakes

- **Editar arquivos antes do `y`** — inclusive "só criar uma pasta". Viola o gate.
- **Mudar URLs, métodos, nomes de campos ou formato de erro** — quebra clientes; é proibido mesmo que o nome seja ruim.
- **Quebrar o seed** ou o comando de start original (ex.: remover `app` em nível de módulo usado por `from app import app`).
- **Deixar o monolito antigo importável** ao lado da nova estrutura (rotas duplicadas, código morto).
- **Linhas de memória** no relatório — sempre `grep -n`/`nl -ba` na sessão.
- **Esquecer de matar servidores** do baseline ou da validação (porta presa na próxima execução).
- **Declarar ✓ sem executar** o boot e as requisições.
- **Trocar `utcnow()` por datetime aware** sem tratar comparações com colunas naive e o formato serializado.
- **Error handler registrado antes das rotas** no Express ou sem wrapper async no Express 4.
- **Criar pacote `app/` ao lado de `app.py`** em Python (conflito de import).
- **Remover endpoint perigoso** em vez de protegê-lo — mantenha a rota, exija auth e restrinja.
- **Token previsível no login** (`'token-' + id`, Base64 do id) ou token que nenhuma rota verifica — é CRITICAL (AP-24), não detalhe.
- **Deixar 404 de rota inexistente fora do handler central** (HTML padrão do framework numa API JSON/texto).
- **Listagem de PII sem auth** tratada como "CRUD comum" (AP-25).
- **Fallback literal para senha de seed** (`get("SEED_..._PASSWORD", "admin123")`) ou seed que quebra sem `.env` — gere aleatória e imprima.
- **Mensagem antiga que ficou falsa** após a correção (ex.: "dados relacionados mantidos" depois da cascata).
- **Sobrescrever `.refactor-arch/` de execução anterior** em vez de arquivar em `iteration-<n>/`.
- **Ignorar código existente não usado** em projetos parcialmente organizados (helpers/validações prontas viram a fonte única ou são apagados).
