# PLAN — Maestro

**Versão:** 1.0 · 24/11/2026 · **Base:** SPEC-001 v1.0 · **Dono/Executor:** Michel Bueno Silva + squad agêntico
**Repositório:** `github.com/bife29/maestro` · **Local:** `C:\Projetos\Michel\maestro` (fora do workspace de trabalho)

## 1. Arquitetura

```
                 ┌──────────────────────── presentation ─────────────────────────┐
                 │  cli/  (Typer + Rich)              mcp/  (FastMCP stdio)        │
                 │  seed · metrics · charts · kb ·    tools.yaml (allow-list)     │
                 │  review · audit · mcp serve        list_repositories …          │
                 └───────────────┬───────────────────────────────┬───────────────┘
                                 ▼                               ▼
                 ┌──────────────────────── application ──────────────────────────┐
                 │  GenerateSeed · ComputeDora · ComputePrFlow · RenderCharts     │
                 │  IndexKnowledge · AskKnowledge · AddNote                       │
                 │  ReviewPullRequest  (state machine: collect→gate→ground→       │
                 │                      analyze→validate→render→publish|dry_run)  │
                 └───────────────┬───────────────────────────────────────────────┘
                                 ▼  portas (Protocol)
                 ┌────────────────────────── domain ──────────────────────────────┐
                 │  Repository · PullRequest · Commit · Deployment · Incident      │
                 │  DoraMetrics · PrFlowMetrics · Chunk · Document                 │
                 │  ReviewVerdict (APROVADO | APROVADO_COM_RESSALVA |              │
                 │                 REPROVADO | REVISAO_MANUAL) · Finding           │
                 │  ports: DevOpsProvider · LLMProvider · KnowledgeStore ·          │
                 │         AuditSink · ChartRenderer · Clock                        │
                 └────────────────────────────────────────────────────────────────┘
                                 ▲  implementações
                 ┌──────────────────────── infrastructure ────────────────────────┐
                 │  devops/   local_json · github_rest · azure_devops_rest         │
                 │  llm/      dry · openai_compatible · bedrock                    │
                 │  kb/       sqlite_fts5 (BM25, chunking por heading)             │
                 │  audit/    jsonl_append_only                                    │
                 │  charts/   matplotlib_png                                       │
                 │  config/   maestro.toml + env (pydantic-settings)               │
                 └────────────────────────────────────────────────────────────────┘
```

Regra de dependência (import-linter): `presentation → application → domain`; `infrastructure → domain`;
nada aponta para `presentation`; `domain` não importa nem `infrastructure` nem bibliotecas de I/O.

## 2. Estrutura de pastas

```
maestro/
├─ .github/
│  ├─ workflows/ci.yml · docs.yml
│  ├─ agents/code-reviewer.agent.md
│  ├─ instructions/security-baseline.instructions.md · python-architecture.instructions.md
│  └─ ISSUE_TEMPLATE/ · PULL_REQUEST_TEMPLATE.md (manifesto de PR com campos obrigatórios)
├─ specs/                 constitution.md · SPEC-001 · PLAN.md · TASKS.md · adr/ADR-00x.md
├─ src/maestro/
│  ├─ domain/             entities.py · metrics.py · review.py · ports.py
│  ├─ application/        seed.py · dora.py · pr_flow.py · charts.py · knowledge.py · review_pipeline.py
│  ├─ infrastructure/     devops/ · llm/ · kb/ · audit/ · charts/ · config.py
│  ├─ presentation/       cli/app.py · mcp/server.py · mcp/tools.yaml
│  └─ prompts/            code_review.system.md · code_review.user.md.j2
├─ tests/                 unit/ · property/ · architecture/ · security/ · e2e/
├─ docs/                  (MkDocs) index · architecture · review-flow · rag · mcp · metrics · governance · adr · roadmap
│  └─ assets/charts/      PNGs gerados
├─ data/local/            (gitignored, gerado por `maestro seed`)  + data/sample/ (versionado, pequeno)
├─ audit/                 (gitignored)
├─ AGENTS.md · README.md · LICENSE · pyproject.toml · maestro.toml · mkdocs.yml · .pre-commit-config.yaml · .env.example
```

## 3. Fluxo do agente de revisão (F-07)

1. **collect** — `DevOpsProvider.get_pull_request(id)` → `PullRequest` (metadados, arquivos, diff, work items, votos). Gera `correlation_id`.
2. **gate** — detecta stack por extensão; aplica `max_files`/`max_lines` de `maestro.toml`. Estourou → `REVISAO_MANUAL` com checklist humano; pipeline pula para `render`.
3. **ground** — `KnowledgeStore.search` com a stack + termos do título/arquivos → trechos do padrão arquitetural e do baseline de segurança (k=6), citados no parecer.
4. **analyze** — monta prompt (sistema estático + usuário com blocos delimitados `<<<DATA … >>>`); `LLMProvider.complete` com timeout/retry/teto de tokens; `dry` devolve parecer determinístico derivado de heurísticas (regex de segredos, SQL concatenado, ausência de testes) para a demo ser útil sem LLM.
5. **validate** — `ReviewVerdict.model_validate_json`; falha → RN-01. Aplica RN-03.
6. **render** — Markdown: aviso de IA, verdicto, resumo, achados (severidade · arquivo:linha · justificativa · fonte KB), ressalvas de processo, próximos passos, rodapé com modelo/tokens/custo/correlation_id.
7. **publish | dry_run** — dry-run grava em `out/review-<pr>.md`; `--confirm` chama `DevOpsProvider.publish_review` (idempotente RN-04) e registra voto só se o verdicto permitir.
8. **audit** — a cada transição, `AuditSink.append` (RN-06).

