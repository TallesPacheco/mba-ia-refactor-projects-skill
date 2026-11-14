# Templates de Saída (Fases 1, 2 e 3)

Os blocos abaixo são **formatos exatos**. Mantenha os títulos, a ordem dos campos, os separadores `================================` e os rótulos em inglês. O conteúdo descritivo (Description, Impact, Recommendation, observações) é escrito em português.

---

## 1. Resumo da Fase 1

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem> <versão do runtime, se conhecida>
Framework:     <framework> <versão>
Dependencies:  <deps diretas relevantes, separadas por vírgula; marque "(não usada)" quando for o caso>
Domain:        <tipo de sistema> (<entidades principais>)
Architecture:  <Monolítica | Camadas parciais | MVC em camadas> — <evidência em uma frase>
Source files:  <N> files analyzed
DB tables:     <tabela1>, <tabela2>, ... (<banco/driver>)
================================
```

Regras:
- `Source files` = contagem do comando da seção 1 de `project-analysis.md` (sem venv, node_modules, .claude, lockfiles).
- `Framework` com versão do manifesto (ou instalada, se o manifesto não fixa).
- Após o bloco, imprima em 3–6 linhas: entry point + comando de start, nº de rotas encontradas e o caminho do baseline (`.refactor-arch/baseline.md`).

---

## 2. Relatório da Fase 2 (ARCHITECTURE AUDIT REPORT)

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <linguagem> + <framework>
Files:   <N> analyzed | ~<L> lines of code

## Summary
CRITICAL: <a> | HIGH: <b> | MEDIUM: <c> | LOW: <d>

## Findings

### [CRITICAL] <Nome do anti-pattern> (AP-xx)
File: <caminho/relativo>:<linha>[-<linha>]
File: <outro/arquivo>:<linha>
Description: <o que está errado, citando o trecho/valor concreto>
Impact: <consequência técnica ou de negócio; cite evidência de runtime do baseline se houver>
Recommendation: <correção concreta> (playbook PB-xx)

### [HIGH] <Nome> (AP-xx)
File: ...
Description: ...
Impact: ...
Recommendation: ... (playbook PB-xx)

### [MEDIUM] Deprecated APIs (AP-17)
File: <arquivo>:<linha>, <linha>, <linha>   — <api deprecated> → <equivalente moderno>
File: <arquivo>:<linha>                       — <api deprecated> → <equivalente moderno>
Description: ...
Impact: ...
Recommendation: ... (playbook PB-13)

### [LOW] <Nome> (AP-xx)
File: ...
Description: ...
Impact: ...
Recommendation: ... (playbook PB-xx)

## Previous Remaining Known Issues (somente modo re-execução)
- <item do refactor-summary.md anterior> → resolvido | persiste (AP-xx) — <evidência: comando/arquivo:linha>

================================
Total: <N> findings
================================
```

### Regras do relatório

1. **Ordenação:** todos os CRITICAL, depois HIGH, MEDIUM, LOW. Dentro da mesma severidade, ordem do catálogo (AP-01, AP-02...).
2. **Localização exata:** toda linha `File:` vem de `grep -n` ou `nl -ba` executado **nesta sessão**, após a última leitura do arquivo. Nunca de memória. Intervalos `a-b` só quando o trecho inteiro é o problema (ex.: uma função/classe). Caminhos relativos à raiz do projeto.
3. **Múltiplas ocorrências:** uma linha `File:` por arquivo; várias linhas do mesmo arquivo separadas por vírgula (`models.py:28, 47-50, 92`). Se houver mais de ~12 ocorrências, liste as 12 mais representativas e acrescente `(+N ocorrências: <comando grep usado>)`.
4. **Um finding por anti-pattern por causa raiz.** Não duplique o mesmo problema em dois IDs; se um trecho evidencia dois anti-patterns (ex.: senha em log = AP-04 + AP-22), registre no mais severo e cite no outro só se houver ocorrências adicionais.
5. **Deprecated APIs:** se qualquer API da tabela do catálogo for encontrada, inclua o finding agregado "Deprecated APIs (AP-17)". Se nenhuma, não crie o finding, mas acrescente ao final da seção Findings a linha `Deprecated APIs: nenhuma ocorrência encontrada (greps: <lista curta>)`.
6. **Summary e Total** devem bater com a contagem real dos blocos `### [...]`.
7. **Evidência de runtime:** quando o baseline mostrou o problema (ex.: senha na resposta, crash, 500 com mensagem SQL), cite em `Impact` (`baseline: GET /x → 200 com campo "password"`).
8. **Nada de "talvez":** só reporte o que foi confirmado lendo o código. Itens verificados e ausentes podem ser citados numa linha final `Verificados sem ocorrência: ...` (opcional).
9. **Modo re-execução:** liste cada item de "Remaining Known Issues" do `refactor-summary.md` anterior no bloco `Previous Remaining Known Issues` com veredito e evidência; item que persiste também vira finding normal (contado em Summary/Total). Omita o bloco na primeira execução.
10. Mínimo esperado em projetos legados: ≥ 5 findings. Se encontrar menos, revise o catálogo inteiro de novo antes de concluir.

### Persistência

- Salve o relatório completo em `.refactor-arch/audit-report.md` (dentro do projeto).
- Se existir o diretório `../reports/` (raiz do repositório), informe ao usuário que o relatório pode ser copiado para lá — **não** escolha o nome nem copie sem solicitação explícita.
- Depois de imprimir o relatório, imprima exatamente:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## 3. Bloco de conclusão da Fase 3

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<raiz>/
├── <entry point> (composition root)
├── config/
│   └── settings.<ext>
├── models/
│   └── ...
├── controllers/
│   └── ...
├── views/ (ou routes/)
│   └── ...
├── middlewares/
│   └── error_handler.<ext>
└── .env.example

## Changes Applied
  [AP-01] <o que foi feito> → <arquivo(s)>
  [AP-02] ...
  (uma linha por finding resolvido; marque "(parcial)" quando aplicável)

## Validation
  ✓ Application boots without errors (<comando de start>, porta <p>)
  ✓ All baseline endpoints respond (<x>/<y> com mesmo status e shape)
  ✓ Original start command still works (<comando original>)
  ✓ Seed / initial data loads
  ✓ No CRITICAL/HIGH catalog signals remaining (re-grep)
  ✓ Old monolith/duplicate files removed
  ✓ .env.example created
  ✗ <item que falhou — com motivo>

## Endpoint Comparison
| Método | Path | Status antes | Status depois | Shape | Obs |
|---|---|---|---|---|---|
| GET | /items | 200 | 200 | = | |
| GET | /users/1 | 200 | 200 | ≈ | campo "password" removido (fix AP-04) |
| POST | /admin/reset | 200 | 401 sem token / 200 com `X-Admin-Token` | = | auth adicionada (fix AP-06) |
| POST | /login | 200 | 200 | ≈ | `token` continua string; valor agora assinado (fix AP-24) |
| GET | /__rota-inexistente__ | 404 text/html | 404 JSON | ≈ | catch-all no handler central (fix AP-12) |

## Remaining Known Issues
  - <finding não resolvido ou parcialmente resolvido, com motivo>
  - <dívida técnica sugerida para depois (ex.: migrar hashes existentes no próximo login)>
================================
```

Regras:
- `✓`/`✗` refletem o que foi **executado** nesta sessão (comando + resultado), nunca suposição.
- Coluna `Shape`: `=` idêntico; `≈` igual exceto mudança de segurança intencional (explique em Obs); `≠` diferente (exige correção ou justificativa em Remaining Known Issues).
- A árvore mostra a estrutura **real** gerada (use `find`/`tree` excluindo `.venv`, `node_modules`, `.claude`, `.refactor-arch`, `__pycache__`).
- Salve o bloco em `.refactor-arch/refactor-summary.md`.