## 4. Dados sintéticos (F-01)

Gerador determinístico (`random.Random(seed)` + faker pt_BR): 6 repositórios de um "banco fictício" (`atlas-payments-api`,
`atlas-ledger-worker`, `atlas-onboarding-web`, `atlas-notifications-consumer`, `atlas-risk-engine`, `atlas-platform-infra`),
12 meses de commits/PRs/builds/deploys/incidentes com distribuições que produzem perfis DORA distintos (um Elite, dois High,
dois Medium, um Low) para os gráficos ficarem didáticos; 40 documentos Markdown (ADRs, runbooks, post-mortems, padrões) com
front-matter `project`/`topic`. Duas PRs marcadas para a demo: `PR-07` (pequena, Python, com 2 achados plantados) e `PR-13`
(grande, 80 arquivos, para o gate).

## 5. Configuração

| Chave (`maestro.toml`) | Padrão | Uso |
|---|---|---|
| `devops.provider` | `local` | `local` · `github` · `azure_devops` |
| `llm.provider` | `dry` | `dry` · `openai_compatible` · `bedrock` |
| `llm.timeout_s` / `llm.max_retries` / `llm.max_tokens` | 60 / 2 / 4000 | resiliência e teto |
| `review.max_files` / `review.max_lines` | 50 / 3000 | gate de porte (P8) |
| `review.cost_limit_usd` | 0.50 | teto por execução |
| `kb.path` | `data/local/kb.sqlite` | índice |
| `audit.dir` | `audit/` | append-only |
| env: `GITHUB_TOKEN`, `AZURE_DEVOPS_PAT`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `AWS_*`, `MAESTRO_BOT_TOKEN` | vazios | opcionais, nunca versionados |

## 6. Fases (mapa para o TASKS.md) — cada fase termina com push + CI verde

| Fase | Nome | Entrega visível | Tasks | Est. |
|---|---|---|---|---|
| 0 | **Fundação** | Repo público, esqueleto Clean Arch, CI, README "em construção", specs, pre-commit, gitleaks | T01–T05 | 3 h |
| 1 | **Métricas & gráficos** | `seed`, `metrics dora`, `metrics pr-flow`, `charts` + 4 PNGs; testes de propriedade | T06–T10 | 5 h |
| 2 | **Base de conhecimento** | `kb index/ask/status/note` sobre 40 docs sintéticos | T11–T13 | 3 h |
| 3 | **Servidor MCP** | `mcp serve` com 6 tools, allow-list, audit, exemplos de config VS Code/Claude | T14–T16 | 3 h |
| 4 | **Agente de revisão** | `review` ponta a ponta com `dry`, gate, schema, prompt-injection suite, agent/instructions files | T17–T22 | 6 h |
| 5 | **Wiki & vitrine** | MkDocs Material em Pages, Mermaid, gráficos, README final com GIF, ADRs | T23–T27 | 4 h |
| 6 | **Integrações reais (opcional)** | providers `github` + `openai_compatible`; demo em PR de repo meu | T28–T30 | 4 h |

**Total:** ≈ 28 h. Ordem é obrigatória de 0 → 4; 5 pode começar em paralelo a partir da Fase 1 (páginas vão sendo
preenchidas); 6 é opcional.

## 7. Protocolo de pausa/retomada (P11)

- **Pausar:** terminar a task em andamento ou revertê-la (`git stash`), garantir `main` verde, atualizar `Status` no
  `TASKS.md`, commit `chore(tasks): checkpoint fase N`. Nada de WIP quebrado no `main`.
- **Retomar:** ler `TASKS.md` (próxima task `Aberto` cuja fase anterior está `Concluido`), rodar `pytest -q` para confirmar o
  estado, seguir. O `TASKS.md` é a única fonte de verdade do progresso — não depender da memória do chat.
- **Separação do trabalho:** nenhuma task deste arquivo é citada em registro de sessão, EOD ou diário profissional (P12).

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Vazar nome/dado de empregador por hábito | P1 + gitleaks + revisão manual do diff antes de cada push; nomes sintéticos com prefixo `atlas-` |
| Escopo crescer e nunca "ficar pronto" | Fases com "pronto" próprio; Fase 0+1+5 já constituem portfólio apresentável |
| FastMCP/SDK mudar API | Pinar versão em `pyproject`; testes do servidor com cliente MCP em processo |
| Demo depender de LLM pago | Provider `dry` com heurísticas reais garante demo útil offline |
| Tempo do chat de trabalho | Protocolo §7; cada sessão deste projeto começa lendo `TASKS.md`, não o histórico |
